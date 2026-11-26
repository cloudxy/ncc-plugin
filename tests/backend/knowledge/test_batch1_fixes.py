from __future__ import annotations

import copy
import secrets
from datetime import timedelta

import httpx
from sqlalchemy import delete, func, select, update

from ncc_data.api.app import create_app
from ncc_data.application.model_settings import save_configuration
from ncc_data.application.service import Service
from ncc_data.cli.main import is_model_configured
from ncc_data.creation.worker import Worker, accept_task, create_task
from ncc_data.domain.contracts import (
    AuthorDraft,
    ChangeInput,
    CreationInput,
    ModelConfigurationInput,
    ScopeInput,
)
from ncc_data.domain.definitions import SYSTEM_SCOPE
from ncc_data.persistence.models import (
    Job,
    Membership,
    Scope,
    User,
    utcnow,
)
from ncc_data.runtime.settings import Settings
from tests.backend.automation.test_api_automation import FixtureProvider


async def _cleanup_scopes(factory, scope_ids: list[str]) -> None:
    if not scope_ids:
        return
    async with factory() as db, db.begin():
        await db.execute(
            update(Job)
            .where(Job.scope_id.in_(scope_ids), Job.state.in_(["queued", "running", "paused", "waiting"]))
            .values(state="cancelled", cancel_requested=True, lease_token=None, lease_until=None)
        )
        await db.execute(delete(Membership).where(Membership.scope_id.in_(scope_ids)))


async def _commit_ops(svc: Service, sid: str, operations: list[dict], title: str = "测试变更") -> dict:
    info = await svc.scope_info(sid)
    change = await svc.create_change(
        sid, ChangeInput(title=title, base_version=info["version"], operations=operations)
    )
    return await svc.adopt(sid, change["id"], f"idem-{change['id']}")


async def test_entities_search_kinds_exclude_kinds_total_version_sort_and_safe_position(store):
    factory, ids = store
    suffix = secrets.token_urlsafe(6)
    created_scopes: list[str] = []

    async with factory() as db:
        actor_username = (await db.get(User, ids[0])).username

    try:
        async with factory() as db, db.begin():
            svc = Service(db, await db.get(User, ids[0]))
            sid = (await svc.create_scope(ScopeInput(name=f"Batch1检索书-{suffix}")))["id"]
            created_scopes.append(sid)

            # Custom definition allowing string position values to simulate dirty/legacy imported data
            await _commit_ops(
                svc,
                sid,
                [
                    {
                        "op": "definition",
                        "definition": {
                            "key": "自由札记",
                            "version": 1,
                            "spec": {
                                "label": "自由札记",
                                "domain": "notes",
                                "properties": {"position": {"type": "text"}},
                            },
                        },
                    }
                ],
                title="注册自由札记",
            )
            await _commit_ops(
                svc,
                sid,
                [
                    {"op": "create", "kind": "character", "name": "沈青", "text": "主角剑客"},
                    {"op": "create", "kind": "character", "name": "顾白", "text": "副角医者"},
                    {"op": "create", "kind": "location", "name": "断魂崖", "text": "北境绝地"},
                    {"op": "create", "kind": "item", "name": "寒铁剑", "text": "旧兵刃"},
                    {"op": "create", "kind": "chapter", "name": "第二章", "data": {"position": 2}},
                    {"op": "create", "kind": "chapter", "name": "第一章", "data": {"position": 1}},
                    {"op": "create", "kind": "自由札记", "name": "浮点序号札记", "data": {"position": "1.5"}},
                    {"op": "create", "kind": "自由札记", "name": "字母序号札记", "data": {"position": "ch-a"}},
                    {"op": "create", "kind": "自由札记", "name": "空白序号札记", "data": {"position": ""}},
                    {
                        "op": "create",
                        "kind": "公共母本",
                        "name": "北境雪夜铺陈卡",
                        "data": {"commons_category": "environment"},
                    },
                    {
                        "op": "create",
                        "kind": "公共母本",
                        "name": "残阳古道压迫感",
                        "data": {"commons_category": "环境"},
                    },
                    {
                        "op": "create",
                        "kind": "公共母本",
                        "name": "三拍反转钩子卡",
                        "data": {"commons_category": "rhythm"},
                    },
                ],
                title="写入多样化实体",
            )
            # Update "寒铁剑" in a newer version so sort="version" places it at the top
            sword = (await svc.entities(sid, None))["items"]
            sword_entity = next(x for x in sword if x["name"] == "寒铁剑")
            ch1_entity = next(x for x in sword if x["name"] == "第一章")
            await _commit_ops(
                svc,
                sid,
                [
                    {
                        "op": "update",
                        "entity_id": sword_entity["id"],
                        "expected": sword_entity["version"],
                        "text": "重铸后的寒铁剑",
                    }
                ],
                title="重铸寒铁剑",
            )

        app = create_app(Settings(database_url="unused", public_origin="http://testserver"), factory)
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

            # 1) kinds filter + accurate total unaffected by limit/offset
            res_kinds = await client.post(
                f"/api/v1/scopes/{sid}/entities/search",
                headers=headers,
                json={"kinds": ["character", "location"], "limit": 2, "offset": 0},
            )
            assert res_kinds.status_code == 200, res_kinds.text
            body_kinds = res_kinds.json()
            assert body_kinds["total"] == 3
            assert len(body_kinds["items"]) == 2
            assert {item["kind"] for item in body_kinds["items"]} <= {"character", "location"}

            # 2) exclude_kinds filter ("其他/未归类")
            res_excl = await client.post(
                f"/api/v1/scopes/{sid}/entities/search",
                headers=headers,
                json={"exclude_kinds": ["character", "location", "item", "chapter", "公共母本"]},
            )
            assert res_excl.status_code == 200, res_excl.text
            body_excl = res_excl.json()
            assert body_excl["total"] == 3
            assert {item["kind"] for item in body_excl["items"]} == {"自由札记"}

            # 2b) filters op="in" for CommonsPage server-side category filtering
            res_in = await client.post(
                f"/api/v1/scopes/{sid}/entities/search",
                headers=headers,
                json={
                    "kind": "公共母本",
                    "filters": [
                        {"field": "commons_category", "op": "in", "value": ["environment", "环境"]}
                    ],
                },
            )
            assert res_in.status_code == 200, res_in.text
            body_in = res_in.json()
            assert body_in["total"] == 2
            assert {item["name"] for item in body_in["items"]} == {"北境雪夜铺陈卡", "残阳古道压迫感"}

            bad_in = await client.post(
                f"/api/v1/scopes/{sid}/entities/search",
                headers=headers,
                json={
                    "kind": "公共母本",
                    "filters": [{"field": "commons_category", "op": "in", "value": []}],
                },
            )
            assert bad_in.status_code == 422

            # 3) sort="position" with non-integer position strings ("1.5", "ch-a", "") NEVER throws 500
            res_pos = await client.post(
                f"/api/v1/scopes/{sid}/entities/search",
                headers=headers,
                json={"sort": "position"},
            )
            assert res_pos.status_code == 200, res_pos.text
            pos_names = [item["name"] for item in res_pos.json()["items"]]
            assert pos_names[:2] == ["第一章", "第二章"]
            assert res_pos.json()["total"] == 12

            # Restricted writer view with chapter cutoff also survives non-integer position entities
            res_writer = await client.post(
                f"/api/v1/scopes/{sid}/entities/search",
                headers=headers,
                json={"role": "writer", "chapter_id": ch1_entity["id"], "sort": "position"},
            )
            assert res_writer.status_code == 200, res_writer.text
            writer_names = [item["name"] for item in res_writer.json()["items"]]
            assert "第一章" in writer_names
            assert "第二章" not in writer_names

            # 4) sort="version" places most recently revised entity ("寒铁剑") first
            res_ver = await client.post(
                f"/api/v1/scopes/{sid}/entities/search",
                headers=headers,
                json={"sort": "version"},
            )
            assert res_ver.status_code == 200, res_ver.text
            assert res_ver.json()["items"][0]["name"] == "寒铁剑"
    finally:
        await _cleanup_scopes(factory, created_scopes)


async def test_no_index_jobs_on_save_and_jobs_filtering_summary_cancel_409_and_retry(store):
    factory, ids = store
    suffix = secrets.token_urlsafe(6)
    created_scopes: list[str] = []

    async with factory() as db:
        actor_username = (await db.get(User, ids[0])).username

    try:
        async with factory() as db, db.begin():
            svc = Service(db, await db.get(User, ids[0]))
            sid = (await svc.create_scope(ScopeInput(name=f"Batch1任务书-{suffix}")))["id"]
            created_scopes.append(sid)

            # Three consecutive adopts must write ZERO Job(kind="index") rows
            ch = None
            for idx in range(1, 4):
                await _commit_ops(
                    svc,
                    sid,
                    [{"op": "create", "kind": "chapter", "name": f"第{idx}章", "text": f"正文-{idx}"}],
                    title=f"连续保存-{idx}",
                )
            ch = (await svc.entities(sid))["items"][0]
            index_count = await db.scalar(
                select(func.count()).select_from(Job).where(Job.scope_id == sid, Job.kind == "index")
            )
            assert index_count == 0

            # Save an author-draft and one synthetic historical index row to ensure both are filtered out
            await svc.author_draft(sid, "chap-draft", AuthorDraft(version=0, name="草稿", text="草稿正文"))
            db.add(Job(scope_id=sid, actor_id=ids[0], kind="index", state="succeeded", payload={"version": 1}))

            # Create a creation task + two export tasks
            creation_job = await create_task(
                svc,
                sid,
                CreationInput(
                    objective="续写关键章",
                    kind="chapter",
                    entity_id=ch["id"],
                    scheme="P1",
                    name="第一章续写",
                ),
            )
            creation_jid = creation_job["id"]
            export_ok_jid = (await svc.queue_export(sid, "json"))["id"]
            export_retry_jid = (await svc.queue_export(sid, "markdown"))["id"]

        # Run creation_jid -> qualified, and export_ok_jid -> succeeded
        worker = Worker(factory, Settings(database_url="unused"), FixtureProvider())
        assert await worker.run_job(creation_jid) is True
        assert await worker.run_job(export_ok_jid) is True

        # Adopt creation_jid -> terminal state "applied"
        async with factory() as db, db.begin():
            svc = Service(db, await db.get(User, ids[0]))
            await accept_task(svc, sid, creation_jid, f"adopt-{creation_jid}")
            # Mark export_retry_jid as failed with an error to exercise /retry clearing error
            retry_row = await db.get(Job, export_retry_jid)
            retry_row.state = "failed"
            retry_row.attempts = 2
            retry_row.result = {"error": {"code": "worker_failure", "detail": "模拟导出失败"}}

        app = create_app(Settings(database_url="unused", public_origin="http://testserver"), factory)
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

            # 1) GET /jobs?summary=true excludes index & author-draft and strips heavy candidates/packet
            list_res = await client.get(f"/api/v1/scopes/{sid}/jobs?summary=true")
            assert list_res.status_code == 200, list_res.text
            jobs_list = list_res.json()
            assert {j["kind"] for j in jobs_list} == {"creation", "export"}
            creation_summary = next(j for j in jobs_list if j["id"] == creation_jid)
            assert "candidates" not in creation_summary["result"]
            assert "packet" not in creation_summary["result"]
            assert creation_summary["result"]["verdict"] == "qualified"
            assert creation_summary["result"]["score"] is not None
            assert creation_summary["result"]["target_id"] == ch["id"]
            assert creation_summary["result"]["target_name"] == "第一章续写"

            export_summary = next(j for j in jobs_list if j["id"] == export_ok_jid)
            assert export_summary["result"]["attachment_id"] is not None

            # Query filters: kind & state & entity_id
            only_failed = await client.get(f"/api/v1/scopes/{sid}/jobs?kind=export&state=failed&summary=true")
            assert only_failed.status_code == 200
            assert [j["id"] for j in only_failed.json()] == [export_retry_jid]

            by_entity = await client.get(f"/api/v1/scopes/{sid}/jobs?entity_id={ch['id']}&summary=true")
            assert by_entity.status_code == 200
            assert [j["id"] for j in by_entity.json()] == [creation_jid]

            # 2) Calling /cancel on terminal "applied" or "succeeded" returns 409 job_terminal without mutating state
            cancel_applied = await client.post(
                f"/api/v1/scopes/{sid}/jobs/{creation_jid}/cancel", headers=headers
            )
            assert cancel_applied.status_code == 409
            assert cancel_applied.json()["code"] == "job_terminal"

            cancel_succeeded = await client.post(
                f"/api/v1/scopes/{sid}/jobs/{export_ok_jid}/cancel", headers=headers
            )
            assert cancel_succeeded.status_code == 409
            assert cancel_succeeded.json()["code"] == "job_terminal"

            async with factory() as db:
                assert (await db.get(Job, creation_jid)).state == "applied"
                assert (await db.get(Job, export_ok_jid)).state == "succeeded"

            # Calling /retry on terminal "succeeded" also returns 409
            retry_succeeded = await client.post(
                f"/api/v1/scopes/{sid}/jobs/{export_ok_jid}/retry", headers=headers
            )
            assert retry_succeeded.status_code == 409

            # 3) Calling /retry on failed export resets to queued, clears error & attempts, and worker succeeds
            retry_res = await client.post(
                f"/api/v1/scopes/{sid}/jobs/{export_retry_jid}/retry", headers=headers
            )
            assert retry_res.status_code == 200, retry_res.text
            retried_body = retry_res.json()
            assert retried_body["state"] == "queued"
            assert retried_body["cancel_requested"] is False
            assert retried_body["attempts"] == 0
            assert "error" not in (retried_body.get("result") or {})

            # Cancel the queued job -> 200 cancelled; second cancel -> 409 job_terminal; retry again -> queued -> worker succeeds
            cancel_queued = await client.post(
                f"/api/v1/scopes/{sid}/jobs/{export_retry_jid}/cancel", headers=headers
            )
            assert cancel_queued.status_code == 200
            assert cancel_queued.json()["state"] == "cancelled"

            cancel_again = await client.post(
                f"/api/v1/scopes/{sid}/jobs/{export_retry_jid}/cancel", headers=headers
            )
            assert cancel_again.status_code == 409
            assert cancel_again.json()["code"] == "job_terminal"

            retry_cancelled = await client.post(
                f"/api/v1/scopes/{sid}/jobs/{export_retry_jid}/retry", headers=headers
            )
            assert retry_cancelled.status_code == 200
            assert retry_cancelled.json()["state"] == "queued"

        assert await worker.run_job(export_retry_jid) is True
        async with factory() as db:
            assert (await db.get(Job, export_retry_jid)).state == "succeeded"
    finally:
        await _cleanup_scopes(factory, created_scopes)


async def test_operations_worker_heartbeat_and_doctor_web_model_registry(store):
    factory, ids = store
    suffix = secrets.token_urlsafe(6)
    created_scopes: list[str] = []
    original_sys_config = None

    async with factory() as db:
        sys_scope = await db.get(Scope, SYSTEM_SCOPE)
        original_sys_config = copy.deepcopy(sys_scope.config or {})

    try:
        async with factory() as db, db.begin():
            svc = Service(db, await db.get(User, ids[0]))
            sid = (await svc.create_scope(ScopeInput(name=f"Batch1运维书-{suffix}")))["id"]
            created_scopes.append(sid)
            # Add internal author-draft + index jobs plus 1 real queued export job
            await svc.author_draft(sid, "d1", AuthorDraft(version=0, name="草稿", text="x"))
            db.add(Job(scope_id=sid, actor_id=ids[0], kind="index", state="succeeded", payload={"version": 0}))
            await svc.queue_export(sid, "csv")

        worker = Worker(factory, Settings(database_url="unused"), FixtureProvider())
        await worker.record_heartbeat()

        async with factory() as db, db.begin():
            svc = Service(db, await db.get(User, ids[0]))
            ops = await svc.operations_status(sid)
            assert ops["jobs"] == {"queued": 1}
            assert ops["worker"]["online"] is True
            assert ops["worker"]["last_seen_at"] is not None
            assert 0 <= ops["worker"]["stale_seconds"] <= 45

            # Roll back synthetic mutations on SYSTEM_SCOPE via savepoint so ncc_audit stays clean
            nested = await db.begin_nested()
            try:
                sys_scope = await db.get(Scope, SYSTEM_SCOPE)
                stale_cfg = dict(sys_scope.config or {})
                stale_cfg["worker_heartbeat"] = {
                    "updated_at": (utcnow() - timedelta(seconds=120)).isoformat(),
                    "pid": 12345,
                }
                sys_scope.config = stale_cfg
                await db.flush()

                ops_stale = await svc.operations_status(sid)
                assert ops_stale["worker"]["online"] is False
                assert ops_stale["worker"]["stale_seconds"] >= 100

                # Doctor model_configured check with blank env settings + web model_registry
                blank_env_settings = Settings(
                    database_url="unused",
                    model_url="",
                    writer_model="",
                    judge_model="",
                )
                clean_cfg = {
                    k: v
                    for k, v in dict(sys_scope.config or {}).items()
                    if k not in {"model_registry", "model_route"}
                }
                sys_scope.config = clean_cfg
                await db.flush()
                assert await is_model_configured(db, blank_env_settings) is False

                await save_configuration(
                    svc,
                    blank_env_settings,
                    ModelConfigurationInput(
                        name="网页端DeepSeek",
                        supplier="DeepSeek",
                        base_url="https://api.deepseek.com",
                        auth_ref="DEEPSEEK_API_KEY",
                        model_key="deepseek-chat",
                        purposes=["plan", "write", "revise", "judge"],
                        enabled=True,
                    ),
                )
                assert await is_model_configured(db, blank_env_settings) is True
            finally:
                await nested.rollback()
    finally:
        async with factory() as db, db.begin():
            sys_scope = await db.scalar(
                select(Scope).where(Scope.id == SYSTEM_SCOPE).with_for_update()
            )
            if sys_scope is not None and original_sys_config is not None:
                sys_scope.config = original_sys_config
        await _cleanup_scopes(factory, created_scopes)
