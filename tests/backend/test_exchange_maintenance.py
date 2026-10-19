import base64
import json
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from ncc_data.application.service import Service
from ncc_data.creation.worker import Worker
from ncc_data.domain.contracts import MaintenanceInput, ScopeInput, StateQuery
from ncc_data.persistence.models import User
from ncc_data.runtime.settings import Settings
from ncc_shared.serialization import digest
from tests.backend.test_core import commit, create


async def test_forward_refs_export_import_and_attachments(store):
    factory, ids = store
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        sid = (await svc.create_scope(ScopeInput(name="原书")))["id"]
        a, b = str(uuid4()), str(uuid4())
        attachment = await svc.upload(sid, "source.txt", "text/plain", b"original-source")
        await commit(
            svc,
            sid,
            [
                {"op": "create", "entity_id": a, "kind": "character", "name": "甲", "data": {"source_id": b}},
                {
                    "op": "create",
                    "entity_id": b,
                    "kind": "source",
                    "name": "乙",
                    "data": {"attachment_id": attachment["id"]},
                },
            ],
        )
        for start in range(0, 205, 100):
            await commit(
                svc,
                sid,
                [
                    {
                        "op": "fact",
                        "entity_id": a,
                        "fact": {
                            "predicate": "record",
                            "category": "fact",
                            "value": {"n": n},
                            "source": {"kind": "author"},
                        },
                    }
                    for n in range(start, min(start + 100, 205))
                ],
            )
        raw, _, _ = await svc.export_bytes(sid, (await svc.scope_info(sid))["version"])
        payload = json.loads(raw)
        assert len(payload["facts"]) >= 205
        assert payload["attachments"][0]["base64"] == base64.b64encode(b"original-source").decode()
        target = (await svc.create_scope(ScopeInput(name="导入书")))["id"]
        upload = await svc.upload(target, "export.json", "application/json", raw)
        plan = await svc.preflight_import(target, upload["id"], {})
        assert not plan["errors"], plan
        assert (await svc.scope_info(target))["version"] == 0
        job = await svc.queue_import(target, plan["id"], True)
    worker = Worker(factory, Settings(database_url="unused"))
    for _ in range(20):
        await worker.run_once()
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        row = await svc.job(target, job["id"])
        assert row.state == "succeeded", row.result
        entities = await svc.all_entities(target)
        person = next(x for x in entities if x["name"] == "甲")
        source = next(x for x in entities if x["name"] == "乙")
        assert person["data"]["source_id"] == source["id"]
        assert (await svc.attachment(target, source["data"]["attachment_id"])).data == b"original-source"
        assert (await svc.facts(target, StateQuery(subject_id=person["id"])))["total"] >= 205


async def test_restore_merge_split_and_three_way_branch(store):
    factory, ids = store
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        sid = (await svc.create_scope(ScopeInput(name="维护书")))["id"]
        a = await create(svc, sid, "甲", data={"description": "旧设定"}, text="旧正文")
        await commit(
            svc, sid, [{"op": "update", "entity_id": a["id"], "expected": a["version"], "text": "新正文"}]
        )
        plan = await svc.maintenance_plan(
            sid,
            MaintenanceInput(action="restore", base_version=2, entity_id=a["id"], revision_id=a["revision"]),
        )
        assert plan["change"]["validation"]["valid"]
        await svc.adopt(sid, plan["change"]["id"], "restore-once")
        assert (await svc.entity(sid, a["id"]))["text"] == "旧正文"
        b = await create(svc, sid, "乙")
        plan = await svc.maintenance_plan(
            sid, MaintenanceInput(action="merge", base_version=4, entity_id=b["id"], target_id=a["id"])
        )
        await svc.adopt(sid, plan["change"]["id"], "merge-once")
        assert len(await svc.all_entities(sid)) == 1
        branch = (await svc.create_scope(ScopeInput(name="分支", kind="branch", base_id=sid)))["id"]
        old = await svc.entity(branch, a["id"])
        await commit(
            svc,
            branch,
            [{"op": "update", "entity_id": a["id"], "expected": old["version"], "text": "分支结局"}],
        )
        current = await svc.entity(sid, a["id"])
        await commit(
            svc,
            sid,
            [{"op": "update", "entity_id": a["id"], "expected": current["version"], "text": "正史结局"}],
        )
        plan = await svc.maintenance_plan(
            sid, MaintenanceInput(action="branch_merge", base_version=6, branch_id=branch)
        )
        assert plan["conflicts"] and plan["change"] is None
        plan = await svc.maintenance_plan(
            sid,
            MaintenanceInput(
                action="branch_merge", base_version=6, branch_id=branch, choices={a["id"]: "source"}
            ),
        )
        await svc.adopt(sid, plan["change"]["id"], "branch-once")
        assert (await svc.entity(sid, a["id"]))["text"] == "分支结局"


async def test_workspace_retry_and_committed_history_guard(store):
    factory, ids = store
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        sid = (await svc.create_scope(ScopeInput(name="工作副本")))["id"]
        raw = b"# Original\n"
        request = {
            "format": "ncc.workspace/1",
            "base_version": 0,
            "request_id": "same-request",
            "files": [{"path": "notes.md", "base64": base64.b64encode(raw).decode(), "sha256": digest(raw)}],
        }
        receipt = await svc.workspace_commit(sid, request)
        assert await svc.workspace_commit(sid, request) == receipt
        snapshot = await svc.workspace_snapshot(sid)
        assert base64.b64decode(snapshot["files"][0]["base64"]) == raw
    async with factory() as db:
        with pytest.raises(DBAPIError):
            await db.execute(
                text("UPDATE ncc_revision SET content_hash='tampered' WHERE scope_id=:sid"), {"sid": sid}
            )
        await db.rollback()
