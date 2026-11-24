"""End-to-end synthetic browser acceptance for Producer Novel Studio, U01-U03, R09, R11, R02/R03."""

import argparse
import json
import re
from pathlib import Path
from uuid import uuid4

import httpx
from _bootstrap import browser_test
from playwright.sync_api import expect, sync_playwright


def _clear_codemirror(page):
    editor = page.locator(".writing-card .cm-content")
    editor.click()
    page.keyboard.press("Meta+a")
    page.keyboard.press("Backspace")


def _seed_job_state(conn, job_id: str, state: str, result: dict, progress: dict | None = None):
    conn.execute(
        "UPDATE ncc_job SET state = %s, result = %s::jsonb, progress = %s::jsonb WHERE id = %s",
        (state, json.dumps(result, ensure_ascii=False), json.dumps(progress or {}, ensure_ascii=False), job_id),
    )


@browser_test
def main(runtime):
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=runtime.origin)
    parser.add_argument("--output", type=Path, default=Path("/tmp/ncc-studio-browser"))
    args = parser.parse_args()
    assert args.url == runtime.origin, "浏览器测试只允许本次启动的-test服务"
    args.output.mkdir(parents=True, exist_ok=True)

    pre_scope_ids = {
        r[0] for r in runtime.connection.execute("SELECT id FROM ncc_scope").fetchall()
    }
    pre_rev_Digest = runtime.connection.execute(
        "SELECT count(*), coalesce( max(version), 0 ) FROM ncc_revision WHERE scope_id = ANY(%s)",
        (list(pre_scope_ids),),
    ).fetchone()

    scope_name = "制片人工作台验收-" + uuid4().hex[:6]
    username, password = runtime.new_credentials("studio-author")
    collab_username, collab_password = runtime.new_credentials("studio-author")

    with httpx.Client(base_url=args.url, timeout=30) as admin_client:
        auth = (
            admin_client.post(
                "/api/v1/auth/login",
                headers={"x-ncc-client": "console"},
                json={"username": runtime.username, "password": runtime.password},
            )
            .raise_for_status()
            .json()
        )
        admin_csrf = {"x-csrf-token": auth["csrf"]}
        author_user = (
            admin_client.post(
                "/api/v1/users",
                headers=admin_csrf,
                json={"username": username, "password": password},
            )
            .raise_for_status()
            .json()
        )
        collab_user = (
            admin_client.post(
                "/api/v1/users",
                headers=admin_csrf,
                json={"username": collab_username, "password": collab_password},
            )
            .raise_for_status()
            .json()
        )

    with sync_playwright() as p:
        chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        browser = p.chromium.launch(
            headless=True, executable_path=str(chrome) if chrome.exists() else None
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000}, device_scale_factor=1
        )
        page = context.new_page()
        page.set_default_timeout(15000)
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))

        # 1. Login as ordinary non-admin author & create synthetic book scope (R01 normal entry)
        page.goto(args.url + "/work")
        page.get_by_label("账号", exact=True).fill(username)
        page.get_by_label("密码", exact=True).fill(password)
        page.get_by_role("button", name=re.compile(r"登\s*录")).click()
        page.get_by_role("button", name="新建作品或资料库").click()
        page.get_by_label("名称", exact=True).fill(scope_name)
        page.get_by_role("button", name="确 定", exact=True).click()
        expect(page.get_by_role("dialog")).not_to_be_visible()

        # Prepare authenticated HTTP client for server read-back & concurrent edit simulation
        user_client = httpx.Client(base_url=args.url, timeout=30)
        u_auth = (
            user_client.post(
                "/api/v1/auth/login",
                headers={"x-ncc-client": "console"},
                json={"username": username, "password": password},
            )
            .raise_for_status()
            .json()
        )
        u_headers = {"x-csrf-token": u_auth["csrf"], "x-ncc-client": "console"}
        scopes = user_client.get("/api/v1/scopes", headers=u_headers).raise_for_status().json()
        book_scope = next(s for s in scopes if s["name"] == scope_name)
        sid = book_scope["id"]

        # Verify R01: ordinary author GET /studio/overview returns 200
        ov_resp = user_client.get(f"/api/v1/scopes/{sid}/studio/overview", headers=u_headers)
        assert ov_resp.status_code == 200, ov_resp.text

        # 2. Verify 6 daily navigation spaces + collapsed-by-default Advanced group + topbar AI shortcut
        nav = page.get_by_role("navigation", name="创作后台导航")
        for label in ("创作台", "大纲与暗线", "作品资料", "公共陈列库", "市场与风向", "我的待办"):
            expect(nav.get_by_role("button", name=label, exact=True)).to_be_visible()
        adv_btn = nav.get_by_role("button", name="高级管理", exact=True)
        expect(adv_btn).to_have_attribute("aria-expanded", "false")
        expect(nav.get_by_role("button", name="定义中心", exact=True)).not_to_be_visible()

        page.locator("header.topbar").get_by_role("button", name="AI 配置").click()
        expect(adv_btn).to_have_attribute("aria-expanded", "true")
        expect(nav.get_by_role("button", name="定义中心", exact=True)).to_be_visible()
        nav.get_by_role("button", name="创作台", exact=True).click()

        # 3. /work: VolumeRail + Chapter creation + R02 Han count ("二〇二六。" == 4)
        rail = page.get_by_role("complementary", name="卷章与细纲目录")
        rail.get_by_label("新卷名称", exact=True).fill("第一卷 · 北境风雪")
        rail.get_by_role("button", name="新建卷", exact=True).click()
        expect(rail.get_by_role("heading", name="第一卷 · 北境风雪")).to_be_visible()

        rail.get_by_label("新章节名称", exact=True).fill("第一章 · 寒鸦渡")
        rail.get_by_role("button", name="新建章节", exact=True).click()
        expect(rail.get_by_text("第一章 · 寒鸦渡", exact=False)).to_be_visible()

        # R02 supplement: verify "二〇二六。" counts as 4 Han chars consistently on frontend & backend
        page.locator(".writing-card .cm-content").fill("二〇二六。")
        expect(page.locator(".editor-footer")).to_contain_text("汉字 4")
        page.get_by_role("button", name="保存修订").click()
        expect(page.locator(".writing-card")).to_contain_text("已保存修订")
        ov_han = user_client.get(f"/api/v1/scopes/{sid}/studio/overview", headers=u_headers).raise_for_status().json()
        ch1 = next(c for c in ov_han["chapters"] if c["name"] == "第一章 · 寒鸦渡")
        ch1_id = ch1["id"]
        assert ch1["char_count"] == 4, ch1
        assert ov_han["diagnostics"]["total_chars"] == 4, ov_han["diagnostics"]

        # Update Chapter 1 with synthetic prose for U01 baseline
        page.locator(".writing-card .cm-content").fill("寒鸦渡的夜雪落在石阶上，更夫敲过三更。")
        expect(page.locator(".writing-card")).to_contain_text("未保存修改")
        page.get_by_role("button", name="保存修订").click()
        expect(page.locator(".writing-card")).to_contain_text("已保存修订")
        ch1_baseline = user_client.get(f"/api/v1/scopes/{sid}/entities/{ch1_id}", headers=u_headers).raise_for_status().json()["version"]

        # 4. U01 acceptance: metadata-only edit, clear-text-only edit, combined edit, status accuracy & reload/leave recovery
        # U01-A: Edit metadata ONLY (beat, hook, pov, plotline, targetWords, keyChapter, scheme)
        page.get_by_text("本章把控", exact=True).click()
        page.get_by_label("本章细纲", exact=True).fill("起：寒鸦渡三更雪；承：检验旧伤；转：黑衣人窥渡；钩：渡船底藏着密信。")
        page.get_by_label("章尾追读钩", exact=True).fill("船板夹层露出火漆密信")
        page.get_by_label("视角人物", exact=True).fill("沈砚")
        page.get_by_label("所属剧情线", exact=True).fill("主线·寒鸦渡")
        page.get_by_label("目标字数", exact=True).fill("3200")
        page.get_by_role("switch", name="关键章").click()
        cockpit = page.get_by_role("complementary", name="出品人工作舱")
        cockpit.get_by_label("评分方案", exact=True).click()
        page.locator(".ant-select-item-option").filter(has_text="修改与更新").first.click()
        # Immediately after changing scheme, status must NOT claim everything is saved yet
        expect(page.locator(".editor-footer")).to_contain_text("未保存修改")
        # Wait for debounced auto-save to succeed
        expect(page.locator(".editor-footer")).to_contain_text("草稿已自动保存", timeout=10000)

        draft_a = user_client.get(f"/api/v1/scopes/{sid}/author-drafts/{ch1_id}", headers=u_headers).raise_for_status().json()
        assert draft_a["baseline"] == ch1_baseline, draft_a
        assert draft_a["beat_outline"].startswith("起：寒鸦渡三更雪"), draft_a
        assert draft_a["hook"] == "船板夹层露出火漆密信", draft_a
        assert draft_a["pov"] == "沈砚", draft_a
        assert draft_a["plotline"] == "主线·寒鸦渡", draft_a
        assert draft_a["target_words"] == "3200", draft_a
        assert draft_a["key_chapter"] is True, draft_a
        assert draft_a["scheme"] == "P5", draft_a

        # Reload browser and verify same chapter, same baseline, and all metadata fields recover
        page.reload()
        expect(page.locator(".editor-footer")).to_contain_text("已恢复自动保存的草稿", timeout=10000)
        expect(page.get_by_label("稿件名称", exact=True)).to_have_value("第一章 · 寒鸦渡")
        expect(page.locator(".writing-card .cm-content")).to_contain_text("寒鸦渡的夜雪落在石阶上")
        expect(page.get_by_label("本章细纲", exact=True)).to_have_value("起：寒鸦渡三更雪；承：检验旧伤；转：黑衣人窥渡；钩：渡船底藏着密信。")
        expect(page.get_by_label("章尾追读钩", exact=True)).to_have_value("船板夹层露出火漆密信")
        expect(page.get_by_label("视角人物", exact=True)).to_have_value("沈砚")
        expect(page.get_by_label("所属剧情线", exact=True)).to_have_value("主线·寒鸦渡")
        expect(page.get_by_label("目标字数", exact=True)).to_have_value("3200")
        expect(page.get_by_role("switch", name="关键章")).to_have_attribute("aria-checked", "true")

        # U01-B: Clear prose text ONLY while keeping metadata, auto-save, leave to /materials & return/reload
        _clear_codemirror(page)
        expect(page.locator(".editor-footer")).to_contain_text("草稿已自动保存", timeout=10000)
        page.reload()
        expect(page.locator(".editor-footer")).to_contain_text("已恢复自动保存的草稿", timeout=10000)
        expect(page.locator(".writing-card .cm-content")).to_have_text("")
        expect(page.get_by_label("本章细纲", exact=True)).to_have_value("起：寒鸦渡三更雪；承：检验旧伤；转：黑衣人窥渡；钩：渡船底藏着密信。")

        # U01-C: Edit prose & metadata together, leave via sidebar (confirm leave), return & verify, then formally save ch1
        page.locator(".writing-card .cm-content").fill("风雪压低了寒鸦渡的芦苇。沈砚拂去旧铁牌上的泥霜，指腹触到一道熟悉的刻痕。")
        page.get_by_label("章尾追读钩", exact=True).fill("铁牌背面的师门暗记在火光下渗出红锈")
        expect(page.locator(".editor-footer")).to_contain_text("草稿已自动保存", timeout=10000)
        nav.get_by_role("button", name="作品资料", exact=True).click()
        leave_modal = page.get_by_role("dialog", name="保留当前未保存内容？")
        expect(leave_modal).to_be_visible()
        leave_modal.get_by_role("button", name=re.compile(r"^离\s*开$")).click()
        expect(page.get_by_role("heading", name="作品资料")).to_be_visible()
        nav.get_by_role("button", name="创作台", exact=True).click()
        page.get_by_label("编辑对象", exact=True).click()
        page.locator(".ant-select-item-option").filter(has_text="第一章 · 寒鸦渡").first.click()
        expect(page.locator(".editor-footer")).to_contain_text("已恢复自动保存的草稿", timeout=10000)
        expect(page.locator(".writing-card .cm-content")).to_contain_text("风雪压低了寒鸦渡的芦苇")
        expect(page.get_by_label("章尾追读钩", exact=True)).to_have_value("铁牌背面的师门暗记在火光下渗出红锈")
        cockpit = page.get_by_role("complementary", name="出品人工作舱")
        cockpit.get_by_label("评分方案", exact=True).click()
        page.locator(".ant-select-item-option").filter(has_text="正文章节").first.click()
        page.get_by_role("button", name="保存修订").click()
        expect(page.locator(".writing-card")).to_contain_text("已保存修订")

        # 5. U02 acceptance: Create Chapter 2 (乙章), make unsaved edits, create Chapter 3 (丙章) -> shared draft guard & isolated targets
        rail = page.get_by_role("complementary", name="卷章与细纲目录")
        rail.get_by_label("新章节名称", exact=True).fill("第二章 · 旧铁牌")
        rail.get_by_role("button", name="新建章节", exact=True).click()
        expect(page.get_by_label("稿件名称", exact=True)).to_have_value("第二章 · 旧铁牌")
        page.locator(".writing-card .cm-content").fill("乙章已保存正式版：沈砚在渡口茶寮核对旧铁牌。")
        page.get_by_role("button", name="保存修订").click()
        expect(page.locator(".writing-card")).to_contain_text("已保存修订")
        ov_u02 = user_client.get(f"/api/v1/scopes/{sid}/studio/overview", headers=u_headers).raise_for_status().json()
        ch2_id = next(c["id"] for c in ov_u02["chapters"] if c["name"] == "第二章 · 旧铁牌")

        # Now type unsaved draft in 乙章
        page.locator(".writing-card .cm-content").fill("乙章未保存草稿文字：茶寮外传来三声梆子响。")
        expect(page.locator(".editor-footer")).to_contain_text("未保存修改")

        # Attempt to create 丙章 while 乙章 is dirty -> must prompt leave guard; cancel keeps 乙章
        rail.get_by_label("新章节名称", exact=True).fill("第三章 · 夜渡芦苇")
        rail.get_by_role("button", name="新建章节", exact=True).click()
        switch_dialog = page.get_by_role("dialog", name="离开未保存的编辑？")
        expect(switch_dialog).to_be_visible()
        switch_dialog.get_by_role("button", name="继续编辑", exact=True).click()
        expect(switch_dialog).not_to_be_visible()
        expect(page.get_by_label("稿件名称", exact=True)).to_have_value("第二章 · 旧铁牌")
        expect(page.locator(".writing-card .cm-content")).to_contain_text("乙章未保存草稿文字")

        # Confirm creating 丙章 -> flushes 乙章 draft to ch2_id, opens clean 丙章, saves formal text to 丙章 only
        rail.get_by_role("button", name="新建章节", exact=True).click()
        switch_dialog = page.get_by_role("dialog", name="离开未保存的编辑？")
        expect(switch_dialog).to_be_visible()
        switch_dialog.get_by_role("button", name="离开当前章节", exact=True).click()
        expect(page.get_by_label("稿件名称", exact=True)).to_have_value("第三章 · 夜渡芦苇")
        expect(page.locator(".writing-card .cm-content")).to_have_text("")
        page.locator(".writing-card .cm-content").fill("丙章正式正文：芦苇荡中孤舟无声滑入夜雾。")
        page.get_by_role("button", name="保存修订").click()
        expect(page.locator(".writing-card")).to_contain_text("已保存修订")

        # Server read-back of BOTH 乙章 and 丙章
        ov_after_u02 = user_client.get(f"/api/v1/scopes/{sid}/studio/overview", headers=u_headers).raise_for_status().json()
        ch3_id = next(c["id"] for c in ov_after_u02["chapters"] if c["name"] == "第三章 · 夜渡芦苇")
        ch2_entity = user_client.get(f"/api/v1/scopes/{sid}/entities/{ch2_id}", headers=u_headers).raise_for_status().json()
        ch2_draft = user_client.get(f"/api/v1/scopes/{sid}/author-drafts/{ch2_id}", headers=u_headers).raise_for_status().json()
        ch3_entity = user_client.get(f"/api/v1/scopes/{sid}/entities/{ch3_id}", headers=u_headers).raise_for_status().json()
        assert ch2_entity["text"] == "乙章已保存正式版：沈砚在渡口茶寮核对旧铁牌。", ch2_entity
        assert ch2_draft["text"] == "乙章未保存草稿文字：茶寮外传来三声梆子响。", ch2_draft
        assert ch3_entity["name"] == "第三章 · 夜渡芦苇", ch3_entity
        assert ch3_entity["text"] == "丙章正式正文：芦苇荡中孤舟无声滑入夜雾。", ch3_entity
        page.screenshot(path=str(args.output / "u01-u02-creative.png"), full_page=True)

        # CreativePage concurrent conflict check on 乙章: update 乙章 via API while 乙章 still has its earlier draft
        ch2_upd_change = (
            user_client.post(
                f"/api/v1/scopes/{sid}/changes",
                headers={**u_headers, "idempotency-key": str(uuid4())},
                json={
                    "title": "他窗并发更新乙章",
                    "base_version": user_client.get(f"/api/v1/scopes/{sid}", headers=u_headers).raise_for_status().json()["version"],
                    "operations": [
                        {
                            "op": "update",
                            "entity_id": ch2_id,
                            "expected": ch2_entity["version"],
                            "text": "乙章他窗并发新版：茶寮掌柜悄悄关上了后窗。",
                        }
                    ],
                },
            )
            .raise_for_status()
            .json()
        )
        user_client.post(
            f"/api/v1/scopes/{sid}/changes/{ch2_upd_change['id']}/adopt",
            headers={**u_headers, "idempotency-key": str(uuid4())},
            json={},
        ).raise_for_status()
        rail.get_by_role("button", name=re.compile("第二章 · 旧铁牌")).click()
        expect(page.locator(".writing-card")).to_contain_text("这一章在别处更新了。你的字还在编辑器里。", timeout=10000)
        expect(page.locator(".writing-card")).to_contain_text("乙章他窗并发新版")
        expect(page.locator(".writing-card .cm-content")).to_contain_text("乙章未保存草稿文字")
        page.screenshot(path=str(args.output / "creative-conflict.png"), full_page=True)
        page.get_by_role("button", name="基于新版保存我的修改", exact=True).click()
        expect(page.locator(".writing-card")).to_contain_text("已保存修订")

        # Focus Mode + Codex Lookup + Composable single-stage ["plan"] task
        page.get_by_role("button", name="进入专注", exact=True).click()
        expect(page.locator("html")).to_have_class(re.compile("studio-focus-mode"))
        expect(page.locator(".sidebar")).not_to_be_visible()
        page.keyboard.press("Escape")
        expect(page.locator(".sidebar")).to_be_visible()

        cockpit = page.get_by_role("complementary", name="出品人工作舱")
        cockpit.get_by_role("tab", name="设定速查").click()
        cockpit.get_by_role("button", name="快建新设定").click()
        modal = page.get_by_role("dialog", name="快建新设定")
        modal.get_by_label("名称").fill("北境黑铁令")
        modal.get_by_label("类别").fill("功法")
        page.locator(".ant-select-item-option").filter(has_text="功法").first.click()
        modal.get_by_label("摘要").fill("北境镇守使信物，内藏玄铁剑气。")
        modal.get_by_role("button", name="确 定").click()
        expect(modal).not_to_be_visible()
        cockpit.get_by_role("button", name="挂载给 AI").first.click()

        cockpit.get_by_role("tab", name="AI 协同").click()
        cockpit.get_by_role("button", name="单推细纲", exact=True).click()
        cockpit.get_by_label("创作目标", exact=True).fill("推演第二章旧铁牌引出的伏击冲突节拍。")
        cockpit.get_by_label("出品人方向指引", exact=True).fill("保持冷峻克制叙事，不要提前暴露幕后主使。")
        cockpit.get_by_role("button", name="开始处理", exact=True).click()
        expect(page.get_by_text("已进入自动创作流程", exact=True)).to_be_visible()
        page.screenshot(path=str(args.output / "studio-work.png"), full_page=True)

        # 6. /blueprint & U03 acceptance: Outline create, slice switch retention, leave guard, return retention, concurrent conflict dual-version handling
        nav.get_by_role("button", name="大纲与暗线", exact=True).click()
        page.get_by_role("button", name="新建总纲", exact=True).click()
        page.get_by_label("总纲名称", exact=True).fill("北境长歌总纲")
        page.get_by_role("button", name=re.compile(r"^保\s*存$")).click()
        expect(page.get_by_role("heading", name="北境长歌总纲")).to_be_visible()
        page.get_by_label("总纲细纲", exact=True).fill("第一卷破局寒鸦渡；第二卷入京查旧案。")
        page.get_by_role("button", name="保存总纲", exact=True).click()
        expect(page.get_by_text("总纲已保存")).to_be_visible()

        ov_bp = user_client.get(f"/api/v1/scopes/{sid}/studio/overview", headers=u_headers).raise_for_status().json()
        outline_obj = next(o for o in ov_bp["outlines"] if o["name"] == "北境长歌总纲")
        outline_id = outline_obj["id"]
        outline_v1 = outline_obj["version"]

        # Edit outline without saving (freezes baseVersion = outline_v1)
        page.get_by_label("总纲细纲", exact=True).fill("窗口一草稿：第三卷封狼居胥，揭开北境铁牌真相。")
        expect(page.get_by_text("当前有未保存的大纲或细纲草稿")).to_be_visible()

        # Slice switch retains draft
        page.get_by_text("细纲卡片墙", exact=True).click()
        expect(page.get_by_role("heading", name=re.compile("第二章 · 旧铁牌"))).to_be_visible()
        page.get_by_text("总纲与剧情走向", exact=True).click()
        expect(page.get_by_label("总纲细纲", exact=True)).to_have_value("窗口一草稿：第三卷封狼居胥，揭开北境铁牌真相。")

        # Sidebar leave guard prompts -> stay -> leave -> return restores session draft
        nav.get_by_role("button", name="市场与风向", exact=True).click()
        bp_leave = page.get_by_role("dialog", name="保留当前未保存内容？")
        expect(bp_leave).to_be_visible()
        bp_leave.get_by_role("button", name="继续编辑", exact=True).click()
        expect(bp_leave).not_to_be_visible()
        expect(page.get_by_label("总纲细纲", exact=True)).to_have_value("窗口一草稿：第三卷封狼居胥，揭开北境铁牌真相。")

        nav.get_by_role("button", name="市场与风向", exact=True).click()
        bp_leave = page.get_by_role("dialog", name="保留当前未保存内容？")
        bp_leave.get_by_role("button", name=re.compile(r"^离\s*开$")).click()
        expect(page.get_by_role("region", name="连载健康度")).to_be_visible()

        # While away on /market, simulate concurrent update from another window advancing outline version
        fresh_scope_v = user_client.get(f"/api/v1/scopes/{sid}", headers=u_headers).raise_for_status().json()["version"]
        conc_change = (
            user_client.post(
                f"/api/v1/scopes/{sid}/changes",
                headers={**u_headers, "idempotency-key": str(uuid4())},
                json={
                    "title": "另一窗口更新总纲",
                    "base_version": fresh_scope_v,
                    "operations": [
                        {
                            "op": "update",
                            "entity_id": outline_id,
                            "expected": outline_v1,
                            "data": {
                                "beat_outline": "窗口二已保存新版：第三卷先入寒渊再决战王庭。",
                                "plotline": "北境王庭暗线",
                            },
                        }
                    ],
                },
            )
            .raise_for_status()
            .json()
        )
        user_client.post(
            f"/api/v1/scopes/{sid}/changes/{conc_change['id']}/adopt",
            headers={**u_headers, "idempotency-key": str(uuid4())},
            json={},
        ).raise_for_status()

        # Return to /blueprint -> conflict alert preserves BOTH server version and local draft!
        nav.get_by_role("button", name="大纲与暗线", exact=True).click()
        expect(page.locator(".blueprint-page")).to_contain_text("检测到并发更新冲突", timeout=10000)
        expect(page.locator(".blueprint-page")).to_contain_text("窗口二已保存新版：第三卷先入寒渊再决战王庭。")
        expect(page.get_by_label("总纲细纲", exact=True)).to_have_value("窗口一草稿：第三卷封狼居胥，揭开北境铁牌真相。")
        expect(page.get_by_role("button", name="保存总纲", exact=True)).to_be_disabled()
        page.screenshot(path=str(args.output / "u03-blueprint-conflict.png"), full_page=True)

        # Resolve conflict by rebasing draft onto latest version
        page.get_by_role("button", name="基于新版保存我的草稿", exact=True).click()
        expect(page.locator(".blueprint-page")).not_to_contain_text("检测到并发更新冲突")
        expect(page.locator(".blueprint-page")).not_to_contain_text("当前有未保存的大纲或细纲草稿")
        saved_outline = user_client.get(f"/api/v1/scopes/{sid}/entities/{outline_id}", headers=u_headers).raise_for_status().json()
        assert saved_outline["data"]["beat_outline"] == "窗口一草稿：第三卷封狼居胥，揭开北境铁牌真相。", saved_outline

        # U03 Counterexample B: ChapterCard direct 409 save without leaving page + "采用服务器最新版" recovery
        page.get_by_text("细纲卡片墙", exact=True).click()
        ch2_card = page.locator("article.blueprint-card").filter(has=page.get_by_role("heading", name=re.compile("第二章 · 旧铁牌")))
        ch2_card.get_by_label("本章细纲", exact=True).fill("细纲墙本地旧基线草稿：准备被服务器新版替代。")
        # Concurrent API update to ch2 while ChapterCard stays mounted with stale baseVersion
        ch2_before_card = user_client.get(f"/api/v1/scopes/{sid}/entities/{ch2_id}", headers=u_headers).raise_for_status().json()
        card_conc = (
            user_client.post(
                f"/api/v1/scopes/{sid}/changes",
                headers={**u_headers, "idempotency-key": str(uuid4())},
                json={
                    "title": "他窗更新乙章细纲卡",
                    "base_version": user_client.get(f"/api/v1/scopes/{sid}", headers=u_headers).raise_for_status().json()["version"],
                    "operations": [
                        {
                            "op": "update",
                            "entity_id": ch2_id,
                            "expected": ch2_before_card["version"],
                            "data": {"beat_outline": "服务器最新乙章细纲：茶寮伏击改在船坞。", "hook": "船坞铁索断裂"},
                        }
                    ],
                },
            )
            .raise_for_status()
            .json()
        )
        user_client.post(
            f"/api/v1/scopes/{sid}/changes/{card_conc['id']}/adopt",
            headers={**u_headers, "idempotency-key": str(uuid4())},
            json={},
        ).raise_for_status()
        # Even if Save is clicked or SSE refreshes, server version must NOT be overwritten; both versions shown
        if ch2_card.get_by_role("button", name="保存这张卡", exact=True).is_enabled():
            ch2_card.get_by_role("button", name="保存这张卡", exact=True).click()
        expect(ch2_card).to_contain_text("检测到并发更新冲突", timeout=10000)
        expect(ch2_card).to_contain_text("服务器最新乙章细纲：茶寮伏击改在船坞。")
        expect(ch2_card).to_contain_text("细纲墙本地旧基线草稿：准备被服务器新版替代。")
        assert (
            user_client.get(f"/api/v1/scopes/{sid}/entities/{ch2_id}", headers=u_headers)
            .raise_for_status()
            .json()["data"]["beat_outline"]
            == "服务器最新乙章细纲：茶寮伏击改在船坞。"
        )
        ch2_card.get_by_role("button", name="采用服务器最新版", exact=True).click()
        expect(ch2_card).not_to_contain_text("检测到并发更新冲突")
        expect(ch2_card.get_by_label("本章细纲", exact=True)).to_have_value("服务器最新乙章细纲：茶寮伏击改在船坞。")

        # Foreshadow Kanban
        page.get_by_text("伏笔与明暗灰线", exact=True).click()
        page.get_by_role("button", name="记下一条伏笔", exact=True).click()
        f_modal = page.get_by_role("dialog", name="记下一条伏笔")
        f_modal.get_by_label("名称").fill("铁牌红锈之谜")
        f_modal.get_by_label("埋设章").fill("1")
        f_modal.get_by_label("期望回收章").fill("1")
        f_modal.get_by_role("button", name="确 定").click()
        expect(f_modal).not_to_be_visible()
        expect(page.get_by_role("heading", name="铁牌红锈之谜")).to_be_visible()
        page.screenshot(path=str(args.output / "studio-blueprint.png"), full_page=True)

        # 7. R09 acceptance: Inbox -> /work & /admin/jobs targeting across 2 chapters, 2 tasks on SAME chapter (plus multi-candidate), failed job targeting, and Return!
        def create_synthetic_task(payload: dict) -> str:
            resp = user_client.post(
                f"/api/v1/scopes/{sid}/creation-tasks",
                headers={**u_headers, "idempotency-key": str(uuid4())},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["id"]

        # Create failed job FIRST so newer jobs sit above it in /admin/jobs (verifies exact row targeting, not rows[0]!)
        job_failed_id = create_synthetic_task(
            {
                "objective": "失败对照：测试模型网关超时定位",
                "scheme": "P1",
                "mode": "create",
                "kind": "chapter",
                "name": "第三章 · 夜渡芦苇",
                "entity_id": ch3_id,
                "stages": ["write"],
            }
        )
        job_ch1_id = create_synthetic_task(
            {
                "objective": "甲章任务：补强寒鸦渡风雪开篇压迫感",
                "scheme": "P1",
                "mode": "create",
                "kind": "chapter",
                "name": "第一章 · 寒鸦渡",
                "entity_id": ch1_id,
                "stages": ["write", "judge"],
            }
        )
        job_ch2_first_id = create_synthetic_task(
            {
                "objective": "乙章同章任务一：突出茶寮刺客夜袭动作节拍",
                "scheme": "P1",
                "mode": "create",
                "kind": "chapter",
                "name": "第二章 · 旧铁牌",
                "entity_id": ch2_id,
                "stages": ["write", "judge"],
            }
        )
        job_ch2_second_id = create_synthetic_task(
            {
                "objective": "乙章同章任务二：突出铁牌师门暗记文戏推理",
                "scheme": "P1",
                "mode": "create",
                "kind": "chapter",
                "name": "第二章 · 旧铁牌",
                "entity_id": ch2_id,
                "stages": ["write", "judge"],
            }
        )
        job_null_entity_id = create_synthetic_task(
            {
                "objective": "无目标新章细纲：推演第四章北境关隘封锁",
                "scheme": "P1",
                "mode": "create",
                "kind": "chapter",
                "name": "第四章候选细纲",
                "entity_id": None,
                "stages": ["plan"],
            }
        )

        _seed_job_state(
            runtime.connection,
            job_failed_id,
            "failed",
            {"error": {"detail": "合成模型网关连接超时（R09任务中心精准定位验证）"}},
            {"stage": "write"},
        )
        _seed_job_state(
            runtime.connection,
            job_ch1_id,
            "waiting",
            {
                "selected": 0,
                "candidates": [
                    {
                        "artifact": "draft",
                        "scheme": "P1",
                        "text": "【甲章候选结果】北风卷起渡口残雪，沈砚按住刀柄踏上浮桥。",
                        "evaluation": {
                            "score": 4.0,
                            "verdict": "review",
                            "report": {"hard": "pass", "dimensions": {}, "suggestions": ["可再压紧第一句呼吸感"]},
                        },
                    }
                ],
            },
            {"stage": "judge", "revisions": 1, "tokens": 1820, "usage_kind": "conservative_estimate"},
        )
        _seed_job_state(
            runtime.connection,
            job_ch2_first_id,
            "waiting",
            {
                "selected": 1,
                "candidates": [
                    {
                        "artifact": "draft",
                        "scheme": "P1",
                        "text": "【乙章任务一·第1版候选】黑影破窗而入，茶碗碎裂声惊起寒鸦。",
                        "evaluation": {
                            "score": 3.5,
                            "verdict": "review",
                            "report": {"hard": "pass", "dimensions": {}, "suggestions": ["补足铁牌遮挡细节"]},
                        },
                    },
                    {
                        "artifact": "draft",
                        "scheme": "P1",
                        "text": "【乙章任务一·第2版候选】刀光劈开竹帘，沈砚以旧铁牌格住淬毒短刃。",
                        "evaluation": {
                            "score": 4.5,
                            "verdict": "qualified",
                            "report": {"hard": "pass", "dimensions": {}, "suggestions": []},
                        },
                    },
                ],
            },
            {"stage": "judge", "revisions": 1, "tokens": 2640, "usage_kind": "conservative_estimate"},
        )
        _seed_job_state(
            runtime.connection,
            job_ch2_second_id,
            "qualified",
            {
                "selected": 0,
                "candidates": [
                    {
                        "artifact": "draft",
                        "scheme": "P1",
                        "text": "【乙章任务二·文戏候选】油灯映出铁牌背面半枚残缺印记，掌柜神色骤变。",
                        "evaluation": {
                            "score": 4.8,
                            "verdict": "qualified",
                            "report": {"hard": "pass", "dimensions": {}, "suggestions": []},
                        },
                    }
                ],
            },
            {"stage": "judge", "revisions": 0, "tokens": 1950, "usage_kind": "conservative_estimate"},
        )

        _seed_job_state(
            runtime.connection,
            job_null_entity_id,
            "waiting",
            {
                "selected": 0,
                "candidates": [
                    {
                        "artifact": "plan",
                        "scheme": "P1",
                        "text": "【无目标新章细纲候选】起：封关盘查；承：伪造路引；转：识破印信；钩：守将竟是旧识。",
                        "evaluation": {
                            "score": 4.3,
                            "verdict": "qualified",
                            "report": {"hard": "pass", "dimensions": {}, "suggestions": []},
                        },
                    }
                ],
            },
            {"stage": "plan", "revisions": 0, "tokens": 980, "usage_kind": "conservative_estimate"},
        )

        # Open /inbox and verify each task navigates to its exact chapter, task & candidate, and returns cleanly!
        nav.get_by_role("button", name="我的待办", exact=True).click()
        expect(page.get_by_role("heading", name="我的待办")).to_be_visible()

        # (a) Chapter 1 task -> /work -> verify Chapter 1 + Task A1 + excerpt -> Return to /inbox
        row_ch1 = page.locator("article.todo-row").filter(has_text="甲章任务：补强寒鸦渡风雪开篇压迫感")
        expect(row_ch1).to_be_visible()
        row_ch1.get_by_role("link", name="到创作台查看").click()
        expect(page.get_by_label("稿件名称", exact=True)).to_have_value("第一章 · 寒鸦渡")
        verdict_box = page.get_by_role("region", name="这一版留不留")
        expect(verdict_box).to_contain_text("甲章任务：补强寒鸦渡风雪开篇压迫感")
        expect(verdict_box).to_contain_text("【甲章候选结果】北风卷起渡口残雪")
        page.get_by_role("button", name="返回我的待办").first.click()
        expect(page.get_by_role("heading", name="我的待办")).to_be_visible()

        # (b) Chapter 2 Task 1 (same-chapter task #1, with 2 candidates) -> /work -> verify Chapter 2 + Task B1 + candidate switch -> Return to /inbox
        row_ch2_t1 = page.locator("article.todo-row").filter(has_text="乙章同章任务一：突出茶寮刺客夜袭动作节拍")
        row_ch2_t1.get_by_role("link", name="到创作台查看").click()
        expect(page.get_by_label("稿件名称", exact=True)).to_have_value("第二章 · 旧铁牌")
        verdict_box = page.get_by_role("region", name="这一版留不留")
        expect(verdict_box).to_contain_text("乙章同章任务一：突出茶寮刺客夜袭动作节拍")
        expect(verdict_box).to_contain_text("第 2 / 2 版")
        expect(verdict_box).to_contain_text("【乙章任务一·第2版候选】刀光劈开竹帘")
        verdict_box.get_by_role("button", name="上一候选", exact=True).click()
        expect(verdict_box).to_contain_text("第 1 / 2 版")
        expect(verdict_box).to_contain_text("【乙章任务一·第1版候选】黑影破窗而入")
        expect(verdict_box.get_by_role("group", name="同章候选任务")).to_be_visible()
        page.screenshot(path=str(args.output / "r09-same-chapter-task1.png"), full_page=True)
        page.get_by_role("button", name="返回我的待办").first.click()
        expect(page.get_by_role("heading", name="我的待办")).to_be_visible()

        # (c) Chapter 2 Task 2 (same-chapter task #2!) -> /work -> verify Chapter 2 + Task B2 (NOT Task B1!) -> Return to /inbox
        row_ch2_t2 = page.locator("article.todo-row").filter(has_text="乙章同章任务二：突出铁牌师门暗记文戏推理")
        row_ch2_t2.get_by_role("link", name="到创作台查看").click()
        expect(page.get_by_label("稿件名称", exact=True)).to_have_value("第二章 · 旧铁牌")
        verdict_box = page.get_by_role("region", name="这一版留不留")
        expect(verdict_box).to_contain_text("乙章同章任务二：突出铁牌师门暗记文戏推理")
        expect(verdict_box).to_contain_text("【乙章任务二·文戏候选】油灯映出铁牌背面半枚残缺印记")
        page.screenshot(path=str(args.output / "r09-same-chapter-task2.png"), full_page=True)
        page.get_by_role("button", name="返回我的待办").first.click()
        expect(page.get_by_role("heading", name="我的待办")).to_be_visible()

        # (d) Null-entity (entity_id=None) task -> /work -> verify new-draft mode STILL selects the exact task & shows plan candidate -> Return to /inbox
        row_null_entity = page.locator("article.todo-row").filter(has_text="无目标新章细纲：推演第四章北境关隘封锁")
        row_null_entity.get_by_role("link", name="到创作台查看").click()
        expect(page.locator(".writing-card")).to_contain_text("新稿")
        verdict_box = page.get_by_role("region", name="这一版留不留")
        expect(verdict_box).to_contain_text("无目标新章细纲：推演第四章北境关隘封锁")
        expect(verdict_box).to_contain_text("【无目标新章细纲候选】起：封关盘查")
        page.get_by_role("button", name="返回我的待办").first.click()
        expect(page.get_by_role("heading", name="我的待办")).to_be_visible()

        # (e) Failed task -> /admin/jobs -> verify exact failed job row is selected (not rows[0]) and detail matches; also verify /admin/jobs -> /work -> Return to /admin/jobs -> Return to /inbox
        row_failed = page.locator("article.todo-row").filter(has_text="失败对照：测试模型网关超时定位")
        row_failed.get_by_role("link", name="到任务中心查看").click()
        expect(page.get_by_role("heading", name="任务中心")).to_be_visible()
        selected_tr = page.locator("table.plain-table tbody tr[aria-current='true']")
        expect(selected_tr).to_contain_text("第三章 · 夜渡芦苇")
        detail_fields = page.locator("[data-component='labeled-fields']")
        expect(detail_fields).to_contain_text("失败对照：测试模型网关超时定位")
        expect(detail_fields).to_contain_text("合成模型网关连接超时（R09任务中心精准定位验证）")
        page.screenshot(path=str(args.output / "r09-failed-job-detail.png"), full_page=True)
        # Jump from JobsPage detail to /work and return back to JobsPage with same job selected
        page.locator(".job-split").get_by_role("link", name="到创作台查看").last.click()
        expect(page.get_by_label("稿件名称", exact=True)).to_have_value("第三章 · 夜渡芦苇")
        expect(page.get_by_role("region", name="这一版留不留")).to_contain_text("失败对照：测试模型网关超时定位")
        page.get_by_role("button", name="返回任务中心").first.click()
        expect(page.get_by_role("heading", name="任务中心")).to_be_visible()
        expect(page.locator("table.plain-table tbody tr[aria-current='true']")).to_contain_text("第三章 · 夜渡芦苇")
        nav.get_by_role("button", name="我的待办", exact=True).click()
        expect(page.get_by_role("heading", name="我的待办")).to_be_visible()

        # 8. /materials, /commons, /market & responsive checks
        nav.get_by_role("button", name="作品资料", exact=True).click()
        capsules = page.get_by_role("group", name="万象设定领域")
        expect(capsules.get_by_role("button", name=re.compile("种族与异界生物"))).to_be_visible()

        nav.get_by_role("button", name="公共陈列库", exact=True).click()
        page.get_by_role("button", name="克隆到当前书").first.click()
        expect(page.get_by_text("已克隆到当前书")).to_be_visible()

        nav.get_by_role("button", name="市场与风向", exact=True).click()
        health = page.get_by_role("region", name="连载健康度")
        expect(health).to_contain_text("总章数")
        expect(health).to_contain_text("超期伏笔")

        nav.get_by_role("button", name="创作台", exact=True).click()
        for width, height in ((1280, 900), (768, 1024), (390, 844)):
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(200)
            scroll_width = page.evaluate("document.documentElement.scrollWidth")
            assert scroll_width <= width + 2, f"Viewport {width} overflowed: {scroll_width}"
        page.set_viewport_size({"width": 1440, "height": 1000})

        # 9. R11 acceptance: Blueprint draft bound to login session; destroyed on permission change & on logout!
        user_client.post(
            f"/api/v1/scopes/{sid}/members",
            headers=u_headers,
            json={"user_id": collab_user["id"], "actions": ["read", "edit", "adopt"]},
        ).raise_for_status()

        # Logout owner -> Login collaborator in the SAME page (same JS heap!)
        page.locator("header.topbar").get_by_role("button", name="退出").click()
        expect(page.get_by_label("账号", exact=True)).to_be_visible()
        page.get_by_label("账号", exact=True).fill(collab_username)
        page.get_by_label("密码", exact=True).fill(collab_password)
        page.get_by_role("button", name=re.compile(r"登\s*录")).click()

        nav = page.get_by_role("navigation", name="创作后台导航")
        nav.get_by_role("button", name="大纲与暗线", exact=True).click()
        expect(page.get_by_role("heading", name="北境长歌总纲")).to_be_visible()
        page.get_by_label("总纲细纲", exact=True).fill("R11权限变更前草稿：仅协作者编辑态暂存。")
        expect(page.locator(".blueprint-page")).to_contain_text("当前有未保存的大纲或细纲草稿")

        # Revoke edit permission -> SSE permissions reset destroys scope draft
        user_client.post(
            f"/api/v1/scopes/{sid}/members",
            headers=u_headers,
            json={"user_id": collab_user["id"], "actions": ["read"]},
        ).raise_for_status()
        expect(page.locator(".blueprint-page")).to_contain_text("当前范围不能编辑", timeout=15000)
        expect(page.get_by_label("总纲细纲", exact=True)).to_have_value("窗口一草稿：第三卷封狼居胥，揭开北境铁牌真相。")

        # Re-grant edit permission, create a new unsaved draft, then Logout -> Login owner in SAME tab -> verify draft is destroyed!
        user_client.post(
            f"/api/v1/scopes/{sid}/members",
            headers=u_headers,
            json={"user_id": collab_user["id"], "actions": ["read", "edit", "adopt"]},
        ).raise_for_status()
        expect(page.locator(".blueprint-page")).not_to_contain_text("当前范围不能编辑", timeout=15000)
        page.get_by_label("总纲细纲", exact=True).fill("R11注销前私有草稿：退出登录后绝不能残留。")
        expect(page.locator(".blueprint-page")).to_contain_text("当前有未保存的大纲或细纲草稿")

        page.locator("header.topbar").get_by_role("button", name="退出").click()
        expect(page.get_by_label("账号", exact=True)).to_be_visible()
        page.get_by_label("账号", exact=True).fill(username)
        page.get_by_label("密码", exact=True).fill(password)
        page.get_by_role("button", name=re.compile(r"登\s*录")).click()
        nav = page.get_by_role("navigation", name="创作后台导航")
        nav.get_by_role("button", name="大纲与暗线", exact=True).click()
        expect(page.get_by_role("heading", name="北境长歌总纲")).to_be_visible()
        expect(page.locator(".blueprint-page")).not_to_contain_text("当前有未保存的大纲或细纲草稿")
        expect(page.get_by_label("总纲细纲", exact=True)).to_have_value("窗口一草稿：第三卷封狼居胥，揭开北境铁牌真相。")
        expect(page.locator("body")).not_to_contain_text("R11注销前私有草稿")

        # R11 Counterexample B: SAME principal logs out and logs back in (new session) -> prior session draft also destroyed!
        page.get_by_label("总纲细纲", exact=True).fill("R11同账号旧会话草稿：重登新会话后同样销毁。")
        expect(page.locator(".blueprint-page")).to_contain_text("当前有未保存的大纲或细纲草稿")
        page.locator("header.topbar").get_by_role("button", name="退出").click()
        expect(page.get_by_label("账号", exact=True)).to_be_visible()
        page.get_by_label("账号", exact=True).fill(username)
        page.get_by_label("密码", exact=True).fill(password)
        page.get_by_role("button", name=re.compile(r"登\s*录")).click()
        nav = page.get_by_role("navigation", name="创作后台导航")
        nav.get_by_role("button", name="大纲与暗线", exact=True).click()
        expect(page.get_by_role("heading", name="北境长歌总纲")).to_be_visible()
        expect(page.locator(".blueprint-page")).not_to_contain_text("当前有未保存的大纲或细纲草稿")
        expect(page.get_by_label("总纲细纲", exact=True)).to_have_value("窗口一草稿：第三卷封狼居胥，揭开北境铁牌真相。")
        expect(page.locator("body")).not_to_contain_text("R11同账号旧会话草稿")
        page.screenshot(path=str(args.output / "r11-session-isolation.png"), full_page=True)

        user_client.close()

        # Verify pre-existing scopes and revisions in shared ncc-dev were completely untouched
        post_scope_ids = {
            r[0] for r in runtime.connection.execute("SELECT id FROM ncc_scope").fetchall()
        }
        assert pre_scope_ids <= post_scope_ids, "原有范围丢失"
        post_rev_digest = runtime.connection.execute(
            "SELECT count(*), coalesce( max(version), 0 ) FROM ncc_revision WHERE scope_id = ANY(%s)",
            (list(pre_scope_ids),),
        ).fetchone()
        assert post_rev_digest == pre_rev_Digest, (pre_rev_Digest, post_rev_digest)

        assert not errors, errors
        result = {
            "browser": "Chromium",
            "synthetic_only": True,
            "page_errors": errors,
            "pre_existing_scopes_preserved": True,
            "checks": [
                "R01 ordinary non-admin author studio overview 200 & 6-space navigation",
                "R02 Han char count consistency ('二〇二六。' == 4 on editor & overview)",
                "U01 full-field auto-draft (metadata-only, clear-text-only, combined, accurate status, reload & leave recovery)",
                "U02 new-chapter & chapter-switch shared leave guard + isolated draft keys & save targets (read-back verified)",
                "U03 blueprint slice draft retention, shell leave guard, frozen baseline & concurrent conflict dual-version recovery",
                "creative page chapter concurrent conflict dual-version alert & rebase save",
                "R09 inbox -> /work & /admin/jobs exact chapter/task/candidate targeting, same-chapter dual tasks, candidate switch & return",
                "R11 blueprint in-memory draft bound to login session & destroyed on permission revocation and logout",
                "responsive viewports 1440/1280/768/390",
            ],
        }
        (args.output / "studio-result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        )
        browser.close()
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
