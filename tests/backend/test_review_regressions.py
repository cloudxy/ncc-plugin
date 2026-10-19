import base64
import json
from uuid import uuid4

import pytest

from ncc_data.application.service import Service
from ncc_data.creation.worker import Worker, create_task
from ncc_data.domain.contracts import CreationInput, Intervention, MemberInput, ScopeInput, StateQuery
from ncc_data.persistence.models import ImportRun, Job, User
from ncc_data.runtime.settings import Settings
from ncc_shared.errors import DomainError
from ncc_shared.serialization import digest
from tests.backend.test_core import commit, create


async def test_secret_revocation_blocks_saved_drafts_exports_and_fact_mutation(store):
    factory, ids = store
    async with factory() as db, db.begin():
        owner = Service(db, await db.get(User, ids[0]))
        sid = (await owner.create_scope(ScopeInput(name="撤权验证")))["id"]
        await owner.set_member(
            sid, MemberInput(user_id=ids[1], actions=["read", "edit", "adopt", "export", "secret"])
        )
        member = Service(db, await db.get(User, ids[1]))
        target = await create(member, sid, "公开人物")
        change = await commit(
            member,
            sid,
            [
                {
                    "op": "fact",
                    "entity_id": target["id"],
                    "fact": {
                        "predicate": "hidden",
                        "category": "fact",
                        "value": {"text": "SECRET"},
                        "secret": True,
                        "source": {"kind": "author"},
                    },
                }
            ],
        )
        fact = (await member.facts(sid, StateQuery(category="fact")))["items"][0]
        blob = await member.upload(sid, "private.json", "application/json", b"SECRET", purpose="export")
        await owner.set_member(sid, MemberInput(user_id=ids[1], actions=["read", "edit", "adopt", "export"]))
        assert await member.changes(sid) == []
        for call in [member.change(sid, change["id"]), member.attachment(sid, blob["id"])]:
            with pytest.raises(DomainError):
                await call
        for operation in [
            {"op": "retract", "entity_id": target["id"], "fact_id": fact["id"]},
            {
                "op": "fact",
                "entity_id": target["id"],
                "fact": {
                    "predicate": "hidden",
                    "category": "fact",
                    "supersedes": fact["id"],
                    "value": {"text": "forbidden replacement"},
                    "source": {"kind": "author"},
                },
            },
        ]:
            with pytest.raises(DomainError):
                await commit(member, sid, [operation])
        assert (await owner.facts(sid, StateQuery(category="fact")))["total"] == 1


async def test_workspace_metadata_reorder_and_delete_do_not_resurrect(store):
    factory, ids = store
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        sid = (await svc.create_scope(ScopeInput(name="元数据验证")))["id"]

        def file(path, content):
            raw = content.encode()
            return {"path": path, "base64": base64.b64encode(raw).decode(), "sha256": digest(raw)}

        state = {
            "title": "合成书",
            "chapters": [{"seq": 1, "title": "旧标题", "file": "text.md", "status": "draft"}],
        }
        await svc.workspace_commit(
            sid,
            {
                "format": "ncc.workspace/1",
                "request_id": "initial",
                "base_version": 0,
                "files": [file("book.json", json.dumps(state)), file("text.md", "旧正文")],
            },
        )
        identity = next(x for x in await svc.all_entities(sid) if x["kind"] == "chapter")["id"]
        state["chapters"][0].update(seq=3, title="新标题", status="complete")
        await svc.workspace_commit(
            sid,
            {
                "format": "ncc.workspace/1",
                "request_id": "metadata",
                "base_version": 1,
                "files": [file("book.json", json.dumps(state))],
            },
        )
        chapter = await svc.entity(sid, identity)
        assert (
            chapter["name"] == "新标题"
            and chapter["data"]["position"] == 3
            and chapter["data"]["status"] == "complete"
        )
        snapshot = await svc.workspace_snapshot(sid)
        book = json.loads(
            base64.b64decode(next(x["base64"] for x in snapshot["files"] if x["path"] == "book.json"))
        )
        assert book["chapters"][0]["status"] == "complete"
        await svc.workspace_commit(
            sid,
            {
                "format": "ncc.workspace/1",
                "request_id": "delete",
                "base_version": 2,
                "files": [{"path": "text.md", "deleted": True}],
            },
        )
        assert "text.md" not in {x["path"] for x in (await svc.workspace_snapshot(sid))["files"]}
        await svc.workspace_commit(
            sid,
            {
                "format": "ncc.workspace/1",
                "request_id": "readd",
                "base_version": 3,
                "files": [file("text.md", "旧正文")],
            },
        )
        assert (await svc.entity(sid, identity))["data"]["position"] == 3


async def test_failed_model_outputs_still_consume_budget(store):
    class Invalid:
        identity = "fixture:invalid"
        calls = 0

        async def call(self, purpose, packet, budget):
            self.calls += 1
            return {"text": ""}, {"tokens": 600, "kind": "fixture"}

    factory, ids = store
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        sid = (await svc.create_scope(ScopeInput(name="预算验证")))["id"]
        job = await create_task(
            svc, sid, CreationInput(objective="无效响应测试", scheme="P3", token_budget=1000)
        )
    provider = Invalid()
    worker = Worker(factory, Settings(database_url="unused"), provider)
    for attempt in range(3):
        await worker.run_once()
        async with factory() as db, db.begin():
            svc = Service(db, await db.get(User, ids[0]))
            row = await svc.job(sid, job["id"])
            assert row.progress["tokens"] >= 600
            if attempt < 2:
                await svc.intervene(sid, job["id"], Intervention(action="resume"))
    assert provider.calls == 2


async def test_long_novel_packet_uses_latest_prior_chapters(store):
    factory, ids = store
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        sid = (await svc.create_scope(ScopeInput(name="长篇上下文")))["id"]
        await commit(
            svc,
            sid,
            [
                {"op": "create", "kind": "chapter", "name": str(n), "text": str(n), "data": {"position": n}}
                for n in range(1, 106)
            ],
        )
        job = await create_task(svc, sid, CreationInput(objective="续写"))
        row = await svc.job(sid, job["id"])
        packet = await Worker(factory, Settings(database_url="unused")).packet(svc, row)
        assert packet["next_position"] == 106
        assert [x["name"] for x in packet["sources"]] == ["103", "104", "105"]


async def test_four_successful_import_batches_are_not_retry_exhaustion(store):
    factory, ids = store
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        sid = (await svc.create_scope(ScopeInput(name="多批导入")))["id"]
        blob = await svc.upload(sid, "source.txt", "text/plain", b"synthetic original")
        operations = [
            {"op": "create", "entity_id": str(uuid4()), "kind": "source", "name": str(i)} for i in range(4)
        ]
        plan = ImportRun(
            scope_id=sid,
            actor_id=ids[0],
            attachment_id=blob["id"],
            base_version=0,
            mapping={},
            plan={
                "rows": operations,
                "batches": [[o] for o in operations],
                "errors": [],
                "warnings": [],
                "source_digest": blob["digest"],
            },
        )
        db.add(plan)
        await db.flush()
        job = await svc.queue_import(sid, plan.id)
    worker = Worker(factory, Settings(database_url="unused"))
    for _ in range(10):
        await worker.run_once()
    async with factory() as db:
        row = await db.get(Job, job["id"])
        assert row.state == "succeeded" and row.progress["committed"] == 4


async def test_unset_secret_preserves_hidden_data_and_public_edit_works(store):
    factory, ids = store
    async with factory() as db, db.begin():
        owner = Service(db, await db.get(User, ids[0]))
        sid = (await owner.create_scope(ScopeInput(name="字段写权限")))["id"]
        target = await create(
            owner, sid, "公开人物", data={"secret_note": "秘密旧值", "description": "公开旧值"}
        )
        await owner.set_member(sid, MemberInput(user_id=ids[1], actions=["read", "edit", "adopt"]))
        member = Service(db, await db.get(User, ids[1]))
        assert "secret_note" not in (await member.entity(sid, target["id"]))["data"]
        await commit(
            member,
            sid,
            [
                {
                    "op": "update",
                    "entity_id": target["id"],
                    "expected": target["version"],
                    "data": {"description": "公开新值"},
                }
            ],
        )
        latest = await member.entity(sid, target["id"])
        with pytest.raises(DomainError):
            await commit(
                member,
                sid,
                [
                    {
                        "op": "update",
                        "entity_id": target["id"],
                        "expected": latest["version"],
                        "unset": ["secret_note"],
                    }
                ],
            )
        assert (await owner.entity(sid, target["id"]))["data"]["secret_note"] == "秘密旧值"


async def test_fact_history_does_not_depend_on_current_target_retirement(store):
    factory, ids = store
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        sid = (await svc.create_scope(ScopeInput(name="历史同基线")))["id"]
        a = await create(svc, sid, "甲")
        sword = await create(svc, sid, "剑", "item")
        await commit(
            svc,
            sid,
            [
                {
                    "op": "fact",
                    "entity_id": a["id"],
                    "fact": {
                        "predicate": "owns",
                        "category": "relation",
                        "object_id": sword["id"],
                        "source": {"kind": "author"},
                    },
                }
            ],
        )
        pin = (await svc.scope_info(sid))["version"]
        assert (await svc.facts(sid, StateQuery(as_of=pin, predicate="owns")))["total"] == 1
        await commit(svc, sid, [{"op": "retire", "entity_id": sword["id"], "expected": sword["version"]}])
        assert (await svc.facts(sid, StateQuery(as_of=pin, predicate="owns")))["total"] == 1


async def test_revoked_membership_does_not_break_or_expose_scope_list(store):
    factory, ids = store
    async with factory() as db, db.begin():
        owner = Service(db, await db.get(User, ids[0]))
        sid = (await owner.create_scope(ScopeInput(name="不可见作品")))["id"]
        await owner.set_member(sid, MemberInput(user_id=ids[1], actions=["read"]))
        member = Service(db, await db.get(User, ids[1]))
        assert len(await member.scopes()) == 1
        await owner.set_member(sid, MemberInput(user_id=ids[1], actions=[]))
        assert await member.scopes() == []
