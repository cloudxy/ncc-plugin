from __future__ import annotations

from contextlib import contextmanager
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import event, select
from sqlalchemy.engine import Engine

from ncc_data.api.app import create_app
from ncc_data.application.service import Service
from ncc_data.domain.contracts import ChangeInput
from ncc_data.persistence.models import ChangeSet, Scope, User
from ncc_data.runtime.settings import Settings
from ncc_shared.errors import DomainError


@contextmanager
def _count_sql_statements():
    statements: list[str] = []

    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(Engine, "before_cursor_execute", _before_cursor_execute)
    try:
        yield statements
    finally:
        event.remove(Engine, "before_cursor_execute", _before_cursor_execute)


async def _login(client: httpx.AsyncClient, username: str, password: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/login",
        headers={"x-ncc-client": "console"},
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_atomic_commit_idempotency_and_conflict_rollback(store):
    factory, ids = store
    admin_id, _ = ids
    admin_pw = factory.credentials[admin_id]

    async with factory() as db:
        admin_username = (await db.get(User, admin_id)).username

    settings = Settings(database_url="unused", public_origin="http://127.0.0.1:8788")
    app = create_app(settings, factory=factory)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8788") as client:
        me = await _login(client, admin_username, admin_pw)
        headers = {"x-csrf-token": me["csrf"]}

        scope = (
            await client.post("/api/v1/scopes", headers=headers, json={"name": "一步原子提交验收空间"})
        ).raise_for_status().json()
        sid = scope["id"]

        commit_payload = {
            "title": "原子创建人物与组织",
            "base_version": 0,
            "operations": [
                {
                    "op": "create",
                    "kind": "character",
                    "name": "陆沉",
                    "text": "守夜人队正",
                    "data": {"position": 1},
                },
                {
                    "op": "create",
                    "kind": "organization",
                    "name": "镇抚司",
                    "text": "京城夜巡机构",
                    "data": {"position": 2},
                },
            ],
        }

        # 1. One-step atomic commit succeeds
        first = await client.post(
            f"/api/v1/scopes/{sid}/changes/commit",
            headers={**headers, "idempotency-key": "b4-commit-key-1"},
            json=commit_payload,
        )
        assert first.status_code == 200, first.text
        first_body = first.json()
        assert first_body["version"] == 1
        assert isinstance(first_body.get("change_id"), str) and first_body["change_id"]
        assert len(first_body["impacts"]) == 2
        char_id = first_body["impacts"][0]["entity_id"]

        # 2. Same Idempotency-Key + identical payload replays original receipt without new ChangeSet
        replay = await client.post(
            f"/api/v1/scopes/{sid}/changes/commit",
            headers={**headers, "idempotency-key": "b4-commit-key-1"},
            json=commit_payload,
        )
        assert replay.status_code == 200, replay.text
        assert replay.json() == first_body

        changes_after_replay = (await client.get(f"/api/v1/scopes/{sid}/changes")).raise_for_status().json()
        assert len(changes_after_replay) == 1
        assert changes_after_replay[0]["id"] == first_body["change_id"]
        assert changes_after_replay[0]["state"] == "applied"
        assert changes_after_replay[0]["applied_version"] == 1

        # 3. Reusing same Idempotency-Key with a different payload returns 409 idempotency_reuse
        reused = await client.post(
            f"/api/v1/scopes/{sid}/changes/commit",
            headers={**headers, "idempotency-key": "b4-commit-key-1"},
            json={**commit_payload, "title": "篡改标题复用幂等键"},
        )
        assert reused.status_code == 409, reused.text
        assert reused.json()["code"] == "idempotency_reuse"

        # 4. Version conflict & precondition failures leave ZERO orphan draft ChangeSet rows
        conflict = await client.post(
            f"/api/v1/scopes/{sid}/changes/commit",
            headers={**headers, "idempotency-key": "b4-commit-conflict"},
            json={
                "title": "过期基线冲突",
                "base_version": 0,
                "operations": [{"op": "create", "kind": "item", "name": "断刀"}],
            },
        )
        assert conflict.status_code == 409, conflict.text
        assert conflict.json()["code"] == "version_conflict"

        stale_entity = await client.post(
            f"/api/v1/scopes/{sid}/changes/commit",
            headers={**headers, "idempotency-key": "b4-commit-precondition"},
            json={
                "title": "过期对象版本",
                "base_version": 1,
                "operations": [
                    {
                        "op": "update",
                        "entity_id": char_id,
                        "expected": f"{sid}:999",
                        "text": "不应写入",
                    }
                ],
            },
        )
        assert stale_entity.status_code == 412, stale_entity.text
        assert stale_entity.json()["code"] == "precondition"

        changes_after_failures = (await client.get(f"/api/v1/scopes/{sid}/changes")).raise_for_status().json()
        assert len(changes_after_failures) == 1

        # Also verify direct in-session Service.commit_change rollback leaves zero orphan ChangeSet
        async with factory() as db, db.begin():
            actor = await db.get(User, admin_id)
            svc = Service(db, actor)
            with pytest.raises(DomainError) as exc_info:
                await svc.commit_change(
                    sid,
                    ChangeInput(
                        title="会话内校验失败",
                        base_version=1,
                        operations=[
                            {
                                "op": "fact",
                                "entity_id": char_id,
                                "fact": {
                                    "predicate": "member_of",
                                    "category": "relation",
                                    "object_id": str(uuid4()),
                                    "source": {"kind": "author"},
                                },
                            }
                        ],
                    ),
                    "b4-direct-rollback",
                )
            assert exc_info.value.code == "reference"
            persisted_changes = (
                await db.scalars(select(ChangeSet).where(ChangeSet.scope_id == sid))
            ).all()
            assert len(persisted_changes) == 1
            scope_row = await db.get(Scope, sid)
            assert scope_row.version == 1

        # 5. Commit without explicit Idempotency-Key + legacy two-step POST /changes + /adopt remain compatible
        auto_key_resp = await client.post(
            f"/api/v1/scopes/{sid}/changes/commit",
            headers=headers,
            json={
                "title": "免手工幂等键提交",
                "base_version": 1,
                "operations": [
                    {
                        "op": "update",
                        "entity_id": char_id,
                        "expected": f"{sid}:1",
                        "text": "守夜人统领",
                    }
                ],
            },
        )
        assert auto_key_resp.status_code == 200, auto_key_resp.text
        assert auto_key_resp.json()["version"] == 2

        two_step = (
            await client.post(
                f"/api/v1/scopes/{sid}/changes",
                headers=headers,
                json={
                    "title": "传统两步提交兼容",
                    "base_version": 2,
                    "operations": [{"op": "create", "kind": "location", "name": "北镇抚司衙门"}],
                },
            )
        ).raise_for_status().json()
        adopted = (
            await client.post(
                f"/api/v1/scopes/{sid}/changes/{two_step['id']}/adopt",
                headers={**headers, "idempotency-key": "b4-two-step-key"},
                json={},
            )
        ).raise_for_status().json()
        assert adopted["version"] == 3


async def test_sql_query_counts_bounded_for_30_plus_entities_and_facts(store):
    factory, ids = store
    admin_id, regular_id = ids
    admin_pw = factory.credentials[admin_id]
    regular_pw = factory.credentials[regular_id]

    async with factory() as db:
        admin_username = (await db.get(User, admin_id)).username
        regular_username = (await db.get(User, regular_id)).username

    settings = Settings(database_url="unused", public_origin="http://127.0.0.1:8788")
    app = create_app(settings, factory=factory)
    transport = httpx.ASGITransport(app=app)

    async with (
        httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8788") as owner_client,
        httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8788") as reader_client,
    ):
        owner_me = await _login(owner_client, admin_username, admin_pw)
        owner_headers = {"x-csrf-token": owner_me["csrf"]}
        reader_me = await _login(reader_client, regular_username, regular_pw)
        reader_headers = {"x-csrf-token": reader_me["csrf"]}

        scope = (
            await owner_client.post(
                "/api/v1/scopes", headers=owner_headers, json={"name": "N+1常数上界压测空间"}
            )
        ).raise_for_status().json()
        sid = scope["id"]

        # Grant read-only non-secret membership to regular user to verify redaction accuracy too
        (
            await owner_client.post(
                f"/api/v1/scopes/{sid}/members",
                headers=owner_headers,
                json={"username": regular_username, "actions": ["read"]},
            )
        ).raise_for_status()

        vol_id = str(uuid4())
        center_id = str(uuid4())
        secret_org_id = str(uuid4())
        chapter_ids = [str(uuid4()) for _ in range(30)]
        org_ids = [str(uuid4()) for _ in range(5)]

        entity_ops = [
            {
                "op": "create",
                "entity_id": vol_id,
                "kind": "volume",
                "name": "第一卷·风起长街",
                "data": {"position": 0},
            },
            {
                "op": "create",
                "entity_id": center_id,
                "kind": "character",
                "name": "陈平安",
                "text": "骊珠洞天少年",
                "data": {"position": 0},
            },
            {
                "op": "create",
                "entity_id": secret_org_id,
                "kind": "organization",
                "name": "暗影密阁",
                "secret": True,
                "text": "仅作者可见的秘密组织",
                "data": {"position": 99},
            },
            *[
                {
                    "op": "create",
                    "entity_id": oid,
                    "kind": "organization",
                    "name": f"宗门势力-{idx + 1:02d}",
                    "data": {"position": idx},
                }
                for idx, oid in enumerate(org_ids)
            ],
            *[
                {
                    "op": "create",
                    "entity_id": cid,
                    "kind": "chapter",
                    "name": f"第{idx + 1:02d}章 试剑第{idx + 1}回",
                    "text": f"这是第 {idx + 1} 章的正文内容。",
                    "data": {"position": idx, "parent_id": vol_id, "status": "done"},
                }
                for idx, cid in enumerate(chapter_ids)
            ],
        ]
        # Total created entities: 1 + 1 + 1 + 5 + 30 = 38 entities (> 30)
        seed_entities = await owner_client.post(
            f"/api/v1/scopes/{sid}/changes/commit",
            headers={**owner_headers, "idempotency-key": "b4-perf-seed-entities"},
            json={"title": "批量灌入38个实体", "base_version": 0, "operations": entity_ops},
        )
        assert seed_entities.status_code == 200, seed_entities.text

        # Create 36 relation facts:
        # - center_id -> 5 org_ids (hop 1)
        # - center_id -> secret_org_id (secret hop 1)
        # - org_ids[i % 5] -> 30 chapter_ids (hop 2)
        fact_ops = [
            *[
                {
                    "op": "fact",
                    "entity_id": center_id,
                    "fact": {
                        "predicate": "member_of",
                        "category": "relation",
                        "object_id": oid,
                        "source": {"kind": "author"},
                    },
                }
                for oid in org_ids
            ],
            {
                "op": "fact",
                "entity_id": center_id,
                "fact": {
                    "predicate": "member_of",
                    "category": "relation",
                    "object_id": secret_org_id,
                    "source": {"kind": "author"},
                },
            },
            *[
                {
                    "op": "fact",
                    "entity_id": org_ids[idx % len(org_ids)],
                    "fact": {
                        "predicate": "appears_in",
                        "category": "relation",
                        "object_id": cid,
                        "chapter_id": cid,
                        "source": {"kind": "author"},
                    },
                }
                for idx, cid in enumerate(chapter_ids)
            ],
        ]
        seed_facts = await owner_client.post(
            f"/api/v1/scopes/{sid}/changes/commit",
            headers={**owner_headers, "idempotency-key": "b4-perf-seed-facts"},
            json={"title": "批量灌入36条关系事实", "base_version": 1, "operations": fact_ops},
        )
        assert seed_facts.status_code == 200, seed_facts.text
        assert seed_facts.json()["version"] == 2

        # 1. Measure facts() SQL statement count (36 relation facts across 37 entities)
        with _count_sql_statements() as owner_fact_sql:
            owner_facts_resp = await owner_client.post(
                f"/api/v1/scopes/{sid}/state/query",
                headers=owner_headers,
                json={"category": "relation", "limit": 200},
            )
        assert owner_facts_resp.status_code == 200, owner_facts_resp.text
        owner_facts = owner_facts_resp.json()
        assert owner_facts["total"] == 36
        assert len(owner_fact_sql) <= 15, f"facts() executed {len(owner_fact_sql)} SQL queries"

        with _count_sql_statements() as reader_fact_sql:
            reader_facts_resp = await reader_client.post(
                f"/api/v1/scopes/{sid}/state/query",
                headers=reader_headers,
                json={"category": "relation", "limit": 200},
            )
        assert reader_facts_resp.status_code == 200, reader_facts_resp.text
        reader_facts = reader_facts_resp.json()
        # Secret relation to secret_org_id must be filtered out for non-secret member
        assert reader_facts["total"] == 35
        assert len(reader_fact_sql) <= 15, f"member facts() executed {len(reader_fact_sql)} SQL queries"

        # 2. Measure graph() SQL statement count (2-hop expansion over 37 nodes & 36 edges)
        with _count_sql_statements() as owner_graph_sql:
            owner_graph_resp = await owner_client.get(
                f"/api/v1/scopes/{sid}/graph/{center_id}", params={"hops": 2}
            )
        assert owner_graph_resp.status_code == 200, owner_graph_resp.text
        owner_graph = owner_graph_resp.json()
        assert len(owner_graph["nodes"]) == 37
        assert len(owner_graph["edges"]) == 36
        assert len(owner_graph_sql) <= 15, f"graph() executed {len(owner_graph_sql)} SQL queries"

        with _count_sql_statements() as reader_graph_sql:
            reader_graph_resp = await reader_client.get(
                f"/api/v1/scopes/{sid}/graph/{center_id}", params={"hops": 2}
            )
        assert reader_graph_resp.status_code == 200, reader_graph_resp.text
        reader_graph = reader_graph_resp.json()
        reader_node_ids = {n["id"] for n in reader_graph["nodes"]}
        assert secret_org_id not in reader_node_ids
        assert len(reader_graph["nodes"]) == 36
        assert len(reader_graph["edges"]) == 35
        assert len(reader_graph_sql) <= 15, f"member graph() executed {len(reader_graph_sql)} SQL queries"

        # 3. Measure reorder() SQL statement count (reordering all 30 chapters in reverse)
        reversed_ids = list(reversed(chapter_ids))
        reorder_items = [
            {
                "entity_id": cid,
                "position": new_pos,
                "parent_id": vol_id,
                "include_parent": True,
            }
            for new_pos, cid in enumerate(reversed_ids)
        ]
        with _count_sql_statements() as reorder_sql:
            reorder_resp = await owner_client.post(
                f"/api/v1/scopes/{sid}/studio/reorder",
                headers={**owner_headers, "idempotency-key": "b4-perf-reorder-30"},
                json={"base_version": 2, "items": reorder_items},
            )
        assert reorder_resp.status_code == 200, reorder_resp.text
        assert reorder_resp.json()["version"] == 3
        assert len(reorder_sql) <= 15, (
            f"reorder(30 chapters) executed {len(reorder_sql)} SQL statements:\n"
            + "\n".join(f"  [{i + 1}] {s.splitlines()[0][:100]}" for i, s in enumerate(reorder_sql))
        )

        overview = (
            await owner_client.get(f"/api/v1/scopes/{sid}/studio/overview")
        ).raise_for_status().json()
        assert [ch["id"] for ch in overview["chapters"]] == reversed_ids
