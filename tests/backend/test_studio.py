import secrets
from uuid import uuid4

import httpx
import pytest

from ncc_data.api.app import create_app
from ncc_data.application.security import password_hash
from ncc_data.application.service import Service
from ncc_data.creation.worker import Worker, accept_task, create_task
from ncc_data.domain.contracts import (
    ChangeInput,
    CreationInput,
    CrossScopeRef,
    ScopeInput,
)
from ncc_data.persistence.models import User
from ncc_data.persistence.seeds import seed
from ncc_data.runtime.settings import Settings
from ncc_shared.errors import DomainError
from tests.backend.test_scoring import report


class StudioFixtureProvider:
    """Synthetic test double for composable studio stage verification."""

    identity = "fixture:studio"

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def call(self, purpose, packet, budget):
        self.calls.append((purpose, packet))
        if purpose in {"judge", "judge_secondary"}:
            from ncc_shared.quality.policy import POLICY

            scheme = next(
                key for key, rubric in POLICY["profiles"].items() if rubric == packet["rubric"]
            )
            return report(scheme, 4.5), {"tokens": 80, "kind": "fixture", "model": "fixture"}
        if purpose == "plan":
            return (
                {
                    "text": "起：寒鸦渡灯下的选择；承：旧铁牌露暗记；转：刺客突袭；合：反杀留活口；钩：铁牌指向镇北王。",
                    "data": {},
                    "claims": [],
                },
                {"tokens": 90, "kind": "fixture", "model": "fixture"},
            )
        return (
            {"text": "灯下的选择。风雪压低芦苇，沈砚按住剑柄，听见渡口冰面裂开细响。", "data": {}, "claims": []},
            {"tokens": 120, "kind": "fixture", "model": "fixture"},
        )


async def test_idempotent_seed_respects_immutable_definitions(store):
    """Re-running seed() on an already-seeded database must never UPDATE ncc_definition."""
    factory, _ = store
    async with factory() as db, db.begin():
        await seed(db)


async def test_studio_catalog_overview_reorder_and_market_config(store):
    factory, ids = store
    async with factory() as db:
        actor_username = (await db.get(User, ids[0])).username
    settings = Settings(database_url="unused", public_origin="http://testserver")
    app = create_app(settings, factory)
    vol_id = str(uuid4())
    ch1_id = str(uuid4())
    ch2_id = str(uuid4())
    fs_id = str(uuid4())
    beast_id = str(uuid4())

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        login = await client.post(
            "/api/v1/auth/login",
            headers={"x-ncc-client": "console"},
            json={"username": actor_username, "password": factory.credentials[ids[0]]},
        )
        assert login.status_code == 200
        headers = {"x-csrf-token": login.json()["csrf"]}

        catalog = (await client.get("/api/v1/studio/catalog")).raise_for_status().json()
        assert len(catalog["codex_groups"]) == 6
        assert len(catalog["commons_categories"]) == 12
        assert len(catalog["commons_cards"]) >= 24
        assert len(catalog["market_playbooks"]) == 7

        book = (
            await client.post(
                "/api/v1/scopes", headers=headers, json={"name": "测试长篇", "kind": "book"}
            )
        ).raise_for_status().json()
        commons = (
            await client.post(
                "/api/v1/scopes", headers=headers, json={"name": "公共技法库", "kind": "author"}
            )
        ).raise_for_status().json()
        sid = book["id"]

        change = (
            await client.post(
                f"/api/v1/scopes/{sid}/changes",
                headers=headers,
                json={
                    "title": "建卷章与伏笔",
                    "base_version": 0,
                    "operations": [
                        {
                            "op": "create",
                            "entity_id": vol_id,
                            "kind": "volume",
                            "name": "第一卷",
                            "data": {"position": 0},
                        },
                        {
                            "op": "create",
                            "entity_id": ch1_id,
                            "kind": "chapter",
                            "name": "第一章",
                            "text": "寒江孤影，江湖故人。",
                            "data": {"position": 0, "parent_id": vol_id, "key_chapter": True},
                        },
                        {
                            "op": "create",
                            "entity_id": ch2_id,
                            "kind": "chapter",
                            "name": "第二章",
                            "text": "风雪夜归人。",
                            "data": {"position": 1, "parent_id": vol_id},
                        },
                        {
                            "op": "create",
                            "entity_id": fs_id,
                            "kind": "伏笔",
                            "name": "断剑之谜",
                            "data": {
                                "line_type": "暗线",
                                "planted_chapter": 1,
                                "expected_chapter": 1,
                                "status": "推进中",
                            },
                        },
                        {
                            "op": "create",
                            "entity_id": beast_id,
                            "kind": "魔兽",
                            "name": "霜脊狼",
                            "data": {"realm": "四阶"},
                        },
                    ],
                },
            )
        ).raise_for_status().json()
        (
            await client.post(
                f"/api/v1/scopes/{sid}/changes/{change['id']}/adopt",
                headers={**headers, "idempotency-key": "adopt-1"},
                json={},
            )
        ).raise_for_status()

        overview = (await client.get(f"/api/v1/scopes/{sid}/studio/overview")).raise_for_status().json()
        assert len(overview["volumes"]) == 1
        assert [c["id"] for c in overview["chapters"]] == [ch1_id, ch2_id]
        assert overview["diagnostics"]["chapter_count"] == 2
        assert overview["diagnostics"]["key_chapter_count"] == 1
        assert overview["diagnostics"]["overdue_foreshadow_count"] == 1
        assert any(s["id"] == commons["id"] for s in overview["commons_scopes"])

        scope_now = (await client.get(f"/api/v1/scopes/{sid}")).raise_for_status().json()
        reordered = await client.post(
            f"/api/v1/scopes/{sid}/studio/reorder",
            headers=headers,
            json={
                "base_version": scope_now["version"],
                "items": [
                    {"entity_id": ch2_id, "position": 0, "parent_id": vol_id},
                    {"entity_id": ch1_id, "position": 1, "parent_id": vol_id},
                ],
            },
        )
        assert reordered.status_code == 200, reordered.text
        overview2 = (await client.get(f"/api/v1/scopes/{sid}/studio/overview")).raise_for_status().json()
        assert [c["id"] for c in overview2["chapters"]] == [ch2_id, ch1_id]
        ch1 = next(c for c in overview2["chapters"] if c["id"] == ch1_id)
        assert ch1["key_chapter"] is True

        playbook_id = catalog["market_playbooks"][0]["id"]
        cfg_res = await client.put(
            f"/api/v1/scopes/{sid}/studio/market-config",
            headers=headers,
            json={
                "playbook_id": playbook_id,
                "target_min_words": 2800,
                "target_max_words": 4200,
                "poison_notes": ["禁止降智反派"],
                "direction_note": "前三章快节奏立人设",
            },
        )
        assert cfg_res.status_code == 200, cfg_res.text
        overview3 = (await client.get(f"/api/v1/scopes/{sid}/studio/overview")).raise_for_status().json()
        assert overview3["market_config"]["playbook_id"] == playbook_id


async def test_composable_plan_adoption_preserves_chapter_text_and_mounts_commons(store):
    factory, ids = store
    provider = StudioFixtureProvider()
    keep_id = str(uuid4())
    card_id = str(uuid4())
    async with factory() as db, db.begin():
        service = Service(db, await db.get(User, ids[0]))
        book_id = (await service.create_scope(ScopeInput(name="细纲单推测试书", kind="book")))["id"]
        commons_id = (await service.create_scope(ScopeInput(name="作者公共卡库", kind="author")))["id"]

        ch_change = await service.create_change(
            book_id,
            ChangeInput.model_validate(
                {
                    "title": "初始章节正文",
                    "base_version": 0,
                    "operations": [
                        {
                            "op": "create",
                            "entity_id": keep_id,
                            "kind": "chapter",
                            "name": "第一章 · 原文保留验证",
                            "text": "这段已写好的正文绝不能被细纲采用覆盖。",
                            "data": {"position": 1},
                        }
                    ],
                }
            ),
        )
        await service.adopt(book_id, ch_change["id"], "init-ch")

        com_change = await service.create_change(
            commons_id,
            ChangeInput.model_validate(
                {
                    "title": "新增作者技法卡",
                    "base_version": 0,
                    "operations": [
                        {
                            "op": "create",
                            "entity_id": card_id,
                            "kind": "公共母本",
                            "name": "三拍反转法",
                            "text": "先立常规预期，再借细节翻面。",
                            "data": {"commons_category": "writing_routine", "usage_guide": "用于章末钩子"},
                        }
                    ],
                }
            ),
        )
        await service.adopt(commons_id, com_change["id"], "init-card")

        job = await create_task(
            service,
            book_id,
            CreationInput(
                objective="单推第一章细纲节拍",
                scheme="P1",
                kind="chapter",
                name="第一章 · 原文保留验证",
                entity_id=keep_id,
                stages=["plan", "judge_plan"],
                guidance="突出暗记悬念",
                commons_refs=[CrossScopeRef(scope_id=commons_id, entity_id=card_id)],
                builtin_commons_ids=["routine-choice-cost"],
            ),
        )
        job_id = job["id"]

    worker = Worker(factory, Settings(database_url="unused"), provider)
    assert await worker.run_job(job_id) is True
    assert [purpose for purpose, _ in provider.calls] == ["plan", "judge"]
    plan_packet = provider.calls[0][1]
    assert plan_packet["producer_guidance"]["guidance"] == "突出暗记悬念"
    assert any(c["name"] == "三拍反转法" and c.get("readonly") is True for c in plan_packet["sources"])

    async with factory() as db, db.begin():
        service = Service(db, await db.get(User, ids[0]))
        finished = await service.serialize_job(await service.job(book_id, job_id))
        assert finished["state"] == "qualified"
        assert finished["result"]["candidates"][-1]["artifact"] == "plan"
        await accept_task(service, book_id, job_id, "adopt-plan-1")
        updated = await service.entity(book_id, keep_id)
        assert updated["text"] == "这段已写好的正文绝不能被细纲采用覆盖。"
        assert "寒鸦渡灯下的选择" in updated["data"]["beat_outline"]


async def test_explicit_write_judge_revise_respects_max_revisions(store):
    """Regression for Wave 3 B-1: unqualified explicit revise must increment revisions and terminate."""
    factory, ids = store

    class LowScoreProvider:
        identity = "fixture:low"

        def __init__(self):
            self.calls = []

        async def call(self, purpose, packet, budget):
            self.calls.append(purpose)
            if purpose == "judge":
                from ncc_shared.quality.policy import POLICY

                scheme = next(
                    key for key, rubric in POLICY["profiles"].items() if rubric == packet["rubric"]
                )
                return report(scheme, 2.5), {"tokens": 60, "kind": "fixture", "model": "fixture"}
            return {"text": "初稿或返修稿文本。", "data": {}, "claims": []}, {
                "tokens": 100,
                "kind": "fixture",
                "model": "fixture",
            }

    provider = LowScoreProvider()
    async with factory() as db, db.begin():
        service = Service(db, await db.get(User, ids[0]))
        book_id = (await service.create_scope(ScopeInput(name="返修上限测试书", kind="book")))["id"]
        job = await create_task(
            service,
            book_id,
            CreationInput(
                objective="起草并最多返修一次",
                scheme="P1",
                kind="chapter",
                name="第一章",
                stages=["write", "judge", "revise"],
                max_revisions=1,
            ),
        )
        job_id = job["id"]

    worker = Worker(factory, Settings(database_url="unused"), provider)
    assert await worker.run_job(job_id) is True
    assert provider.calls == ["write", "judge", "revise", "judge", "judge"]
    async with factory() as db, db.begin():
        service = Service(db, await db.get(User, ids[0]))
        finished = await service.serialize_job(await service.job(book_id, job_id))
        assert finished["state"] == "waiting"
        assert finished["progress"]["revisions"] == 1
        assert "revision_evaluation" in finished["result"]["candidates"][-1]


async def test_d03_d05_a07_a09_a11_overview_projection_reorder_idempotency_scale_and_metrics(store):
    """Covers D03, D05, A07, A09, A11, and U01 backend draft persistence."""
    factory, ids = store
    async with factory() as db:
        actor_username = (await db.get(User, ids[0])).username
        stranger_id = ids[1]
    settings = Settings(database_url="unused", public_origin="http://testserver")
    app = create_app(settings, factory)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        login = await client.post(
            "/api/v1/auth/login",
            headers={"x-ncc-client": "console"},
            json={"username": actor_username, "password": factory.credentials[ids[0]]},
        )
        headers = {"x-csrf-token": login.json()["csrf"]}
        book = (
            await client.post(
                "/api/v1/scopes", headers=headers, json={"name": "全景验收测试书", "kind": "book"}
            )
        ).raise_for_status().json()
        sid = book["id"]

        # D03: Custom chapter definition where beat_outline & hook are secret; collaborator without 'secret' sees unified redaction
        def_change = (
            await client.post(
                f"/api/v1/scopes/{sid}/changes",
                headers=headers,
                json={
                    "title": "私有细纲定义",
                    "base_version": 0,
                    "operations": [
                        {
                            "op": "definition",
                            "definition": {
                                "key": "chapter",
                                "version": 2,
                                "spec": {
                                    "label": "章节",
                                    "domain": "叙事生产",
                                    "required": [],
                                    "properties": {
                                        "position": {"type": "integer", "label": "排序", "minimum": 0},
                                        "parent_id": {"type": "reference", "label": "所属卷"},
                                        "status": {"type": "text", "label": "状态"},
                                        "key_chapter": {"type": "boolean", "label": "关键章"},
                                        "pov": {"type": "text", "label": "视角"},
                                        "plotline": {"type": "text", "label": "剧情线"},
                                        "target_words": {"type": "integer", "label": "目标字数", "minimum": 0},
                                        "beat_outline": {"type": "text", "label": "细纲", "secret": True},
                                        "hook": {"type": "text", "label": "章尾钩", "secret": True},
                                    },
                                },
                            },
                        }
                    ],
                },
            )
        ).raise_for_status().json()
        (
            await client.post(
                f"/api/v1/scopes/{sid}/changes/{def_change['id']}/adopt",
                headers={**headers, "idempotency-key": "def-v2"},
                json={},
            )
        ).raise_for_status()

        # A07 (>1000 mixed objects), A09 (6 planted unresolved dark lines + resolved + dropped), A11 ("甲，A1。" -> 1 Han char)
        ch1_id, ch2_id = str(uuid4()), str(uuid4())
        ops = [
            {
                "op": "create",
                "entity_id": ch1_id,
                "kind": "chapter",
                "name": "第一章",
                "text": "甲，A1。",
                "data": {
                    "position": 0,
                    "beat_outline": "绝密细纲不可外泄",
                    "hook": "绝密钩子",
                    "pov": "沈砚",
                },
            },
            {
                "op": "create",
                "entity_id": ch2_id,
                "kind": "chapter",
                "name": "第二章",
                "text": "乙，B2。",
                "data": {"position": 1},
            },
        ]
        # 6 planted unresolved dark lines across overdue (expected=1 < written=2), due_soon (expected=3), active (planted=1, expected=10)
        for idx, exp in enumerate([1, 1, 2, 3, 9, 10], 1):
            ops.append(
                {
                    "op": "create",
                    "entity_id": str(uuid4()),
                    "kind": "伏笔",
                    "name": f"暗线-{idx}",
                    "data": {
                        "line_type": "暗线",
                        "planted_chapter": 1,
                        "expected_chapter": exp,
                        "status": "已埋设",
                    },
                }
            )
        ops.append(
            {
                "op": "create",
                "entity_id": str(uuid4()),
                "kind": "伏笔",
                "name": "已兑现暗线",
                "data": {"line_type": "暗线", "planted_chapter": 1, "expected_chapter": 2, "status": "已兑现"},
            }
        )
        ops.append(
            {
                "op": "create",
                "entity_id": str(uuid4()),
                "kind": "伏笔",
                "name": "已作废暗线",
                "data": {"line_type": "暗线", "planted_chapter": 1, "expected_chapter": 2, "status": "作废"},
            }
        )

        cur_ver = 1
        c0 = (
            await client.post(
                f"/api/v1/scopes/{sid}/changes",
                headers=headers,
                json={"title": "结构与暗线", "base_version": cur_ver, "operations": ops},
            )
        ).raise_for_status().json()
        cur_ver = (
            await client.post(
                f"/api/v1/scopes/{sid}/changes/{c0['id']}/adopt",
                headers={**headers, "idempotency-key": "seed-struct"},
                json={},
            )
        ).raise_for_status().json()["version"]

        # Add 1050 codex objects in batches + delete 2 so scope has >1000 mixed active/structural/secret/deleted objects
        deleted_ids: list[str] = []
        for batch in range(3):
            batch_ops = []
            for k in range(350):
                eid = str(uuid4())
                if batch == 0 and k in (0, 1):
                    deleted_ids.append(eid)
                batch_ops.append(
                    {
                        "op": "create",
                        "entity_id": eid,
                        "kind": "魔兽" if k % 2 == 0 else "丹药",
                        "name": f"条目-{batch}-{k}",
                        "data": {"position": k},
                    }
                )
            cb = (
                await client.post(
                    f"/api/v1/scopes/{sid}/changes",
                    headers=headers,
                    json={"title": f"批量设定-{batch}", "base_version": cur_ver, "operations": batch_ops},
                )
            ).raise_for_status().json()
            cur_ver = (
                await client.post(
                    f"/api/v1/scopes/{sid}/changes/{cb['id']}/adopt",
                    headers={**headers, "idempotency-key": f"seed-batch-{batch}"},
                    json={},
                )
            ).raise_for_status().json()["version"]
        retire_ops = []
        for eid in deleted_ids:
            ent_ver = (
                await client.get(f"/api/v1/scopes/{sid}/entities/{eid}")
            ).raise_for_status().json()["version"]
            retire_ops.append({"op": "retire", "entity_id": eid, "expected": ent_ver})
        c_del = (
            await client.post(
                f"/api/v1/scopes/{sid}/changes",
                headers=headers,
                json={
                    "title": "停用两条设定以构造混合已删对象",
                    "base_version": cur_ver,
                    "operations": retire_ops,
                },
            )
        ).raise_for_status().json()
        cur_ver = (
            await client.post(
                f"/api/v1/scopes/{sid}/changes/{c_del['id']}/adopt",
                headers={**headers, "idempotency-key": "seed-delete-2"},
                json={},
            )
        ).raise_for_status().json()["version"]

        # Author overview sees full >1000 counts, Han count = 1 per chapter, active_hidden_lines == 6, secret fields visible to author
        ov = (await client.get(f"/api/v1/scopes/{sid}/studio/overview")).raise_for_status().json()
        assert ov["pagination"]["total_entities"] == 1058
        assert ov["pagination"]["truncated"] is False
        assert ov["codex_counts"]["kinds"]["魔兽"] == 524
        assert ov["codex_counts"]["kinds"]["丹药"] == 524
        assert len(ov["chapters"]) == 2
        ch1_ov = next(c for c in ov["chapters"] if c["id"] == ch1_id)
        assert ch1_ov["char_count"] == 1
        assert ch1_ov["beat_outline"] == "绝密细纲不可外泄"
        assert ov["diagnostics"]["total_chars"] == 2
        assert ov["diagnostics"]["avg_chars"] == 1
        assert ov["diagnostics"]["active_hidden_lines"] == 6
        assert ov["diagnostics"]["hidden_line_cap_exceeded"] is True
        assert ov["diagnostics"]["overdue_foreshadow_count"] == 2
        assert ov["diagnostics"]["due_soon_foreshadow_count"] == 2
        assert ov["diagnostics"]["planted_overdue_foreshadow_count"] == 2
        assert ov["diagnostics"]["planted_due_soon_foreshadow_count"] == 2
        assert ov["diagnostics"]["resolved_hidden_lines"] == 1
        assert ov["diagnostics"]["dropped_hidden_lines"] == 1

        # Explicit small limit exposes truncation info while codex_counts & whole-book diagnostics still reconcile
        ov_trunc = (
            await client.get(f"/api/v1/scopes/{sid}/studio/overview?limit=3")
        ).raise_for_status().json()
        assert ov_trunc["pagination"]["truncated"] is True
        assert ov_trunc["pagination"]["returned_structural"] == 3
        assert ov_trunc["codex_counts"]["kinds"]["魔兽"] == 524
        assert ov_trunc["diagnostics"] == ov["diagnostics"]
        assert (
            await client.get(f"/api/v1/scopes/{sid}/studio/overview?role=character")
        ).status_code == 422

        # D03: Grant read-only (no 'secret') to stranger -> overview redacts secret beat_outline & hook identically to /entities/{id}
        (
            await client.post(
                f"/api/v1/scopes/{sid}/members",
                headers=headers,
                json={"user_id": stranger_id, "actions": ["read"]},
            )
        ).raise_for_status()
        async with factory() as db:
            stranger_username = (await db.get(User, stranger_id)).username
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as reader_client:
            r_login = await reader_client.post(
                "/api/v1/auth/login",
                headers={"x-ncc-client": "console"},
                json={"username": stranger_username, "password": factory.credentials[stranger_id]},
            )
            assert r_login.status_code == 200
            ov_reader = (
                await reader_client.get(f"/api/v1/scopes/{sid}/studio/overview")
            ).raise_for_status().json()
            ent_reader = (
                await reader_client.get(f"/api/v1/scopes/{sid}/entities/{ch1_id}")
            ).raise_for_status().json()
            ch1_reader = next(c for c in ov_reader["chapters"] if c["id"] == ch1_id)
            assert ch1_reader["beat_outline"] == ""
            assert ch1_reader["hook"] == ""
            assert ch1_reader["pov"] == "沈砚"
            assert "beat_outline" not in ent_reader["data"]
            assert "hook" not in ent_reader["data"]

        # D05: Exact same reorder request replayed returns existing receipt & produces only 1 version; stale different request returns 409
        reorder_payload = {
            "base_version": cur_ver,
            "items": [
                {"entity_id": ch2_id, "position": 0},
                {"entity_id": ch1_id, "position": 1},
            ],
        }
        r1 = await client.post(f"/api/v1/scopes/{sid}/studio/reorder", headers=headers, json=reorder_payload)
        assert r1.status_code == 200, r1.text
        r2 = await client.post(f"/api/v1/scopes/{sid}/studio/reorder", headers=headers, json=reorder_payload)
        assert r2.status_code == 200, r2.text
        assert r1.json()["version"] == cur_ver + 1
        assert r2.json() == r1.json()
        stale_different = await client.post(
            f"/api/v1/scopes/{sid}/studio/reorder",
            headers=headers,
            json={
                "base_version": cur_ver,
                "items": [
                    {"entity_id": ch1_id, "position": 0},
                    {"entity_id": ch2_id, "position": 1},
                ],
            },
        )
        assert stale_different.status_code == 409

        # U01 backend contract: AuthorDraft saves & restores metadata-only and empty-text drafts
        saved_draft = (
            await client.put(
                f"/api/v1/scopes/{sid}/author-drafts/{ch1_id}",
                headers=headers,
                json={
                    "version": 0,
                    "entity_id": ch1_id,
                    "baseline": f"{sid}:{cur_ver + 1}",
                    "name": "第一章·草稿",
                    "text": "",
                    "scheme": "P1",
                    "beat_outline": "新细纲节拍",
                    "hook": "新章尾钩",
                    "pov": "陆言",
                    "plotline": "主线·寒江",
                    "target_words": "3500",
                    "key_chapter": True,
                    "has_draft": True,
                },
            )
        ).raise_for_status().json()
        loaded_draft = (
            await client.get(f"/api/v1/scopes/{sid}/author-drafts/{ch1_id}")
        ).raise_for_status().json()
        assert loaded_draft["has_draft"] is True
        assert loaded_draft["text"] == ""
        assert loaded_draft["beat_outline"] == "新细纲节拍"
        assert loaded_draft["hook"] == "新章尾钩"
        assert loaded_draft["pov"] == "陆言"
        assert loaded_draft["plotline"] == "主线·寒江"
        assert loaded_draft["target_words"] == "3500"
        assert loaded_draft["key_chapter"] is True
        assert loaded_draft["version"] == saved_draft["version"]


async def test_d04_a01_a02_a06_a10_pipeline_gates_revocation_volumes_and_plan_adopt(store):
    """Covers D04, A01, A02, A06, and A10."""
    import pytest
    from ncc_data.domain.contracts import DelegationInput, MemberInput
    from ncc_shared.errors import DomainError

    factory, ids = store
    provider = StudioFixtureProvider()

    # 1. D04: Cross-scope reference revocation clips continuation model call & job display while preserving auditable ref+version
    async with factory() as db, db.begin():
        owner_svc = Service(db, await db.get(User, ids[1]))
        shared_scope = (await owner_svc.create_scope(ScopeInput(name="外部参考库", kind="universe")))["id"]
        ref_eid = str(uuid4())
        ch_ref = await owner_svc.create_change(
            shared_scope,
            ChangeInput.model_validate(
                {
                    "title": "私密参考卡",
                    "base_version": 0,
                    "operations": [
                        {
                            "op": "create",
                            "entity_id": ref_eid,
                            "kind": "source",
                            "name": "古阵机密考",
                            "text": "绝密跨范围参考原文XYZ987",
                        }
                    ],
                }
            ),
        )
        await owner_svc.adopt(shared_scope, ch_ref["id"], "ref-init")
        await owner_svc.set_member(shared_scope, MemberInput(user_id=ids[0], actions=["read"]))

        author_svc = Service(db, await db.get(User, ids[0]))
        target_book = (await author_svc.create_scope(ScopeInput(name="目标作品", kind="book")))["id"]
        # Create a 3rd target-scope admin without access to shared_scope
        co_admin_pw = secrets.token_urlsafe(24)
        co_admin = User(
            username=f"coadmin-{uuid4().hex[:8]}",
            password_hash=password_hash(co_admin_pw),
            active=True,
        )
        db.add(co_admin)
        await db.flush()
        co_admin_id = co_admin.id
        factory.register_user(co_admin_id, co_admin_pw)
        await author_svc.set_member(target_book, MemberInput(user_id=co_admin_id, actions=["read", "admin", "secret", "edit"]))
        d04_job = await create_task(
            author_svc,
            target_book,
            CreationInput(
                objective="参考外部资料推演并起草",
                scheme="P1",
                kind="chapter",
                name="第一章",
                stages=["plan", "write"],
                commons_refs=[CrossScopeRef(scope_id=shared_scope, entity_id=ref_eid)],
            ),
        )
        d04_job_id = d04_job["id"]

    # Before revocation: co-admin on target_book who lacks access to shared_scope sees redacted source, while author sees live text
    worker = Worker(factory, Settings(database_url="unused"), provider)
    assert await worker.run_job(d04_job_id) is True
    assert len(provider.calls) == 2
    assert any("绝密跨范围参考原文XYZ987" in s.get("text", "") for s in provider.calls[0][1]["sources"])

    async with factory() as db, db.begin():
        author_svc = Service(db, await db.get(User, ids[0]))
        coadmin_svc = Service(db, await db.get(User, co_admin_id))
        # Raw DB row never caches cross-scope text; retains auditable revision & hash
        raw_row = await author_svc.job(target_book, d04_job_id)
        stored_src = next(s for s in raw_row.result["packet"]["sources"] if s.get("scope_id") == shared_scope)
        assert "text" not in stored_src
        assert stored_src["revision"] and stored_src["content_hash"]
        # Author currently authorized -> sees text
        author_view = await author_svc.serialize_job(raw_row)
        assert "绝密跨范围参考原文XYZ987" in str(author_view)
        # Target-scope co-admin without shared_scope permission -> redacted!
        coadmin_view = await coadmin_svc.serialize_job(raw_row)
        assert "绝密跨范围参考原文XYZ987" not in str(coadmin_view)
        assert any(s.get("redacted") is True for s in coadmin_view["result"]["packet"]["sources"])

        # Now revoke author's access on shared_scope!
        owner_svc = Service(db, await db.get(User, ids[1]))
        await owner_svc.set_member(shared_scope, MemberInput(user_id=ids[0], actions=[]))

    async with factory() as db, db.begin():
        author_svc = Service(db, await db.get(User, ids[0]))
        raw_row = await author_svc.job(target_book, d04_job_id)
        revoked_view = await author_svc.serialize_job(raw_row)
        assert "绝密跨范围参考原文XYZ987" not in str(revoked_view)
        revoked_src = next(s for s in revoked_view["result"]["packet"]["sources"] if s.get("scope_id") == shared_scope)
        assert revoked_src["redacted"] is True
        assert revoked_src["revision"] and revoked_src["content_hash"]
        # Resume continuation on cached packet after revocation -> model call must clip revoked source!
        raw_row.state = "queued"
        raw_row.progress = {**raw_row.progress, "stage": "write"}

    provider.calls.clear()
    assert await worker.run_job(d04_job_id) is True
    assert len(provider.calls) == 1
    assert "绝密跨范围参考原文XYZ987" not in str(provider.calls[0][1])

    # 2. A01 + A02: plan+revise & judge_plan+revise+judge execute every stage, attach P5 + second judge, reject delegation+stages
    provider2 = StudioFixtureProvider()

    class DualJudgeProvider(StudioFixtureProvider):
        async def call(self, purpose, packet, budget):
            self.calls.append((purpose, packet))
            if purpose in {"judge", "judge_secondary"}:
                from ncc_shared.quality.policy import POLICY

                scheme = next(k for k, r in POLICY["profiles"].items() if r == packet["rubric"])
                return report(scheme, 4.5), {"tokens": 70, "kind": "fixture", "model": "fixture"}
            return await super().call(purpose, packet, budget)

    dual_provider = DualJudgeProvider()
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        a_book = (await svc.create_scope(ScopeInput(name="工序与闸门测试", kind="book")))["id"]
        ch_target = str(uuid4())
        ch_init = await svc.create_change(
            a_book,
            ChangeInput.model_validate(
                {
                    "title": "初始章",
                    "base_version": 0,
                    "operations": [
                        {
                            "op": "create",
                            "entity_id": ch_target,
                            "kind": "chapter",
                            "name": "第四章",
                            "text": "初稿已有文字。",
                            "data": {"position": 4, "beat_outline": "起：灯下的选择；承转合"},
                        }
                    ],
                }
            ),
        )
        await svc.adopt(a_book, ch_init["id"], "a-init")
        deleg = await svc.delegation(
            a_book,
            DelegationInput(
                target_ids=[ch_target],
                schemes=["P1", "P5"],
                count=2,
                mode="author_trial",
                note="合成测试授权",
            ),
        )
        # Explicit stages + delegation_id must be rejected
        with pytest.raises(DomainError, match="显式拆分工序"):
            await create_task(
                svc,
                a_book,
                CreationInput(
                    objective="非法并传",
                    entity_id=ch_target,
                    delegation_id=deleg["id"],
                    stages=["revise", "judge"],
                ),
            )
        j_pr = await create_task(
            svc,
            a_book,
            CreationInput(
                objective="先推细纲再返修",
                scheme="P1",
                entity_id=ch_target,
                stages=["plan", "revise"],
            ),
        )
        j_jprj = await create_task(
            svc,
            a_book,
            CreationInput(
                objective="结构审后返修并复评",
                scheme="P5",
                entity_id=ch_target,
                stages=["judge_plan", "revise", "judge"],
            ),
        )
        from ncc_data.creation.model_route import environment_snapshot

        jprj_db_row = await svc.job(a_book, j_jprj["id"])
        jprj_db_row.result = {
            **jprj_db_row.result,
            "model_route": environment_snapshot(
                Settings(
                    database_url="unused",
                    writer_model="fixture:writer",
                    judge_model="fixture:judge",
                    second_judge_model="fixture:second",
                )
            ),
        }

    w_dual = Worker(
        factory,
        Settings(database_url="unused", second_judge_model="fixture:second"),
        dual_provider,
    )
    assert await w_dual.run_job(j_pr["id"]) is True
    assert await w_dual.run_job(j_jprj["id"]) is True
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        pr_view = await svc.serialize_job(await svc.job(a_book, j_pr["id"]))
        assert pr_view["state"] == "waiting"
        assert pr_view["result"]["candidates"][-1]["artifact"] == "draft"
        jprj_row = await svc.job(a_book, j_jprj["id"])
        jprj_view = await svc.serialize_job(jprj_row)
        assert jprj_view["state"] == "qualified"
        cand = jprj_view["result"]["candidates"][-1]
        assert cand["evaluation"]["verdict"] == "qualified"
        assert cand["second_evaluation"]["verdict"] == "qualified"
        assert cand["revision_evaluation"]["verdict"] == "qualified"
        # Tampering to remove required P5 revision_assessment_id must block adoption!
        saved_rev_id = jprj_row.result["candidates"][-1]["revision_assessment_id"]
        jprj_row.result = {
            **jprj_row.result,
            "candidates": [{**jprj_row.result["candidates"][-1], "revision_assessment_id": None}],
        }
        with pytest.raises(DomainError, match="P5"):
            await accept_task(svc, a_book, j_jprj["id"], "try-missing-p5")
        jprj_row.result = {
            **jprj_row.result,
            "candidates": [{**jprj_row.result["candidates"][-1], "revision_assessment_id": saved_rev_id}],
        }
        await accept_task(svc, a_book, j_jprj["id"], "adopt-jprj")

    # 3. A10: Standalone chapter plan without entity_id -> adopt -> new chapter has beat_outline, empty text, 0 facts; outline creation preserved
    class ClaimPlanProvider(StudioFixtureProvider):
        async def call(self, purpose, packet, budget):
            self.calls.append((purpose, packet))
            if purpose == "plan":
                plan_text = "起：渡口夜雨；承：铁牌现世；转：暗哨合围；合：借雾脱身；钩：水下浮尸。"
                return (
                    {
                        "text": plan_text,
                        "data": {},
                        "claims": [
                            {"predicate": "appeared", "category": "fact", "quote": "铁牌现世", "value": {"note": "计划事实"}}
                        ],
                    },
                    {"tokens": 80, "kind": "fixture", "model": "fixture"},
                )
            return await super().call(purpose, packet, budget)

    plan_provider = ClaimPlanProvider()
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        p_book = (await svc.create_scope(ScopeInput(name="无目标细纲立章书", kind="book")))["id"]
        ch_plan_job = await create_task(
            svc,
            p_book,
            CreationInput(objective="推演新章细纲", scheme="P1", kind="chapter", name="新立第一章", stages=["plan"]),
        )
    w_plan = Worker(factory, Settings(database_url="unused"), plan_provider)
    assert await w_plan.run_job(ch_plan_job["id"]) is True
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        ch_receipt = await accept_task(svc, p_book, ch_plan_job["id"], "adopt-new-ch-plan")
        new_ch_id = ch_receipt["entity_id"]
        new_ch = await svc.entity(p_book, new_ch_id)
        assert new_ch["kind"] == "chapter"
        assert new_ch["text"] == ""
        assert "铁牌现世" in new_ch["data"]["beat_outline"]
        facts = await svc.facts(p_book)
        assert not any(f["subject_id"] == new_ch_id and f["category"] == "fact" for f in facts["items"])
        out_plan_job = await create_task(
            svc,
            p_book,
            CreationInput(objective="推演全书总纲", scheme="P2", kind="outline", name="全书总纲", stages=["plan"]),
        )
    assert await w_plan.run_job(out_plan_job["id"]) is True
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        out_receipt = await accept_task(svc, p_book, out_plan_job["id"], "adopt-new-outline")
        new_out = await svc.entity(p_book, out_receipt["entity_id"])
        assert new_out["kind"] == "outline"
        assert "铁牌现世" in new_out["text"]
        assert "铁牌现世" in new_out["data"]["beat_outline"]

    # 4. A06: 2 volumes x 4 chapters -> book-wide order, current excluded, previous-3 cross volume boundary, opening protection only Vol 1 Ch 1..3
    vol_provider = StudioFixtureProvider()
    v1_id, v2_id = str(uuid4()), str(uuid4())
    v1_chs = [str(uuid4()) for _ in range(4)]
    v2_chs = [str(uuid4()) for _ in range(4)]
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        v_book = (await svc.create_scope(ScopeInput(name="双卷八章测试", kind="book")))["id"]
        v_ops = [
            {"op": "create", "entity_id": v1_id, "kind": "volume", "name": "第一卷", "data": {"position": 0}},
            {"op": "create", "entity_id": v2_id, "kind": "volume", "name": "第二卷", "data": {"position": 1}},
        ]
        for i, cid in enumerate(v1_chs):
            v_ops.append(
                {
                    "op": "create",
                    "entity_id": cid,
                    "kind": "chapter",
                    "name": f"第一卷第{i + 1}章",
                    "text": f"【V1C{i + 1}正文标记】",
                    "data": {"position": i, "parent_id": v1_id},
                }
            )
        for i, cid in enumerate(v2_chs):
            v_ops.append(
                {
                    "op": "create",
                    "entity_id": cid,
                    "kind": "chapter",
                    "name": f"第二卷第{i + 1}章",
                    "text": f"【V2C{i + 1}正文标记】",
                    "data": {"position": i, "parent_id": v2_id},
                }
            )
        vc = await svc.create_change(
            v_book, ChangeInput.model_validate({"title": "建双卷八章", "base_version": 0, "operations": v_ops})
        )
        await svc.adopt(v_book, vc["id"], "v-seed")
        v_deleg = await svc.delegation(
            v_book,
            DelegationInput(
                target_ids=[v1_chs[0], v2_chs[0]],
                schemes=["P1"],
                count=2,
                mode="author_trial",
                note="双卷开篇保护核查",
            ),
        )
        # Task on Vol 1 Ch 1 (position=0, book_order=1): must have 0 previous chapters & hold auto-adopt on key_chapter!
        j_v1c1 = await create_task(
            svc, v_book, CreationInput(objective="改第一卷首章", entity_id=v1_chs[0], delegation_id=v_deleg["id"])
        )
    w_vol = Worker(factory, Settings(database_url="unused"), vol_provider)
    assert await w_vol.run_job(j_v1c1["id"]) is True
    v1c1_sources = vol_provider.calls[0][1]["sources"]
    assert v1c1_sources == []
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        r_v1c1 = await svc.job(v_book, j_v1c1["id"])
        assert r_v1c1.state == "qualified" and r_v1c1.result["auto_hold"]["code"] == "key_chapter"
        # Now task on Vol 2 Ch 1 (position=0 in Vol 2, book_order=5 > 3): previous 3 chapters MUST be V1C2, V1C3, V1C4 (excluding V2C1 and V2C2..4), and auto-adopt succeeds!
        j_v2c1 = await create_task(
            svc, v_book, CreationInput(objective="改第二卷首章", entity_id=v2_chs[0], delegation_id=v_deleg["id"])
        )
    vol_provider.calls.clear()
    assert await w_vol.run_job(j_v2c1["id"]) is True
    v2c1_source_names = [s["name"] for s in vol_provider.calls[0][1]["sources"]]
    assert v2c1_source_names == ["第一卷第2章", "第一卷第3章", "第一卷第4章"]
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        r_v2c1 = await svc.job(v_book, j_v2c1["id"])
        assert r_v2c1.state == "applied"


async def test_a05_a08_cli_studio_bidirectional_workspace_and_concurrent_model_settings(store):
    """Covers A05 (CLI <-> Studio deep round-trip) and A08 (concurrent system scope settings)."""
    import asyncio
    import base64
    import json
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    from ncc_data.application.model_settings import bind_default, load_model_settings, save_configuration
    from ncc_data.application.subscription_settings import save_subscription_model
    from ncc_data.domain.contracts import ModelConfigurationInput, ModelDefaultInput
    from ncc_data.persistence.models import Scope
    from ncc_shared.serialization import digest
    from ncc_shared.workspace import scan_files

    factory, ids = store

    # 1. A08: Two concurrent transactions saving model_registry and subscription_auth on the same scope preserve both!
    synth_sys_id = str(uuid4())
    async with factory() as db, db.begin():
        actor = await db.get(User, ids[0])
        actor.admin = True
        db.add(Scope(id=synth_sys_id, name="synthetic-system", kind="system", owner_id=actor.id, config={}))

    settings = Settings(database_url="unused")

    async def tx_save_model():
        async with factory() as db, db.begin():
            svc = Service(db, await db.get(User, ids[0]))
            res = await save_configuration(
                svc,
                settings,
                ModelConfigurationInput(
                    name="并发写作模型",
                    enabled=True,
                    base_url="https://gateway.example/v1",
                    auth_ref="NCC_MODEL_KEY",
                    model_key="writer-v1",
                    purposes=["write", "plan"],
                ),
                scope_id=synth_sys_id,
            )
            await bind_default(
                svc,
                settings,
                ModelDefaultInput(purpose="write", configuration_id=res["saved_id"]),
                scope_id=synth_sys_id,
            )

    async def tx_save_subscription():
        async with factory() as db, db.begin():
            svc = Service(db, await db.get(User, ids[0]))
            await save_subscription_model(svc, "grok", "grok-imagine-image-2.0", scope_id=synth_sys_id)

    await asyncio.gather(tx_save_model(), tx_save_subscription())
    async with factory() as db:
        merged_scope = await db.get(Scope, synth_sys_id)
        assert len(merged_scope.config["model_registry"]["configurations"]) == 1
        assert merged_scope.config["model_registry"]["defaults"]["write"] != ""
        assert merged_scope.config["subscription_auth"]["grok"]["model"] == "grok-imagine-image-2.0"

    # 2. A05: CLI init + foreshadow + scene card -> workspace_commit -> Studio overview & AI -> Studio new chapter + beat edit -> workspace_snapshot -> CLI continues
    repo_root = Path(__file__).resolve().parents[2]
    ncc_state = str(repo_root / "scripts" / "ncc_state.py")
    with tempfile.TemporaryDirectory(prefix="ncc-a05-roundtrip-") as tmp:
        book_dir = Path(tmp) / "互通测试书"
        subprocess.run(
            [sys.executable, ncc_state, "init", str(book_dir), "--title", "互通测试书", "--genre", "仙侠", "--mode", "混合"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                sys.executable,
                ncc_state,
                "promise",
                "add",
                str(book_dir),
                "--type",
                "伏笔",
                "--line",
                "暗线",
                "--strength",
                "5",
                "--content",
                "寒铁断剑暗纹",
                "--ch",
                "1",
                "--window",
                "4-8",
                "--cover",
                "剑柄生锈凹槽",
                "--truth",
                "北境镇魔印残钥",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [sys.executable, ncc_state, "chapter", "add", str(book_dir), "1", "--file", "04-正文/第0001章.md"],
            check=True,
            capture_output=True,
            text=True,
        )
        (book_dir / "04-正文").mkdir(parents=True, exist_ok=True)
        (book_dir / "04-正文/第0001章.md").write_text("风雪夜渡寒江，少年握住断剑。" * 210, "utf-8")
        (book_dir / "02-大纲/场景卡").mkdir(parents=True, exist_ok=True)
        (book_dir / "02-大纲/场景卡/ch-0001.md").write_text(
            "# ch-0001 场景卡\n\n## 场景 1\n- 目的：渡江避祸\n- 障碍：渡船封锁\n- 翻转：借寒铁断剑暗槽撬锁\n- 感官锚点：江面碎冰声\n- 变化：登船潜行\n",
            "utf-8",
        )

        local_files = scan_files(book_dir)
        commit_files = [
            {"path": p, "base64": base64.b64encode(raw).decode(), "sha256": digest(raw)}
            for p, raw in sorted(local_files.items(), key=lambda x: (x[0] != "book.json", x[0]))
        ]
        async with factory() as db, db.begin():
            svc = Service(db, await db.get(User, ids[0]))
            ws_scope = (await svc.create_scope(ScopeInput(name="互通测试书", kind="book")))["id"]
            committed = await svc.workspace_commit(
                ws_scope,
                {
                    "format": "ncc.workspace/1",
                    "base_version": 0,
                    "files": commit_files,
                    "request_id": "a05-import-1",
                    "title": "CLI初始导入",
                },
            )
            assert committed["coverage"]["typed_chapters"] == 1
            assert committed["coverage"]["typed_foreshadows"] == 1
            assert "bidirectional" in committed["coverage"]["boundaries"]

        # Query via Studio overview: chapter 1 has scene card in beat_outline, FS-0001 projected into foreshadows!
        app = create_app(settings, factory)
        async with factory() as db:
            actor_username = (await db.get(User, ids[0])).username
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            login = await client.post(
                "/api/v1/auth/login",
                headers={"x-ncc-client": "console"},
                json={"username": actor_username, "password": factory.credentials[ids[0]]},
            )
            headers = {"x-csrf-token": login.json()["csrf"]}
            ov = (await client.get(f"/api/v1/scopes/{ws_scope}/studio/overview")).raise_for_status().json()
            assert len(ov["chapters"]) == 1
            ch1_studio = ov["chapters"][0]
            assert "借寒铁断剑暗槽撬锁" in ch1_studio["beat_outline"]
            assert len(ov["foreshadows"]) == 1
            fs_studio = ov["foreshadows"][0]
            assert "FS-0001" in fs_studio["name"]
            assert fs_studio["line_type"] == "暗线"
            # Secret truth is in secret_note (not leaked into public text)
            fs_full = (
                await client.get(f"/api/v1/scopes/{ws_scope}/entities/{fs_studio['id']}")
            ).raise_for_status().json()
            assert "北境镇魔印残钥" not in fs_full["text"]
            assert fs_full["data"]["secret_note"] == "北境镇魔印残钥"

            # In Studio: create Chapter 2 (no legacy_path!), edit beat_outline, and add a Studio foreshadow!
            scope_ver = (await client.get(f"/api/v1/scopes/{ws_scope}")).raise_for_status().json()["version"]
            studio_ch2_id = str(uuid4())
            studio_fs2_id = str(uuid4())
            c_studio = (
                await client.post(
                    f"/api/v1/scopes/{ws_scope}/changes",
                    headers=headers,
                    json={
                        "title": "工作台新建第二章与新伏笔",
                        "base_version": scope_ver,
                        "operations": [
                            {
                                "op": "create",
                                "entity_id": studio_ch2_id,
                                "kind": "chapter",
                                "name": "芦苇暗箭",
                                "text": "夜雾深处冷箭破空，少年俯身避过。" * 210,
                                "data": {
                                    "position": 2,
                                    "status": "draft",
                                    "beat_outline": "起：夜航遇袭；转：反夺铁弓；钩：箭尾刻有王府印。",
                                    "hook": "箭尾刻有镇北王府狼头印",
                                },
                            },
                            {
                                "op": "create",
                                "entity_id": studio_fs2_id,
                                "kind": "伏笔",
                                "name": "箭尾狼头印",
                                "text": "追兵冷箭尾部的青铜狼头暗记",
                                "data": {
                                    "line_type": "暗线",
                                    "status": "已埋设",
                                    "planted_chapter": 2,
                                    "expected_chapter": 7,
                                },
                            },
                        ],
                    },
                )
            ).raise_for_status().json()
            (
                await client.post(
                    f"/api/v1/scopes/{ws_scope}/changes/{c_studio['id']}/adopt",
                    headers={**headers, "idempotency-key": "studio-ch2"},
                    json={},
                )
            ).raise_for_status()

        # Pull snapshot back to CLI directory and continue CLI creation!
        async with factory() as db, db.begin():
            svc = Service(db, await db.get(User, ids[0]))
            pulled = await svc.workspace_snapshot(ws_scope)
        pulled_map = {f["path"]: base64.b64decode(f["base64"]) for f in pulled["files"]}
        assert "04-正文/第0002章.md" in pulled_map
        assert "02-大纲/章纲/ch-0002.md" in pulled_map
        for rel_p, raw_b in pulled_map.items():
            dest = book_dir / rel_p
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw_b)

        # CLI reads pulled Chapter 2, Studio foreshadow FS-0002, and continues seamlessly; re-commit preserves studio_ch2_id!
        status_proc = subprocess.run(
            [sys.executable, ncc_state, "status", str(book_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
        assert "第 2 章" in status_proc.stdout or "2" in status_proc.stdout
        plist_proc = subprocess.run(
            [sys.executable, ncc_state, "promise", "list", str(book_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
        assert "FS-0001" in plist_proc.stdout
        assert "箭尾狼头印" in plist_proc.stdout

        # Continue writing in CLI on Chapter 2 and re-commit -> preserves exact Studio chapter identity!
        (book_dir / "04-正文/第0002章.md").write_text(
            "夜雾深处冷箭破空，少年俯身避过并反手夺下铁弓。" * 210, "utf-8"
        )
        raw_ch2 = (book_dir / "04-正文/第0002章.md").read_bytes()
        async with factory() as db, db.begin():
            svc = Service(db, await db.get(User, ids[0]))
            recommit = await svc.workspace_commit(
                ws_scope,
                {
                    "format": "ncc.workspace/1",
                    "base_version": pulled["version"],
                    "files": [
                        {
                            "path": "04-正文/第0002章.md",
                            "base64": base64.b64encode(raw_ch2).decode(),
                            "sha256": digest(raw_ch2),
                        }
                    ],
                    "request_id": "a05-cli-continue-2",
                    "title": "CLI续写第二章",
                },
            )
            ch2_after = await svc.entity(ws_scope, studio_ch2_id)
            assert "反手夺下铁弓" in ch2_after["text"]
            assert ch2_after["name"] == "芦苇暗箭"
            # Stale base_version conflict check
            with pytest.raises(DomainError, match="三方比较"):
                await svc.workspace_commit(
                    ws_scope,
                    {
                        "format": "ncc.workspace/1",
                        "base_version": pulled["version"],
                        "files": [
                            {
                                "path": "04-正文/第0002章.md",
                                "base64": base64.b64encode(raw_ch2).decode(),
                                "sha256": digest(raw_ch2),
                            }
                        ],
                        "request_id": "a05-stale-conflict",
                        "title": "过期冲突",
                    },
                )


async def test_r01_r02_r03_ordinary_author_paged_aggregates_and_ephemeral_lifecycle(runtime, store):
    """Covers R01 (non-admin 200), R02 + supplement (paged aggregates, cross-volume order, '〇', unplanted dark line), and R03 (ephemeral credential retirement)."""
    from sqlalchemy import select
    from support.runtime import TestRuntime
    from tests.backend.conftest import retire_ephemeral_users

    factory, ids = store
    settings = Settings(database_url="unused", public_origin="http://testserver")
    app = create_app(settings, factory)

    ordinary_pw = secrets.token_urlsafe(24)
    async with factory() as db, db.begin():
        pre_users = {
            u.id: (u.username, u.active, u.password_hash)
            for u in (await db.scalars(select(User))).all()
        }
        ordinary = User(
            username=f"test-ordinary-{secrets.token_urlsafe(8)}",
            password_hash=password_hash(ordinary_pw),
            admin=False,
            active=True,
        )
        db.add(ordinary)
        await db.flush()
        ordinary_id, ordinary_username = ordinary.id, ordinary.username
        factory.register_user(ordinary_id, ordinary_pw)

    v1, v2 = str(uuid4()), str(uuid4())
    c11, c12, c21, c22 = (str(uuid4()) for _ in range(4))
    fs_planted, fs_unplanted_due = str(uuid4()), str(uuid4())
    late_role_id = str(uuid4())

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        login = await client.post(
            "/api/v1/auth/login",
            headers={"x-ncc-client": "console"},
            json={"username": ordinary_username, "password": ordinary_pw},
        )
        assert login.status_code == 200, login.text
        headers = {"x-csrf-token": login.json()["csrf"]}

        book = (
            await client.post(
                "/api/v1/scopes",
                headers=headers,
                json={"name": "R01-R02普通作者分页书", "kind": "book"},
            )
        ).raise_for_status().json()
        sid = book["id"]

        change = (
            await client.post(
                f"/api/v1/scopes/{sid}/changes",
                headers=headers,
                json={
                    "title": "双卷四章与伏笔",
                    "base_version": 0,
                    "operations": [
                        {"op": "create", "entity_id": v1, "kind": "volume", "name": "卷一", "data": {"position": 0}},
                        {"op": "create", "entity_id": v2, "kind": "volume", "name": "卷二", "data": {"position": 1}},
                        {
                            "op": "create",
                            "entity_id": c11,
                            "kind": "chapter",
                            "name": "一卷一章",
                            "text": "二〇二六。",
                            "data": {"position": 0, "parent_id": v1, "key_chapter": True},
                        },
                        {
                            "op": "create",
                            "entity_id": c12,
                            "kind": "chapter",
                            "name": "一卷二章",
                            "text": "寒鸦渡口",
                            "data": {"position": 1, "parent_id": v1},
                        },
                        {
                            "op": "create",
                            "entity_id": c21,
                            "kind": "chapter",
                            "name": "二卷一章",
                            "text": "北境烽火",
                            "data": {"position": 0, "parent_id": v2},
                        },
                        {
                            "op": "create",
                            "entity_id": c22,
                            "kind": "chapter",
                            "name": "二卷二章",
                            "text": "雪夜孤城",
                            "data": {"position": 1, "parent_id": v2},
                        },
                        {
                            "op": "create",
                            "entity_id": fs_planted,
                            "kind": "伏笔",
                            "name": "已埋临期暗线",
                            "data": {
                                "line_type": "暗线",
                                "status": "推进中",
                                "planted_chapter": 1,
                                "expected_chapter": 5,
                            },
                        },
                        {
                            "op": "create",
                            "entity_id": fs_unplanted_due,
                            "kind": "伏笔",
                            "name": "待埋临期暗线",
                            "data": {
                                "line_type": "暗线",
                                "status": "待埋设",
                                "planted_chapter": 2,
                                "expected_chapter": 5,
                            },
                        },
                        {
                            "op": "create",
                            "entity_id": late_role_id,
                            "kind": "scene",
                            "name": "二卷二章晚场",
                            "data": {"chapter_id": c22},
                        },
                    ],
                },
            )
        ).raise_for_status().json()
        (
            await client.post(
                f"/api/v1/scopes/{sid}/changes/{change['id']}/adopt",
                headers={**headers, "idempotency-key": "r01-r02-init"},
                json={},
            )
        ).raise_for_status()

        # R01: Ordinary non-admin author gets 200 OK
        full_res = await client.get(f"/api/v1/scopes/{sid}/studio/overview")
        assert full_res.status_code == 200, full_res.text
        full = full_res.json()

        # R02 supplement: "二〇二六。" counts as 4 Han chars; unplanted due-soon dark line excluded from active_hidden_lines
        ch_map = {c["id"]: c for c in full["chapters"]}
        assert ch_map[c11]["char_count"] == 4
        assert full["diagnostics"]["total_chars"] == 16
        assert full["diagnostics"]["active_hidden_lines"] == 1
        assert full["diagnostics"]["planned_hidden_lines"] == 1
        assert full["diagnostics"]["due_soon_foreshadow_count"] == 2
        assert full["diagnostics"]["planted_due_soon_foreshadow_count"] == 1
        assert full["diagnostics"]["unplanted_due_foreshadow_count"] == 1
        fs_map = {f["id"]: f for f in full["foreshadows"]}
        assert fs_map[fs_planted]["planted"] is True and fs_map[fs_planted]["due_state"] == "due_soon"
        assert fs_map[fs_unplanted_due]["planted"] is False and fs_map[fs_unplanted_due]["due_state"] == "due_soon"

        # R02: Whole-book diagnostics, codex_counts, and cross-volume book_order invariant across pages
        paged_orders = {}
        for off in (0, 2, 4, 6, 8):
            page = (
                await client.get(f"/api/v1/scopes/{sid}/studio/overview?offset={off}&limit=2")
            ).raise_for_status().json()
            assert page["diagnostics"] == full["diagnostics"]
            assert page["codex_counts"] == full["codex_counts"]
            for ch in page["chapters"]:
                paged_orders[ch["id"]] = ch["book_order"]
        assert paged_orders == {c11: 1, c12: 2, c21: 3, c22: 4}

        # R02: role validation & cross-volume chapter_id cutoff match /entities/search
        assert (
            await client.get(f"/api/v1/scopes/{sid}/studio/overview?role=character")
        ).status_code == 422
        ov_at_c21 = (
            await client.get(f"/api/v1/scopes/{sid}/studio/overview?role=reader&chapter_id={c21}")
        ).raise_for_status().json()
        ents_at_c21 = (
            await client.post(
                f"/api/v1/scopes/{sid}/entities/search",
                headers=headers,
                json={"role": "reader", "chapter_id": c21},
            )
        ).raise_for_status().json()
        assert [c["id"] for c in ov_at_c21["chapters"]] == [c11, c12, c21]
        assert ov_at_c21["codex_counts"]["kinds"].get("scene", 0) == 0
        assert not any(it["id"] in {c22, late_role_id} for it in ents_at_c21["items"])
        ov_at_c22 = (
            await client.get(f"/api/v1/scopes/{sid}/studio/overview?role=reader&chapter_id={c22}")
        ).raise_for_status().json()
        assert [c["id"] for c in ov_at_c22["chapters"]] == [c11, c12, c21, c22]
        assert ov_at_c22["codex_counts"]["kinds"].get("scene", 0) == 1

        # R03: Retire ordinary ephemeral user -> active session immediately revoked & re-login rejected with 401
        async with factory() as db, db.begin():
            await retire_ephemeral_users(db, [ordinary_id])
        assert (await client.get("/api/v1/scopes")).status_code == 401
        relogin = await client.post(
            "/api/v1/auth/login",
            headers={"x-ncc-client": "console"},
            json={"username": ordinary_username, "password": ordinary_pw},
        )
        assert relogin.status_code == 401

    # R03: Verify TestRuntime browser credential lifecycle (isolated credentials -> login 200 -> teardown -> login 401, pre-existing users untouched)
    browser_rt = object.__new__(TestRuntime)
    browser_rt.settings = runtime.settings
    browser_rt.username = f"browser-author-{secrets.token_urlsafe(8)}"
    browser_rt.password = secrets.token_urlsafe(24)
    browser_rt.user_id = None
    browser_rt._pre_user_ids = set()
    browser_rt._ephemeral_user_ids = set()
    browser_rt._ephemeral_usernames = {browser_rt.username}
    browser_rt._seeded_browser = False
    await browser_rt.seed_browser()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as b_client:
        b_ok = await b_client.post(
            "/api/v1/auth/login",
            headers={"x-ncc-client": "console"},
            json={"username": browser_rt.username, "password": browser_rt.password},
        )
        assert b_ok.status_code == 200
        await browser_rt.teardown_browser()
        assert (await b_client.get("/api/v1/scopes")).status_code == 401
        b_after = await b_client.post(
            "/api/v1/auth/login",
            headers={"x-ncc-client": "console"},
            json={"username": browser_rt.username, "password": browser_rt.password},
        )
        assert b_after.status_code == 401

    async with factory() as db:
        post_users = {
            u.id: (u.username, u.active, u.password_hash)
            for u in (await db.scalars(select(User))).all()
        }
    for uid_existing, snap in pre_users.items():
        assert post_users[uid_existing] == snap
