"""Permanent Playwright Chromium acceptance suite for Batch 1-3 console upgrade capabilities."""

import argparse
import asyncio
import io
import json
import re
import sys as _sys
import threading
import time
import zipfile
from pathlib import Path as _Path
from uuid import uuid4

import httpx

_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from support.browser import browser_test  # noqa: E402

from ncc_data.creation.worker import Worker  # noqa: E402
from ncc_data.persistence.database import database  # noqa: E402

_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)
_SAMPLE_SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script><rect width="10" height="10"/></svg>'


class _ScopedWorkerThread:
    def __init__(self, settings, scope_ids: set[str]):
        self.settings = settings
        self.scope_ids = set(scope_ids)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=10)

    def _run(self) -> None:
        asyncio.run(self._loop())

    async def _loop(self) -> None:
        engine, factory = database(self.settings.database_url)
        try:
            worker = Worker(factory, self.settings, scope_ids=self.scope_ids)
            await worker.record_heartbeat()
            while not self._stop.is_set():
                worked = await worker.run_once()
                if not worked:
                    await asyncio.sleep(0.15)
        finally:
            await engine.dispose()


def _launch_browser(playwright_instance):
    try:
        return playwright_instance.chromium.launch(headless=True, channel="chrome")
    except Exception:
        return playwright_instance.chromium.launch(headless=True)


def _check_viewport_metrics(page) -> dict:
    return page.evaluate(
        """() => {
            const docWidth = document.documentElement.scrollWidth;
            const winWidth = window.innerWidth;
            const overflowPx = Math.max(0, docWidth - winWidth);
            const tooSmall = [];
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            let node;
            while ((node = walker.nextNode())) {
                const txt = (node.nodeValue || "").trim();
                if (!txt) continue;
                const el = node.parentElement;
                if (!el) continue;
                if (el.closest("svg, .ant-select-selection-search, [aria-hidden='true']")) continue;
                const style = window.getComputedStyle(el);
                if (
                    style.display === "none" ||
                    style.visibility === "hidden" ||
                    parseFloat(style.opacity || "1") === 0
                ) {
                    continue;
                }
                const rect = el.getBoundingClientRect();
                if (rect.width < 2 || rect.height < 2) continue;
                const fontSize = parseFloat(style.fontSize || "14");
                if (fontSize < 11.95) {
                    tooSmall.push({
                        tag: el.tagName,
                        className: String(el.className || "").slice(0, 60),
                        fontSize,
                        sample: txt.slice(0, 24),
                    });
                }
            }
            return {
                docWidth,
                winWidth,
                overflowPx,
                smallFontCount: tooSmall.length,
                smallFontSamples: tooSmall.slice(0, 5),
            };
        }"""
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/tmp/ncc-upgrade-browser")
    args, _ = parser.parse_known_args()
    return args


@browser_test
def main(runtime):
    args = _parse_args()
    out_dir = _Path(args.output).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    origin = runtime.origin
    reset_user, init_pw = runtime.new_credentials("test-reset")
    _, temp_pw = runtime.new_credentials("test-temp-unused")
    _, updated_pw = runtime.new_credentials("test-updated-unused")
    ui_new_user, ui_new_pw = runtime.new_credentials("test-ui-member")
    tag = uuid4().hex[:8]
    synthetic_model_name = f"升级回归CLI路由-{tag}"
    created_model_ids: set[str] = set()
    page_errors: list[str] = []
    inline_basemap_headers: dict[str, str] = {}
    worker_runner: _ScopedWorkerThread | None = None

    with httpx.Client(
        base_url=origin,
        timeout=30,
        limits=httpx.Limits(max_keepalive_connections=0),
    ) as admin_http:
        me = (
            admin_http.post(
                "/api/v1/auth/login",
                headers={"x-ncc-client": "console"},
                json={"username": runtime.username, "password": runtime.password},
            )
            .raise_for_status()
            .json()
        )
        csrf = {"x-csrf-token": me["csrf"]}
        pre_models = admin_http.get("/api/v1/model-settings").raise_for_status().json()
        pre_model_ids = {c["id"] for c in (pre_models.get("configurations") or [])}

        try:
            # Prepare synthetic scope + non-admin reset-password user + chapters + location
            created_reset = (
                admin_http.post(
                    "/api/v1/users",
                    headers=csrf,
                    json={"username": reset_user, "password": init_pw},
                )
                .raise_for_status()
                .json()
            )
            admin_http.patch(
                f"/api/v1/users/{created_reset['id']}",
                headers=csrf,
                json={"reset_password": temp_pw},
            ).raise_for_status()

            main_scope = (
                admin_http.post(
                    "/api/v1/scopes",
                    headers=csrf,
                    json={"name": f"升级验收主书-{tag}"},
                )
                .raise_for_status()
                .json()
            )
            sid = main_scope["id"]
            empty_scope = (
                admin_http.post(
                    "/api/v1/scopes",
                    headers=csrf,
                    json={"name": f"待删空空间-{tag}"},
                )
                .raise_for_status()
                .json()
            )
            empty_sid = empty_scope["id"]

            admin_http.post(
                f"/api/v1/scopes/{sid}/members",
                headers=csrf,
                json={"username": reset_user, "actions": ["read", "edit"]},
            ).raise_for_status()

            vol_id = str(uuid4())
            admin_http.post(
                f"/api/v1/scopes/{sid}/changes/commit",
                headers={**csrf, "idempotency-key": f"b4-up-seed-{tag}"},
                json={
                    "title": "准备升级浏览器验收合成数据",
                    "base_version": 0,
                    "operations": [
                        {
                            "op": "create",
                            "entity_id": vol_id,
                            "kind": "volume",
                            "name": "第一卷·夜雨长安",
                            "data": {"position": 0},
                        },
                        {
                            "op": "create",
                            "kind": "chapter",
                            "name": "第1章 风起朱雀街",
                            "text": "rev1: 内部审校批注不应导出\n---\n雨落长安石板路。\n少年撑伞走过坊门。",
                            "data": {"position": 0, "parent_id": vol_id, "status": "done"},
                        },
                        {
                            "op": "create",
                            "kind": "chapter",
                            "name": "第2章 灯下故人来",
                            "text": "茶肆孤灯微明，故人推门而入。",
                            "data": {"position": 1, "parent_id": vol_id, "status": "done"},
                        },
                        {
                            "op": "create",
                            "kind": "chapter",
                            "name": "绝密暗线章",
                            "secret": True,
                            "text": "SECRET-MANUSCRIPT-DO-NOT-LEAK",
                            "data": {"position": 2, "parent_id": vol_id, "status": "done"},
                        },
                        {
                            "op": "create",
                            "kind": "location",
                            "name": "朱雀门钟楼",
                            "text": "俯瞰长街的制高点",
                            "data": {
                                "coordinate": {"frame": "长安城平面图", "x": "180", "y": "260"}
                            },
                        },
                    ],
                },
            ).raise_for_status()

            worker_runner = _ScopedWorkerThread(runtime.settings, {sid})
            worker_runner.start()

            with sync_playwright() as p:
                browser = _launch_browser(p)
                try:
                    # =====================================================================
                    # 1. Non-admin temporary password reset reminder & prefilled modal flow
                    # =====================================================================
                    ctx_reset = browser.new_context(viewport={"width": 1440, "height": 900})
                    try:
                        page_reset = ctx_reset.new_page()
                        page_reset.set_default_timeout(15000)
                        page_reset.on("pageerror", lambda e: page_errors.append(str(e)))

                        page_reset.goto(origin + "/work")
                        page_reset.get_by_label("账号", exact=True).fill(reset_user)
                        page_reset.get_by_label("密码", exact=True).fill(temp_pw)
                        page_reset.get_by_role("button", name=re.compile(r"登\s*录")).click()

                        expect(
                            page_reset.get_by_text(f"当前账号（{reset_user}）使用的是初始或已重置临时密码")
                        ).to_be_visible(timeout=15000)
                        page_reset.get_by_role("button", name="立即修改账号密码").click()

                        expect(
                            page_reset.get_by_text(f"请修改临时密码（{reset_user}）")
                        ).to_be_visible()
                        username_input = page_reset.locator("#credentialChangeForm_new_username")
                        expect(username_input).to_have_value(reset_user)

                        page_reset.locator("#credentialChangeForm_current_password").fill(temp_pw)
                        page_reset.locator("#credentialChangeForm_new_password").fill(updated_pw)
                        page_reset.locator("#credentialChangeForm_confirm_password").fill(updated_pw)
                        page_reset.get_by_role("button", name="确认修改").click()

                        expect(page_reset.locator("body")).not_to_contain_text(
                            "使用的是初始或已重置临时密码", timeout=15000
                        )
                        page_reset.screenshot(path=str(out_dir / "01-password-reset-updated.png"))
                    finally:
                        ctx_reset.close()

                    # =====================================================================
                    # Admin main context (Flows 2, 3, 4, 5, 6)
                    # =====================================================================
                    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
                    try:
                        page = ctx.new_page()
                        page.set_default_timeout(15000)
                        page.on("pageerror", lambda e: page_errors.append(str(e)))

                        def _capture_inline(resp):
                            if "/attachments/" in resp.url and "inline=true" in resp.url:
                                inline_basemap_headers["status"] = str(resp.status)
                                inline_basemap_headers["content_type"] = resp.headers.get(
                                    "content-type", ""
                                )
                                inline_basemap_headers["nosniff"] = resp.headers.get(
                                    "x-content-type-options", ""
                                )

                        page.on("response", _capture_inline)

                        page.goto(origin + "/work")
                        page.get_by_label("账号", exact=True).fill(runtime.username)
                        page.get_by_label("密码", exact=True).fill(runtime.password)
                        page.get_by_role("button", name=re.compile(r"登\s*录")).click()
                        expect(page.locator(".topbar")).to_be_visible(timeout=15000)

                        def _select_scope_by_name(scope_label: str) -> None:
                            scope_sel = page.locator(".scope-select")
                            if scope_label in (scope_sel.inner_text() or ""):
                                return
                            scope_sel.click()
                            page.locator(".ant-select-item-option").filter(
                                has_text=scope_label
                            ).first.click()
                            expect(scope_sel).to_contain_text(scope_label, timeout=10000)

                        _select_scope_by_name(main_scope["name"])

                        # =====================================================================
                        # 2. /admin/models HTTP <-> CLI OAuth toggle + Subscription tab bind
                        # =====================================================================
                        page.goto(origin + "/admin/models")
                        expect(page.locator("[data-component='model-settings']")).to_be_visible()
                        expect(page.get_by_label("网关地址")).to_be_visible()

                        page.locator(".ant-segmented").get_by_text(
                            "本机 CLI OAuth 订阅", exact=True
                        ).click()
                        expect(page.get_by_label("网关地址")).to_have_count(0)
                        expect(page.get_by_text("CLI 订阅通道")).to_be_visible()

                        page.locator(".ant-segmented").get_by_text(
                            "兼容 HTTP 接口（API Key）", exact=True
                        ).click()
                        expect(page.get_by_label("网关地址")).to_be_visible()

                        page.get_by_role("tab", name="本机 CLI OAuth 订阅").click()
                        expect(page.locator("[data-component='subscription-auth']")).to_be_visible()
                        page.get_by_role("button", name="绑定为写作/审评模型").first.click()

                        # Returned to "模型与连接" tab with CLI OAuth fields populated
                        expect(page.get_by_text("CLI 订阅通道")).to_be_visible()
                        name_input = page.get_by_label("配置名称")
                        assert "CLI OAuth" in name_input.input_value()
                        name_input.fill(synthetic_model_name)
                        # Keep disabled so global active defaults for other scopes are untouched
                        switch_btn = page.get_by_role("switch")
                        if switch_btn.get_attribute("aria-checked") == "true":
                            switch_btn.click()
                        page.get_by_role("button", name="保存配置").click()
                        expect(page.locator(".model-list")).to_contain_text(synthetic_model_name)

                        after_models = (
                            admin_http.get("/api/v1/model-settings").raise_for_status().json()
                        )
                        for cfg in after_models.get("configurations") or []:
                            if (
                                cfg["id"] not in pre_model_ids
                                and cfg.get("name") == synthetic_model_name
                            ):
                                created_model_ids.add(cfg["id"])
                        page.screenshot(path=str(out_dir / "02-models-oauth-bound.png"))

                        # =====================================================================
                        # 3. /work & /admin/exchange manuscript exports (EPUB / TXT / MD)
                        # =====================================================================
                        page.goto(origin + "/work")
                        _select_scope_by_name(main_scope["name"])
                        page.get_by_role("button", name="导出成稿").click()
                        export_modal = page.locator(".ant-modal").filter(has_text="导出作品成稿")
                        expect(export_modal).to_be_visible()
                        export_modal.get_by_role("button", name="立即生成成稿").click()
                        expect(
                            export_modal.get_by_role("button", name=re.compile(r"下载\s+"))
                        ).to_be_visible(timeout=15000)
                        export_modal.get_by_role("button", name="关闭").click()

                        page.goto(origin + "/admin/exchange")
                        expect(page.get_by_text("作品成稿导出")).to_be_visible()
                        for fmt_option in ("纯净排版 TXT（首行缩进）", "合稿 Markdown（.md）"):
                            page.locator(
                                "[aria-label='成稿格式'], .ant-select:has([aria-label='成稿格式'])"
                            ).first.click()
                            page.locator(".ant-select-item-option").filter(
                                has_text=fmt_option
                            ).first.click()
                            page.get_by_role("button", name="导出作品成稿").click()
                            page.wait_for_timeout(200)

                        # Poll export jobs via API and verify EPUB / TXT / MD bytes & zero secret leakage
                        deadline = time.monotonic() + 20
                        export_by_fmt: dict[str, dict] = {}
                        while time.monotonic() < deadline:
                            jobs_list = (
                                admin_http.get(
                                    f"/api/v1/scopes/{sid}/jobs",
                                    params={"kind": "export", "summary": "true"},
                                )
                                .raise_for_status()
                                .json()
                            )
                            for j in jobs_list:
                                fmt_k = (j.get("payload") or {}).get("format")
                                if j.get("state") == "succeeded" and fmt_k in {
                                    "epub",
                                    "txt",
                                    "manuscript_md",
                                }:
                                    export_by_fmt[fmt_k] = j
                            if {"epub", "txt", "manuscript_md"} <= set(export_by_fmt):
                                break
                            time.sleep(0.25)

                        assert {"epub", "txt", "manuscript_md"} <= set(export_by_fmt), export_by_fmt

                        txt_bytes = admin_http.get(
                            f"/api/v1/scopes/{sid}/attachments/{export_by_fmt['txt']['result']['id']}"
                        ).raise_for_status().content.decode("utf-8")
                        md_bytes = admin_http.get(
                            f"/api/v1/scopes/{sid}/attachments/{export_by_fmt['manuscript_md']['result']['id']}"
                        ).raise_for_status().content.decode("utf-8")
                        epub_raw = admin_http.get(
                            f"/api/v1/scopes/{sid}/attachments/{export_by_fmt['epub']['result']['id']}"
                        ).raise_for_status().content

                        for rendered in (txt_bytes, md_bytes):
                            assert "风起朱雀街" in rendered
                            assert "灯下故人来" in rendered
                            assert "内部审校批注不应导出" not in rendered
                            assert "SECRET-MANUSCRIPT-DO-NOT-LEAK" not in rendered
                            assert "绝密暗线章" not in rendered

                        with zipfile.ZipFile(io.BytesIO(epub_raw), "r") as zf:
                            names = zf.namelist()
                            assert names[0] == "mimetype"
                            epub_joined = "\n".join(
                                zf.read(n).decode("utf-8", errors="ignore") for n in names
                            )
                            assert "风起朱雀街" in epub_joined
                            assert "内部审校批注不应导出" not in epub_joined
                            assert "SECRET-MANUSCRIPT-DO-NOT-LEAK" not in epub_joined
                            assert "绝密暗线章" not in epub_joined
                        page.screenshot(path=str(out_dir / "03-exchange-manuscripts.png"))

                        # =====================================================================
                        # 4. /admin/settings zero-UUID user -> member -> token -> archive/restore -> delete v0
                        # =====================================================================
                        page.goto(origin + "/admin/settings")
                        expect(page.get_by_text("系统账号管理")).to_be_visible()

                        page.get_by_role("button", name="建立新账号").click()
                        user_modal = page.locator(".ant-modal").filter(has_text="建立本机账号")
                        expect(user_modal).to_be_visible()
                        page.locator("#userForm_username").fill(ui_new_user)
                        page.locator("#userForm_password").fill(ui_new_pw)
                        user_modal.locator(".ant-modal-footer .ant-btn-primary").click()
                        expect(user_modal).to_be_hidden(timeout=10000)

                        all_users = admin_http.get("/api/v1/users").raise_for_status().json()
                        assert any(u.get("username") == ui_new_user for u in all_users)

                        # Member form username was auto-populated without typing any UUID; grant read+edit
                        member_form = page.locator("form#memberForm")
                        expect(member_form).to_contain_text(ui_new_user, timeout=10000)
                        member_form.get_by_role("button", name="更新成员权限").click()
                        members_card = page.locator(".ant-card").filter(has_text="范围成员")
                        expect(members_card).to_contain_text(ui_new_user, timeout=10000)

                        # Issue & revoke scoped token
                        tokens_card = page.locator(".ant-card").filter(has_text="本范围自动化凭据")
                        tokens_card.get_by_role("button", name="生成范围凭据").click()
                        expect(tokens_card.get_by_role("button", name="吊销")).to_be_visible(
                            timeout=10000
                        )
                        tokens_card.get_by_role("button", name="吊销").first.click()
                        page.locator(".ant-popover:visible .ant-btn-primary").click()
                        expect(tokens_card).to_contain_text(
                            "当前没有已签发的活跃范围凭据", timeout=10000
                        )

                        # Archive & restore scope (row-targeted to avoid touching unrelated archived scopes)
                        scope_card = page.locator(".ant-card").filter(has_text="作品空间管理")
                        scope_card.get_by_role("button", name="归档当前空间").click()
                        page.locator(".ant-popover:visible .ant-btn-primary").click()
                        archived_row = (
                            page.locator(".ant-card")
                            .filter(has_text="作品空间管理")
                            .locator("tr")
                            .filter(has_text=main_scope["name"])
                        )
                        expect(archived_row).to_be_visible(timeout=10000)
                        archived_row.get_by_role("button", name="恢复使用").click()
                        expect(archived_row).to_have_count(0, timeout=10000)

                        # Switch to v0 empty_scope and delete it permanently
                        _select_scope_by_name(empty_scope["name"])
                        scope_card = page.locator(".ant-card").filter(has_text="作品空间管理")
                        expect(scope_card.get_by_role("button", name="删除空空间")).to_be_visible()
                        scope_card.get_by_role("button", name="删除空空间").click()
                        page.locator(".ant-popover:visible .ant-btn-primary").click()

                        # Verify empty_sid is gone from /scopes?include_archived=true
                        expect(page.locator(".scope-select")).not_to_contain_text(
                            empty_scope["name"], timeout=10000
                        )
                        remaining_ids = {
                            s["id"]
                            for s in admin_http.get(
                                "/api/v1/scopes", params={"include_archived": "true"}
                            )
                            .raise_for_status()
                            .json()
                        }
                        assert empty_sid not in remaining_ids
                        _select_scope_by_name(main_scope["name"])
                        page.screenshot(path=str(out_dir / "04-settings-governance.png"))

                        # =====================================================================
                        # 5. /admin/maps PNG inline basemap preview + SVG forced download check
                        # =====================================================================
                        page.goto(origin + "/admin/maps")
                        expect(page.get_by_text("朱雀门钟楼")).to_be_visible(timeout=15000)
                        png_path = out_dir / "synthetic-basemap.png"
                        png_path.write_bytes(_TINY_PNG)
                        page.locator(".map-filters input[type='file']").set_input_files(
                            str(png_path)
                        )

                        deadline = time.monotonic() + 10
                        while time.monotonic() < deadline and not inline_basemap_headers.get(
                            "status"
                        ):
                            page.wait_for_timeout(200)
                        assert inline_basemap_headers.get("status") == "200", inline_basemap_headers
                        assert inline_basemap_headers.get("content_type") == "image/png"
                        assert inline_basemap_headers.get("nosniff") == "nosniff"

                        # Upload SVG via API and verify ?inline=true still forces octet-stream attachment
                        svg_att = (
                            admin_http.post(
                                f"/api/v1/scopes/{sid}/attachments",
                                headers=csrf,
                                files={"file": ("hazard.svg", _SAMPLE_SVG, "image/svg+xml")},
                            )
                            .raise_for_status()
                            .json()
                        )
                        svg_resp = admin_http.get(
                            f"/api/v1/scopes/{sid}/attachments/{svg_att['id']}",
                            params={"inline": "true"},
                        )
                        assert svg_resp.status_code == 200
                        assert svg_resp.headers.get("content-type") == "application/octet-stream"
                        assert "attachment" in (svg_resp.headers.get("content-disposition") or "")
                        assert svg_resp.headers.get("x-content-type-options") == "nosniff"
                        page.screenshot(path=str(out_dir / "05-maps-safe-basemap.png"))

                        # =====================================================================
                        # 6. Multi-viewport computed style checks (1440x900, 768x1024, 375x812)
                        # =====================================================================
                        viewport_reports: dict[str, dict] = {}
                        for width, height in ((1440, 900), (768, 1024), (375, 812)):
                            vp_key = f"{width}x{height}"
                            page.set_viewport_size({"width": width, "height": height})
                            for route in (
                                "/work",
                                "/blueprint",
                                "/materials",
                                "/admin/models",
                                "/admin/settings",
                            ):
                                page.goto(origin + route)
                                expect(page.locator(".topbar")).to_be_visible(timeout=15000)
                                page.wait_for_timeout(400)
                                metrics = _check_viewport_metrics(page)
                                assert (
                                    metrics["overflowPx"] <= 1
                                ), f"{vp_key} {route} overflow: {metrics}"
                                assert (
                                    metrics["smallFontCount"] == 0
                                ), f"{vp_key} {route} <12px font: {metrics}"
                                viewport_reports[f"{vp_key}:{route}"] = metrics
                            page.screenshot(path=str(out_dir / f"06-viewport-{vp_key}.png"))

                        assert page_errors == [], page_errors
                    finally:
                        ctx.close()
                finally:
                    browser.close()

            report = {
                "synthetic_only": True,
                "checks": [
                    "non-admin reset password dynamic reminder and prefilled modal update",
                    "models HTTP <-> CLI OAuth form toggle and subscription one-click bind",
                    "work & exchange manuscript exports (EPUB/TXT/MD) with zero secret leakage",
                    "zero-UUID user creation, member select, token issue/revoke, scope archive/restore & v0 delete",
                    "maps PNG inline preview with nosniff and SVG forced octet-stream download",
                    "1440x900, 768x1024, 375x812 zero <12px font, zero horizontal overflow, zero page_errors",
                ],
                "inline_basemap": inline_basemap_headers,
                "viewports_checked": len(viewport_reports),
                "page_errors": page_errors,
            }
            (out_dir / "upgrade-report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print(json.dumps(report, ensure_ascii=False))
        finally:
            if worker_runner is not None:
                worker_runner.stop()
            for cfg_id in created_model_ids:
                try:
                    admin_http.delete(
                        f"/api/v1/model-settings/configurations/{cfg_id}",
                        headers={**csrf, "content-length": "0"},
                    )
                except Exception:
                    pass


if __name__ == "__main__":
    main()
