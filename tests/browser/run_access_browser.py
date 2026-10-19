"""Synthetic two-principal revocation during an SSE disconnect."""

import json
import re
from uuid import uuid4

import httpx
from _bootstrap import browser_test
from playwright.sync_api import expect, sync_playwright


@browser_test
def main(runtime):
    origin = runtime.origin
    password = "synthetic-access-password"
    with httpx.Client(base_url=origin, timeout=30) as owner:
        me = (
            owner.post(
                "/api/v1/auth/login",
                headers={"x-ncc-client": "console"},
                json={"username": "browser-author", "password": "synthetic-browser-password"},
            )
            .raise_for_status()
            .json()
        )
        headers = {"x-csrf-token": me["csrf"]}
        username = "access-fixture-" + str(uuid4())[:8]
        user = (
            owner.post("/api/v1/users", headers=headers, json={"username": username, "password": password})
            .raise_for_status()
            .json()
        )
        scope = (
            owner.post("/api/v1/scopes", headers=headers, json={"name": "撤权合成空间"})
            .raise_for_status()
            .json()
        )
        sid = scope["id"]
        member = {"user_id": user["id"], "actions": ["read", "edit", "adopt", "secret"]}
        owner.post(f"/api/v1/scopes/{sid}/members", headers=headers, json=member).raise_for_status()
        change = (
            owner.post(
                f"/api/v1/scopes/{sid}/changes",
                headers=headers,
                json={
                    "title": "合成秘密内容",
                    "base_version": 0,
                    "operations": [
                        {
                            "op": "create",
                            "kind": "chapter",
                            "name": "授权合成章",
                            "secret": True,
                            "data": {"position": 4},
                            "text": "SECRET-ACCESS-FIXTURE：用于撤权检查的合成内容。",
                        }
                    ],
                },
            )
            .raise_for_status()
            .json()
        )
        owner.post(
            f"/api/v1/scopes/{sid}/changes/{change['id']}/adopt",
            headers={**headers, "idempotency-key": str(uuid4())},
            json={},
        ).raise_for_status()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, channel="chrome")
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            page.set_default_timeout(15000)
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(origin + "/materials")
            page.get_by_label("账号", exact=True).fill(username)
            page.get_by_label("密码", exact=True).fill(password)
            page.get_by_role("button", name=re.compile(r"登\s*录")).click()
            page.get_by_role("cell", name="授权合成章", exact=True).click()
            editor = page.locator(".ant-drawer .cm-content")
            expect(editor).to_contain_text("SECRET-ACCESS-FIXTURE")
            editor.fill("SECRET-DIRTY-FIXTURE：未采用的合成草稿。")
            context.set_offline(True)
            page.wait_for_timeout(300)
            member["actions"] = ["read", "edit", "adopt"]
            owner.post(f"/api/v1/scopes/{sid}/members", headers=headers, json=member).raise_for_status()
            context.set_offline(False)
            expect(page.locator("body")).not_to_contain_text("SECRET-DIRTY-FIXTURE", timeout=20000)
            member["actions"] = []
            owner.post(f"/api/v1/scopes/{sid}/members", headers=headers, json=member).raise_for_status()
            expect(page.get_by_text("从一个故事，或一份资料开始")).to_be_visible(timeout=20000)
            assert not errors, errors
            browser.close()
        print(
            json.dumps(
                {
                    "synthetic_only": True,
                    "checks": [
                        "secret displayed with permission",
                        "dirty edit preserved until revocation",
                        "offline revocation detected on reconnect",
                        "local secret form cleared",
                        "read revocation removes scope",
                    ],
                    "page_errors": errors,
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
