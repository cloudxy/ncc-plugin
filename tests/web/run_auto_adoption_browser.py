"""Real UI delegation -> creation payload wiring, synthetic local scope only."""

import json
import re
from uuid import uuid4

import httpx
from playwright.sync_api import expect, sync_playwright


def main():
    origin = "http://127.0.0.1:8787"
    scope_name = "自动定稿合成验收-" + uuid4().hex[:8]
    username = "auto-fixture-" + uuid4().hex[:8]
    password = "synthetic-auto-password"
    with httpx.Client(base_url=origin, timeout=30) as client:
        auth = (
            client.post(
                "/api/v1/auth/login",
                headers={"x-ncc-client": "console"},
                json={"username": "browser-author", "password": "synthetic-browser-password"},
            )
            .raise_for_status()
            .json()
        )
        headers = {"x-csrf-token": auth["csrf"]}
        client.post(
            "/api/v1/users", headers=headers, json={"username": username, "password": password}
        ).raise_for_status()
        auth = (
            client.post(
                "/api/v1/auth/login",
                headers={"x-ncc-client": "console"},
                json={"username": username, "password": password},
            )
            .raise_for_status()
            .json()
        )
        headers = {"x-csrf-token": auth["csrf"]}
        sid = (
            client.post("/api/v1/scopes", headers=headers, json={"name": scope_name})
            .raise_for_status()
            .json()["id"]
        )
        change = (
            client.post(
                f"/api/v1/scopes/{sid}/changes",
                headers=headers,
                json={
                    "title": "合成对象",
                    "base_version": 0,
                    "operations": [
                        {
                            "op": "create",
                            "kind": "chapter",
                            "name": "合成自动定稿第四章",
                            "data": {"position": 4},
                            "text": "灯下的选择。合成正文。",
                        }
                    ],
                },
            )
            .raise_for_status()
            .json()
        )
        client.post(
            f"/api/v1/scopes/{sid}/changes/{change['id']}/adopt",
            headers={**headers, "idempotency-key": str(uuid4())},
            json={},
        ).raise_for_status()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, channel="chrome")
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.set_default_timeout(15000)
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(origin + "/admin/settings")
            page.get_by_label("账号", exact=True).fill(username)
            page.get_by_label("密码", exact=True).fill(password)
            page.get_by_role("button", name=re.compile(r"登\s*录")).click()
            expect(page.get_by_text(scope_name, exact=True).first).to_be_visible()
            card = page.locator(".ant-card").filter(has=page.get_by_text("自动定稿授权", exact=True))
            expect(card.get_by_text("试运行不代表评分已校准", exact=True)).to_be_visible()
            card.get_by_label("授权依据").fill("作者通过合成浏览器验收启用本对象试运行。")
            card.get_by_label("查找引用对象").click()
            page.get_by_text("合成自动定稿第四章 · chapter", exact=True).last.click()
            page.keyboard.press("Escape")
            card.get_by_role("button", name="登记本次授权").click()
            expect(card.get_by_role("cell", name="作者试运行 · 未校准", exact=True)).to_be_visible()
            delegations = client.get(f"/api/v1/scopes/{sid}/delegations").raise_for_status().json()
            delegation = delegations[0]
            assert delegation["authorization"]["mode"] == "author_trial"
            page.get_by_text("创作台", exact=True).click()
            page.get_by_label("编辑对象", exact=True).click()
            page.get_by_text("合成自动定稿第四章", exact=True).last.click()
            expect(page.locator(".writing-card .cm-content")).to_contain_text("合成正文")
            page.get_by_label("成果采用方式").click()
            page.get_by_text(re.compile("自动定稿试运行 · 校准未验证 · 剩余3次")).last.click()
            page.get_by_label("创作目标").fill("用于验证授权接线的合成任务。")
            page.get_by_role("button", name=re.compile("开始处理")).click()
            expect(page.get_by_text("已进入自动创作流程", exact=True)).to_be_visible()
            jobs = client.get(f"/api/v1/scopes/{sid}/jobs").raise_for_status().json()
            job = next(j for j in jobs if j["kind"] == "creation")
            assert job["payload"]["delegation_id"] == delegation["id"]
            assert not errors, errors
            browser.close()
        print(
            json.dumps(
                {
                    "synthetic_only": True,
                    "checks": [
                        "owner trial registration in UI",
                        "unverified calibration label",
                        "target-scoped authorization selection",
                        "creation payload delegation binding",
                    ],
                    "page_errors": errors,
                    "live_model_tested": False,
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
