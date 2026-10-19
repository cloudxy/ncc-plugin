"""Local synthetic browser acceptance; never loads or uploads a real novel."""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8787")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert urlsplit(args.url).hostname in {"localhost", "127.0.0.1"}
    args.output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        browser = p.chromium.launch(headless=True, executable_path=str(chrome) if chrome.exists() else None)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page = context.new_page()
        page.set_default_timeout(10000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url + "/work")
        page.get_by_label("账号", exact=True).fill("browser-author")
        page.get_by_label("密码", exact=True).fill("synthetic-browser-password")
        page.get_by_role("button", name=re.compile(r"登\s*录"), exact=True).click()
        page.get_by_role("button", name="新建作品或资料库").click()
        page.get_by_label("名称", exact=True).fill("合成验收空间")
        page.get_by_role("button", name="确 定", exact=True).click()
        expect(page.get_by_role("dialog")).not_to_be_visible()
        expect(page.get_by_placeholder("给这一章或这份内容起个名字")).to_be_visible()
        page.get_by_placeholder("给这一章或这份内容起个名字").fill("渡河 · 合成样例")
        page.locator(".writing-card .cm-content").fill(
            "雨落在渡口。少年放下剑，先去救人。\n\n这是一段用于软件验收的合成文本。"
        )
        expect(page.get_by_text("草稿已自动保存", exact=False)).to_be_visible(timeout=10000)
        sidebar = page.locator(".sidebar")
        assert sidebar.bounding_box()["width"] >= 220, sidebar.evaluate(
            "el => ({inline:el.getAttribute('style'), width:getComputedStyle(el).width, flex:getComputedStyle(el).flex, viewport:innerWidth})"
        )
        page.screenshot(path=str(args.output / "desktop-viewport.png"))
        (args.output / "layout.json").write_text(
            json.dumps(
                page.evaluate(
                    """() => Object.fromEntries(['.app-layout','.sidebar','.brand','.topbar','.content'].map(s=>{const e=document.querySelector(s),r=e.getBoundingClientRect();return [s,{x:r.x,width:r.width,flex:getComputedStyle(e).flex}]}))"""
                ),
                indent=2,
            )
        )
        page.screenshot(path=str(args.output / "before-save.png"), full_page=True)
        page.get_by_role("button", name="保存修订").click()
        expect(page.get_by_text("新修订已保存；旧评分将重新检查有效性")).to_be_visible()
        page.screenshot(path=str(args.output / "creative.png"), full_page=True)
        page.get_by_text("作品资料", exact=True).click()
        expect(page.get_by_role("cell", name="渡河 · 合成样例", exact=True)).to_be_visible()
        page.get_by_role("cell", name="渡河 · 合成样例", exact=True).click()
        expect(page.get_by_role("tab", name="修订历史")).to_be_visible()
        page.get_by_role("tab", name="修订历史").click()
        expect(page.get_by_role("button", name="打开此修订")).to_be_visible()
        page.get_by_role("button", name="打开此修订").click()
        expect(page.get_by_text("历史修订（只读）")).to_be_visible()
        page.screenshot(path=str(args.output / "history.png"), full_page=True)
        page.locator(".ant-modal-close").click()
        expect(page.get_by_text("历史修订（只读）")).not_to_be_visible()
        page.locator(".ant-drawer-close").click()
        expect(page.get_by_role("tab", name="修订历史")).not_to_be_visible()
        page.get_by_text("高级管理", exact=True).click()
        page.get_by_text("定义中心", exact=True).click()
        expect(page.get_by_role("heading", name="定义中心")).to_be_visible()
        page.screenshot(path=str(args.output / "definitions.png"), full_page=True)
        page.get_by_text("任务中心", exact=True).click()
        expect(page.get_by_role("heading", name="任务中心")).to_be_visible()
        page.get_by_text("成员与设置", exact=True).click()
        expect(page.get_by_text("自动定稿授权", exact=True)).to_be_visible()
        page.get_by_text("创作台", exact=True).click()
        expect(page.locator(".writing-card .cm-content")).to_have_text("")
        page.get_by_label("编辑对象", exact=True).click()
        page.get_by_text("渡河 · 合成样例", exact=True).last.click()
        expect(page.locator(".writing-card .cm-content")).to_contain_text("雨落在渡口")
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_function("document.querySelector('.sidebar').getBoundingClientRect().width <= 65")
        expect(page.locator(".writing-card .cm-content")).to_be_visible()
        page.wait_for_timeout(300)
        assert page.evaluate("document.documentElement.scrollWidth") <= 392, (
            "Mobile layout overflows horizontally"
        )
        page.screenshot(path=str(args.output / "mobile.png"), full_page=True)
        assert not errors, errors
        result = {
            "browser": "Chromium",
            "synthetic_only": True,
            "page_errors": errors,
            "checks": [
                "login",
                "scope creation",
                "server draft autosave",
                "adopt author edit",
                "materials",
                "read historical revision",
                "definitions",
                "jobs",
                "mobile rendering",
            ],
        }
        (args.output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        browser.close()
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
