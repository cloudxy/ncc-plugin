from __future__ import annotations

import base64
import io
import json
import secrets
import zipfile

import httpx
from sqlalchemy import delete, select, update

from ncc_data.api.app import create_app
from ncc_data.application.service import Service
from ncc_data.creation.worker import Worker
from ncc_data.domain.contracts import ChangeInput, MemberInput, Query, ScopeInput
from ncc_data.persistence.models import Audit, Job, Membership, Scope, User, uid
from ncc_data.runtime.settings import Settings
from ncc_shared.serialization import digest
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


async def _commit_ops(svc: Service, sid: str, operations: list[dict], title: str = "Batch2变更") -> dict:
    info = await svc.scope_info(sid)
    change = await svc.create_change(
        sid, ChangeInput(title=title, base_version=info["version"], operations=operations)
    )
    return await svc.adopt(sid, change["id"], f"b2-{change['id']}")


async def test_manuscript_exports_epub_txt_md_filters_422_and_zero_secret_leakage(store):
    factory, ids = store
    suffix = secrets.token_urlsafe(6)
    created_scopes: list[str] = []
    vol1_id = uid()
    vol2_id = uid()
    vol_empty_id = uid()
    vol_sec_id = uid()
    del_ch_id = uid()

    async with factory() as db:
        author_username = (await db.get(User, ids[0])).username
        reader_username = (await db.get(User, ids[1])).username

    try:
        async with factory() as db, db.begin():
            svc = Service(db, await db.get(User, ids[0]))
            sid = (await svc.create_scope(ScopeInput(name=f"雪夜长歌-{suffix}")))["id"]
            created_scopes.append(sid)

            # Grant read-only (no export) to ids[1] to verify export permission check
            await svc.set_member(sid, MemberInput(user_id=ids[1], actions=["read"]))

            await _commit_ops(
                svc,
                sid,
                [
                    {"op": "create", "entity_id": vol1_id, "kind": "volume", "name": "第一卷 寒山", "data": {"position": 1}},
                    {"op": "create", "entity_id": vol2_id, "kind": "volume", "name": "第二卷 沧海", "data": {"position": 2}},
                    {"op": "create", "entity_id": vol_empty_id, "kind": "volume", "name": "第三卷 空卷", "data": {"position": 3}},
                    {
                        "op": "create",
                        "entity_id": vol_sec_id,
                        "kind": "volume",
                        "name": "秘密暗卷XYZ",
                        "secret": True,
                        "data": {"position": 4},
                    },
                    {
                        "op": "create",
                        "kind": "chapter",
                        "name": "楔子 古剑",
                        "text": "# 楔子 古剑\n\nrev 1: 初稿批注\n---\n孤峰积雪千年不化。",
                        "data": {"position": 0, "status": "done"},
                    },
                    {
                        "op": "create",
                        "kind": "chapter",
                        "name": "第一章 下山",
                        "text": "少年背剑走入风雪。\n\n山下灯火微明。",
                        "data": {
                            "parent_id": vol1_id,
                            "position": 1,
                            "status": "done",
                            "secret_note": "作者机密伏笔SECRET111",
                            "beat_outline": "内部细纲OUTLINE222",
                        },
                    },
                    {
                        "op": "create",
                        "kind": "chapter",
                        "name": "第二章 客栈草稿",
                        "text": "草稿未定稿内容DRAFT333。",
                        "data": {"parent_id": vol1_id, "position": 2, "status": "draft"},
                    },
                    {
                        "op": "create",
                        "kind": "chapter",
                        "name": "第三章 渡海",
                        "text": "长风破浪会有时。",
                        "data": {"parent_id": vol2_id, "position": 1, "status": "已定稿"},
                    },
                    {
                        "op": "create",
                        "kind": "chapter",
                        "name": "机密番外章",
                        "secret": True,
                        "text": "绝密正文SECRET_CH_444",
                        "data": {"parent_id": vol1_id, "position": 3, "status": "done"},
                    },
                    {
                        "op": "create",
                        "kind": "chapter",
                        "name": "秘密卷内章",
                        "text": "秘密卷内正文SECRET_VOL_CH_555",
                        "data": {"parent_id": vol_sec_id, "position": 1, "status": "done"},
                    },
                    {
                        "op": "create",
                        "entity_id": del_ch_id,
                        "kind": "chapter",
                        "name": "已归档旧章",
                        "text": "废弃章节DELETED_666",
                        "data": {"parent_id": vol1_id, "position": 4, "status": "done"},
                    },
                    {
                        "op": "create",
                        "kind": "character",
                        "name": "人物设定卡CHAR_777",
                        "text": "人物设定正文CHAR_BODY_777",
                    },
                ],
            )
            del_ch = await svc.entity(sid, del_ch_id)
            await _commit_ops(
                svc,
                sid,
                [{"op": "retire", "entity_id": del_ch["id"], "expected": del_ch["version"]}],
                title="归档废弃章",
            )

        app = create_app(Settings(database_url="unused", public_origin="http://testserver"), factory)
        worker = Worker(factory, Settings(database_url="unused"), FixtureProvider())

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client, httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as reader_client:
            # Read-only member without export action gets 403
            r_login = await reader_client.post(
                "/api/v1/auth/login",
                headers={"x-ncc-client": "console"},
                json={"username": reader_username, "password": factory.credentials[ids[1]]},
            )
            assert r_login.status_code == 200
            r_headers = {"x-csrf-token": r_login.json()["csrf"]}
            denied = await reader_client.post(
                f"/api/v1/scopes/{sid}/exports",
                headers=r_headers,
                json={"format": "epub", "only_done": True},
            )
            assert denied.status_code == 403

            # Author login
            a_login = await client.post(
                "/api/v1/auth/login",
                headers={"x-ncc-client": "console"},
                json={"username": author_username, "password": factory.credentials[ids[0]]},
            )
            assert a_login.status_code == 200
            headers = {"x-csrf-token": a_login.json()["csrf"]}

            # Empty filter (third volume has 0 chapters) -> 422 export_empty
            empty_res = await client.post(
                f"/api/v1/scopes/{sid}/exports",
                headers=headers,
                json={"format": "epub", "volume_id": vol_empty_id, "only_done": True},
            )
            assert empty_res.status_code == 422
            assert empty_res.json()["code"] == "export_empty"

            # Secret volume ID also yields 422 export_empty (never leaks existence/chapters)
            sec_vol_res = await client.post(
                f"/api/v1/scopes/{sid}/exports",
                headers=headers,
                json={"format": "txt", "volume_id": vol_sec_id},
            )
            assert sec_vol_res.status_code == 422
            assert sec_vol_res.json()["code"] == "export_empty"

            # 1) EPUB export with only_done=True across whole book -> 3 chapters (楔子, 第一章, 第三章)
            epub_job_res = await client.post(
                f"/api/v1/scopes/{sid}/exports",
                headers=headers,
                json={"format": "epub", "only_done": True, "author": "云山执笔"},
            )
            assert epub_job_res.status_code == 202, epub_job_res.text
            epub_jid = epub_job_res.json()["id"]
            assert await worker.run_job(epub_jid) is True

            job_detail = (await client.get(f"/api/v1/scopes/{sid}/jobs/{epub_jid}")).json()
            assert job_detail["state"] == "succeeded"
            assert job_detail["result"]["format"] == "epub"
            assert job_detail["result"]["chapter_count"] == 3
            assert job_detail["result"]["words"] > 0
            assert job_detail["result"]["name"].endswith(".epub")

            # Summary endpoint also preserves format / chapter_count / words
            summary_rows = (await client.get(f"/api/v1/scopes/{sid}/jobs?summary=true")).json()
            epub_summary = next(x for x in summary_rows if x["id"] == epub_jid)
            assert epub_summary["result"]["format"] == "epub"
            assert epub_summary["result"]["chapter_count"] == 3
            assert epub_summary["result"]["words"] == job_detail["result"]["words"]

            epub_bytes = (
                await client.get(f"/api/v1/scopes/{sid}/attachments/{job_detail['result']['id']}")
            ).content
            with zipfile.ZipFile(io.BytesIO(epub_bytes), "r") as zf:
                assert zf.namelist()[0] == "mimetype"
                assert zf.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
                all_epub_text = "\n".join(
                    zf.read(n).decode("utf-8", errors="ignore") for n in zf.namelist()
                )
                assert "云山执笔" in all_epub_text
                assert "孤峰积雪千年不化" in all_epub_text
                assert "少年背剑走入风雪" in all_epub_text
                assert "长风破浪会有时" in all_epub_text
                assert "rev 1" not in all_epub_text
                for forbidden in (
                    "DRAFT333",
                    "SECRET111",
                    "OUTLINE222",
                    "SECRET_CH_444",
                    "SECRET_VOL_CH_555",
                    "秘密暗卷XYZ",
                    "DELETED_666",
                    "CHAR_777",
                    "CHAR_BODY_777",
                ):
                    assert forbidden not in all_epub_text

            # 2) manuscript_md export scoped to vol1 with only_done=False -> 2 chapters (第一章 + 第二章), zero secrets
            md_job_res = await client.post(
                f"/api/v1/scopes/{sid}/exports",
                headers=headers,
                json={"format": "manuscript_md", "volume_id": vol1_id, "only_done": False},
            )
            assert md_job_res.status_code == 202
            md_jid = md_job_res.json()["id"]
            assert await worker.run_job(md_jid) is True
            md_job = (await client.get(f"/api/v1/scopes/{sid}/jobs/{md_jid}")).json()
            assert md_job["result"]["chapter_count"] == 2
            md_text = (
                await client.get(f"/api/v1/scopes/{sid}/attachments/{md_job['result']['id']}")
            ).content.decode("utf-8")
            assert "## 第一卷 寒山" in md_text
            assert "### 第一章 下山" in md_text
            assert "### 第二章 客栈草稿" in md_text
            assert "楔子 古剑" not in md_text
            assert "第三章 渡海" not in md_text
            assert "```json" not in md_text
            assert "SECRET111" not in md_text
            assert "SECRET_CH_444" not in md_text

            # 3) txt export with only_done=True -> full-width indented paragraphs
            txt_job_res = await client.post(
                f"/api/v1/scopes/{sid}/exports",
                headers=headers,
                json={"format": "txt", "only_done": True},
            )
            assert txt_job_res.status_code == 202
            txt_jid = txt_job_res.json()["id"]
            assert await worker.run_job(txt_jid) is True
            txt_job = (await client.get(f"/api/v1/scopes/{sid}/jobs/{txt_jid}")).json()
            txt_content = (
                await client.get(f"/api/v1/scopes/{sid}/attachments/{txt_job['result']['id']}")
            ).content.decode("utf-8")
            assert "　　孤峰积雪千年不化。" in txt_content
            assert "　　少年背剑走入风雪。\n　　山下灯火微明。" in txt_content
            assert "DRAFT333" not in txt_content
            assert "SECRET_CH_444" not in txt_content
    finally:
        await _cleanup_scopes(factory, created_scopes)


async def test_founding_card_author_draft_status_and_reader_anti_spoiler_overview(store):
    factory, ids = store
    suffix = secrets.token_urlsafe(6)
    created_scopes: list[str] = []
    v1_id = uid()
    c1_id = uid()
    c2_id = uid()
    c3_id = uid()
    fs_vis_id = uid()
    fs_dark_ok_id = uid()
    fs_future_id = uid()
    fs_planned_id = uid()
    fs_dark_unanchored_id = uid()

    async with factory() as db:
        author_username = (await db.get(User, ids[0])).username
        reader_username = (await db.get(User, ids[1])).username

    try:
        async with factory() as db, db.begin():
            svc = Service(db, await db.get(User, ids[0]))
            sid = (await svc.create_scope(ScopeInput(name=f"防剧透与立书-{suffix}")))["id"]
            created_scopes.append(sid)

            await svc.set_member(sid, MemberInput(user_id=ids[1], actions=["read"]))

            await _commit_ops(
                svc,
                sid,
                [
                    {
                        "op": "create",
                        "entity_id": v1_id,
                        "kind": "volume",
                        "name": "第一卷 风起",
                        "text": "第一卷卷纲总述：少年走出边城。",
                        "data": {"position": 1, "description": "边城开局卷"},
                    },
                    {
                        "op": "create",
                        "entity_id": c1_id,
                        "kind": "chapter",
                        "name": "第一章 边城",
                        "text": "边城铁铺炉火通明。",
                        "data": {"parent_id": v1_id, "position": 1, "status": "done"},
                    },
                    {
                        "op": "create",
                        "entity_id": c2_id,
                        "kind": "chapter",
                        "name": "第二章 断刀",
                        "text": "断刀在雪夜鸣响。",
                        "data": {"parent_id": v1_id, "position": 2, "status": "review"},
                    },
                    {
                        "op": "create",
                        "entity_id": c3_id,
                        "kind": "chapter",
                        "name": "第三章 未来剧透章",
                        "text": "幕后黑手现身。",
                        "data": {"parent_id": v1_id, "position": 3, "status": "planned"},
                    },
                    {
                        "op": "create",
                        "entity_id": fs_vis_id,
                        "kind": "伏笔",
                        "name": "炉底古印",
                        "text": "第一章铁炉下露出的半枚残印",
                        "data": {
                            "position": 1,
                            "status": "已埋设",
                            "line_type": "明线",
                            "planted_chapter": 1,
                            "expected_chapter": 5,
                            "strength": 4,
                            "secret_note": "实为镇国虎符残片",
                        },
                    },
                    {
                        "op": "create",
                        "entity_id": fs_dark_ok_id,
                        "kind": "伏笔",
                        "name": "掌柜咳血",
                        "text": "第二章掌柜暗中咳出黑血",
                        "data": {
                            "position": 2,
                            "status": "推进中",
                            "line_type": "暗线",
                            "planted_chapter": 2,
                            "expected_chapter": 8,
                            "strength": 5,
                            "secret_note": "掌柜中了寒鸦蛊",
                        },
                    },
                    {
                        "op": "create",
                        "entity_id": fs_future_id,
                        "kind": "伏笔",
                        "name": "第三章城主密信",
                        "text": "第三章才出现的密信",
                        "data": {
                            "position": 3,
                            "status": "已埋设",
                            "line_type": "明线",
                            "planted_chapter": 3,
                            "expected_chapter": 10,
                        },
                    },
                    {
                        "op": "create",
                        "entity_id": fs_planned_id,
                        "kind": "伏笔",
                        "name": "未埋设伏笔",
                        "text": "计划埋设但尚未落笔",
                        "data": {
                            "position": 4,
                            "status": "待埋设",
                            "line_type": "明线",
                            "planted_chapter": 1,
                        },
                    },
                    {
                        "op": "create",
                        "entity_id": fs_dark_unanchored_id,
                        "kind": "伏笔",
                        "name": "无埋设章暗线",
                        "text": "纯作者暗线备忘",
                        "data": {
                            "position": 5,
                            "status": "推进中",
                            "line_type": "暗线",
                        },
                    },
                ],
            )

        app = create_app(Settings(database_url="unused", public_origin="http://testserver"), factory)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client, httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as reader_client:
            a_login = await client.post(
                "/api/v1/auth/login",
                headers={"x-ncc-client": "console"},
                json={"username": author_username, "password": factory.credentials[ids[0]]},
            )
            headers = {"x-csrf-token": a_login.json()["csrf"]}

            r_login = await reader_client.post(
                "/api/v1/auth/login",
                headers={"x-ncc-client": "console"},
                json={"username": reader_username, "password": factory.credentials[ids[1]]},
            )
            r_headers = {"x-csrf-token": r_login.json()["csrf"]}

            # Read-only member cannot PUT /studio/founding -> 403
            forbid_founding = await reader_client.put(
                f"/api/v1/scopes/{sid}/studio/founding",
                headers=r_headers,
                json={"soul_question": "越权写入"},
            )
            assert forbid_founding.status_code == 403

            # Author saves founding card -> 200 + Audit recorded
            founding_payload = {
                "soul_question": "弱者在铁律崩坏之世如何守诺？",
                "soul_answer": "以凡铁铸新约，不借神明一分力。",
                "soul_injustice": "世家垄断灵脉却令寒门戍边。",
                "soul_ending": "斩断灵脉锁链，归隐边城铁铺。",
                "soul_arc": "正向",
                "soul_status": "确定",
                "contract_main": "低开高走硬派仙侠",
                "contract_extras": ["师徒传承", "群像智斗"],
                "contract_audience": "偏爱逻辑闭环与代价感的老白读者",
                "poison_lines": ["主角无脑圣母", "战力崩坏秒天秒地"],
                "writing_mode": "混合",
                "style_anchor": "多用铁器、风雪、炭火意象，对白短促留白。",
            }
            put_res = await client.put(
                f"/api/v1/scopes/{sid}/studio/founding",
                headers=headers,
                json=founding_payload,
            )
            assert put_res.status_code == 200, put_res.text
            assert put_res.json()["founding"] == founding_payload

            async with factory() as db:
                audit_row = await db.scalar(
                    select(Audit).where(Audit.scope_id == sid, Audit.action == "studio.founding")
                )
                assert audit_row is not None

            # AuthorDraft round-trips chapter_status
            save_draft_res = await client.put(
                f"/api/v1/scopes/{sid}/author-drafts/ch-2-draft",
                headers=headers,
                json={
                    "version": 0,
                    "entity_id": c2_id,
                    "name": "第二章 断刀",
                    "text": "修订中的断刀正文",
                    "chapter_status": "done",
                },
            )
            assert save_draft_res.status_code == 200, save_draft_res.text
            assert save_draft_res.json()["chapter_status"] == "done"
            get_draft_res = await client.get(f"/api/v1/scopes/{sid}/author-drafts/ch-2-draft")
            assert get_draft_res.status_code == 200
            assert get_draft_res.json()["chapter_status"] == "done"

            # Author overview includes volume text/description, foreshadow text/strength/secret_note, founding, view_context
            author_ov = (await client.get(f"/api/v1/scopes/{sid}/studio/overview")).json()
            assert author_ov["founding"] == founding_payload
            assert author_ov["view_context"] == {"role": "author", "chapter_id": None}
            assert author_ov["volumes"][0]["text"] == "第一卷卷纲总述：少年走出边城。"
            assert author_ov["volumes"][0]["description"] == "边城开局卷"
            assert len(author_ov["chapters"]) == 3
            assert len(author_ov["foreshadows"]) == 5
            fs1_author = next(f for f in author_ov["foreshadows"] if f["id"] == fs_vis_id)
            assert fs1_author["text"] == "第一章铁炉下露出的半枚残印"
            assert fs1_author["strength"] == 4
            assert fs1_author["secret_note"] == "实为镇国虎符残片"

            # Reader anti-spoiler overview at chapter 2 hides future Ch 3, strips secret_note, and hides unplanted/future foreshadows
            reader_ov = (
                await client.get(
                    f"/api/v1/scopes/{sid}/studio/overview?role=reader&chapter_id={c2_id}"
                )
            ).json()
            assert reader_ov["view_context"] == {"role": "reader", "chapter_id": c2_id}
            assert [c["id"] for c in reader_ov["chapters"]] == [c1_id, c2_id]
            reader_fs_ids = [f["id"] for f in reader_ov["foreshadows"]]
            assert reader_fs_ids == [fs_vis_id, fs_dark_ok_id]
            for f_item in reader_ov["foreshadows"]:
                assert f_item["secret_note"] == ""
            assert "虎符" not in json.dumps(reader_ov, ensure_ascii=False)
            assert "寒鸦蛊" not in json.dumps(reader_ov, ensure_ascii=False)
    finally:
        await _cleanup_scopes(factory, created_scopes)


async def test_workspace_bidirectional_settings_founding_chapter_status_and_idempotency(store):
    factory, ids = store
    suffix = secrets.token_urlsafe(6)
    created_scopes: list[str] = []
    char_shen_id = uid()
    sect_qing_id = uid()
    ch1_id = uid()
    ch2_id = uid()

    try:
        async with factory() as db, db.begin():
            svc = Service(db, await db.get(User, ids[0]))
            sid = (await svc.create_scope(ScopeInput(name=f"双向设定同步-{suffix}")))["id"]
            created_scopes.append(sid)

            s_row = await db.get(Scope, sid)
            s_row.config = {
                **(s_row.config or {}),
                "founding": {
                    "soul_question": "何以为剑？",
                    "soul_answer": "护身前尺地。",
                    "soul_injustice": "宗门视苍生为炉鼎。",
                    "soul_ending": "碎鼎重开山门。",
                    "soul_arc": "平弧",
                    "soul_status": "暂定",
                    "contract_main": "古典仙侠群像",
                    "contract_extras": ["宗门经营"],
                    "contract_audience": "仙侠读者",
                    "poison_lines": ["机械降神"],
                    "writing_mode": "建筑师",
                    "style_anchor": "克制白描，重动作质感。",
                },
            }

            interview_raw = "# 沈青采访\n\n问：你最怕什么？\n".encode()
            await _commit_ops(
                svc,
                sid,
                [
                    {
                        "op": "create",
                        "entity_id": char_shen_id,
                        "kind": "character",
                        "name": "沈青",
                        "text": "外门执剑弟子，性情孤直。",
                        "data": {"motivation": "查清师兄死因", "secret_note": "身负断剑残魂"},
                    },
                    {
                        "op": "create",
                        "entity_id": sect_qing_id,
                        "kind": "宗门",
                        "name": "青云宗",
                        "text": "北境第一剑宗。",
                    },
                    {
                        "op": "create",
                        "entity_id": ch1_id,
                        "kind": "chapter",
                        "name": "第一章 问剑",
                        "text": "山门石阶覆满积雪。",
                        "data": {"position": 1, "status": "done"},
                    },
                    {
                        "op": "create",
                        "entity_id": ch2_id,
                        "kind": "chapter",
                        "name": "第二章 藏锋",
                        "text": "藏经阁烛火摇曳。",
                        "data": {"position": 2, "status": "review"},
                    },
                    {
                        "op": "create",
                        "kind": "legacy-file",
                        "name": "01-设定/人物卡/沈青-采访.md",
                        "text": interview_raw.decode("utf-8"),
                        "data": {
                            "legacy_path": "01-设定/人物卡/沈青-采访.md",
                            "encoding": "utf-8",
                            "content_hash": digest(interview_raw),
                        },
                    },
                ],
            )

            snap1 = await svc.workspace_snapshot(sid)
            snap1_map = {f["path"]: base64.b64decode(f["base64"]) for f in snap1["files"]}

            assert "01-设定/人物卡/沈青.md" in snap1_map
            assert "01-设定/人物卡/沈青-采访.md" in snap1_map
            assert "01-设定/类目/宗门/青云宗.md" in snap1_map
            assert "03-文风/文风基准.md" in snap1_map

            shen_md = snap1_map["01-设定/人物卡/沈青.md"].decode("utf-8")
            assert f'"id":"{char_shen_id}"' in shen_md
            assert "# 沈青" in shen_md
            assert "外门执剑弟子，性情孤直。" in shen_md
            assert "## 作者秘密\n\n身负断剑残魂" in shen_md
            assert snap1_map["03-文风/文风基准.md"].decode("utf-8").strip() == "克制白描，重动作质感。"

            book_json = json.loads(snap1_map["book.json"].decode("utf-8"))
            assert book_json["soul"]["question"] == "何以为剑？"
            assert book_json["soul"]["arc"] == "平弧"
            assert book_json["contract"]["main"] == "古典仙侠群像"
            assert book_json["contract"]["poison"] == ["机械降神"]
            assert book_json["mode"] == "建筑师"
            assert [c["status"] for c in book_json["chapters"]] == ["done", "reviewing"]

            # 1) Unmodified snapshot -> commit MUST be 100% idempotent (unchanged: True)
            noop_res = await svc.workspace_commit(
                sid,
                {
                    "format": "ncc.workspace/1",
                    "base_version": snap1["version"],
                    "files": snap1["files"],
                    "request_id": f"noop-{suffix}",
                },
            )
            assert noop_res.get("unchanged") is True
            assert noop_res["version"] == snap1["version"]

            # 2) Edit CLI files: modify 沈青.md, add 类目/门派/天剑门.md & 世界观圣经.md, delete 青云宗.md, update book.json + style
            updated_shen = (
                f'<!-- ncc-studio: {{"id":"{char_shen_id}","kind":"character"}} -->\n'
                "# 沈青\n\n已破境入内门，执掌寒鸦剑。\n\n## 作者秘密\n\n剑魂已苏醒第一重\n"
            ).encode()
            new_sect_md = "# 门派：天剑门\n\n西州剑修圣地，专修快剑。\n".encode()
            bible_md = "# 天道铁律\n\n灵气总量守恒，破境必有天衰。\n".encode()
            new_style_md = "冷冽凝练，多用短句与金石声响。\n".encode()

            book_json["soul"]["question"] = "天道有缺，谁补苍穹？"
            book_json["soul"]["status"] = "确定"
            book_json["chapters"][1]["status"] = "done"
            new_book_bytes = (json.dumps(book_json, ensure_ascii=False, indent=2) + "\n").encode()

            commit_files = [
                {
                    "path": "01-设定/人物卡/沈青.md",
                    "base64": base64.b64encode(updated_shen).decode(),
                    "sha256": digest(updated_shen),
                },
                {
                    "path": "01-设定/类目/门派/天剑门.md",
                    "base64": base64.b64encode(new_sect_md).decode(),
                    "sha256": digest(new_sect_md),
                },
                {
                    "path": "01-设定/世界观圣经.md",
                    "base64": base64.b64encode(bible_md).decode(),
                    "sha256": digest(bible_md),
                },
                {
                    "path": "01-设定/类目/宗门/青云宗.md",
                    "deleted": True,
                },
                {
                    "path": "03-文风/文风基准.md",
                    "base64": base64.b64encode(new_style_md).decode(),
                    "sha256": digest(new_style_md),
                },
                {
                    "path": "book.json",
                    "base64": base64.b64encode(new_book_bytes).decode(),
                    "sha256": digest(new_book_bytes),
                },
            ]
            commit_res = await svc.workspace_commit(
                sid,
                {
                    "format": "ncc.workspace/1",
                    "base_version": snap1["version"],
                    "files": commit_files,
                    "request_id": f"cli-sync-{suffix}",
                },
            )
            assert commit_res["coverage"]["typed_settings"] >= 3

            # Verify Studio entities reflect CLI edits while preserving existing extra properties (motivation)
            shen_after = await svc.entity(sid, char_shen_id)
            assert shen_after["text"] == "已破境入内门，执掌寒鸦剑。"
            assert shen_after["data"]["secret_note"] == "剑魂已苏醒第一重"
            assert shen_after["data"]["motivation"] == "查清师兄死因"

            # 青云宗 retired
            qing_retired = await svc.entity(sid, sect_qing_id, Query(include_deleted=True))
            assert qing_retired["deleted"] is True

            # 天剑门 mapped alias 门派 -> 宗门; 世界观圣经.md -> 法则; 采访 file NOT turned into 人物
            active_items = (await svc.entities(sid, Query(limit=100)))["items"]
            tianjian = next(x for x in active_items if x["name"] == "天剑门")
            assert tianjian["kind"] == "宗门"
            bible_ent = next(x for x in active_items if x["name"] == "天道铁律")
            assert bible_ent["kind"] == "法则"
            assert not any("采访" in x["name"] and x["kind"] in {"character", "人物"} for x in active_items)

            # Chapter 2 status synced to "done", founding updated
            ch2_after = await svc.entity(sid, ch2_id)
            assert ch2_after["data"]["status"] == "done"
            s_info = await svc.scope_info(sid)
            assert s_info["config"]["founding"]["soul_question"] == "天道有缺，谁补苍穹？"
            assert s_info["config"]["founding"]["soul_status"] == "确定"
            assert s_info["config"]["founding"]["style_anchor"] == "冷冽凝练，多用短句与金石声响。"

            # 3) Second snapshot -> commit round-trip is ALSO 100% idempotent
            snap2 = await svc.workspace_snapshot(sid)
            snap2_paths = {f["path"] for f in snap2["files"]}
            assert "01-设定/类目/宗门/青云宗.md" not in snap2_paths
            noop_res2 = await svc.workspace_commit(
                sid,
                {
                    "format": "ncc.workspace/1",
                    "base_version": snap2["version"],
                    "files": snap2["files"],
                    "request_id": f"noop2-{suffix}",
                },
            )
            assert noop_res2.get("unchanged") is True
            assert noop_res2["version"] == snap2["version"]
    finally:
        await _cleanup_scopes(factory, created_scopes)
