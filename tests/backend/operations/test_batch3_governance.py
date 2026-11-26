from __future__ import annotations

import copy
import secrets
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import select, update

from ncc_data.api.app import create_app
from ncc_data.application.security import password_hash
from ncc_data.domain.definitions import SYSTEM_SCOPE
from ncc_data.persistence.models import Assessment, Audit, Scope, User
from ncc_data.runtime.settings import Settings
from ncc_shared.quality.policy import POLICY_HASH

# Minimal valid 1x1 PNG
_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


class _Completed:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


async def _login(client: httpx.AsyncClient, username: str, password: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/login",
        headers={"x-ncc-client": "console"},
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _delete(client: httpx.AsyncClient, path: str, headers: dict[str, str]) -> httpx.Response:
    return await client.delete(path, headers={**headers, "content-length": "0"})


async def test_user_governance_directory_and_security_guards(store):
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
    created_user_id: str | None = None

    try:
        async with (
            httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8788") as admin_client,
            httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8788") as regular_client,
            httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8788") as managed_client,
        ):
            admin_me = await _login(admin_client, admin_username, admin_pw)
            admin_headers = {"x-csrf-token": admin_me["csrf"]}
            reg_me = await _login(regular_client, regular_username, regular_pw)
            reg_headers = {"x-csrf-token": reg_me["csrf"]}

            # Non-admin gets 403 on user management endpoints
            assert (await regular_client.get("/api/v1/users")).status_code == 403
            assert (
                await regular_client.patch(f"/api/v1/users/{admin_id}", headers=reg_headers, json={"active": True})
            ).status_code == 403

            # Non-admin CAN query /api/v1/users/directory with strict minimal field isolation
            dir_resp = await regular_client.get(
                "/api/v1/users/directory", params={"q": admin_username[-6:]}
            )
            assert dir_resp.status_code == 200, dir_resp.text
            dir_items = dir_resp.json()
            assert any(item["id"] == admin_id for item in dir_items)
            for item in dir_items:
                assert set(item.keys()) == {"id", "username"}

            # Admin creates a new account (verifies user.create audit)
            new_uname = f"test-gov-user-{secrets.token_urlsafe(6)}"
            new_pw = f"InitialPass-{secrets.token_urlsafe(10)}"
            create_resp = await admin_client.post(
                "/api/v1/users",
                headers=admin_headers,
                json={"username": new_uname, "password": new_pw},
            )
            assert create_resp.status_code == 201, create_resp.text
            created_user_id = create_resp.json()["id"]
            factory.register_user(created_user_id, new_pw)

            # Admin lists users: never leaks password_hash
            users_resp = await admin_client.get("/api/v1/users")
            assert users_resp.status_code == 200
            users_list = users_resp.json()
            created_entry = next(u for u in users_list if u["id"] == created_user_id)
            assert "password_hash" not in created_entry
            assert created_entry["active"] is True
            assert created_entry["admin"] is False
            assert created_entry["must_change_credentials"] is False
            assert isinstance(created_entry["created_at"], str)

            # Self-disable is rejected with 409 self_disable
            self_disable = await admin_client.patch(
                f"/api/v1/users/{admin_id}",
                headers=admin_headers,
                json={"active": False},
            )
            assert self_disable.status_code == 409
            assert self_disable.json()["code"] == "self_disable"

            # Managed user logs in; admin resets password -> revokes old session & sets must_change_credentials=True
            await _login(managed_client, new_uname, new_pw)
            assert (await managed_client.get("/api/v1/me")).status_code == 200

            reset_pw = f"ResetPass-{secrets.token_urlsafe(12)}"
            patch_reset = await admin_client.patch(
                f"/api/v1/users/{created_user_id}",
                headers=admin_headers,
                json={"reset_password": reset_pw},
            )
            assert patch_reset.status_code == 200, patch_reset.text
            assert patch_reset.json()["must_change_credentials"] is True

            # Old browser session of managed_client is immediately invalid (401)
            assert (await managed_client.get("/api/v1/me")).status_code == 401

            # Managed user logs in with reset password -> must_change_credentials=True, dynamic non-admin reminder
            managed_me = await _login(managed_client, new_uname, reset_pw)
            assert managed_me["must_change_credentials"] is True
            assert new_uname in managed_me["credential_change_reminder"]
            assert "（admin）" not in managed_me["credential_change_reminder"]

            me_loop_check = await managed_client.get("/api/v1/me")
            assert me_loop_check.status_code == 200
            me_loop_json = me_loop_check.json()
            assert me_loop_json["credential_change_reminder"] == (
                f"当前账号（{new_uname}）使用的是初始或已重置临时密码，请及时修改密码。"
            )
            assert "（admin）" not in me_loop_json["credential_change_reminder"]

            me_lan_check = await managed_client.get(
                "/api/v1/me", headers={"Host": "192.168.1.25:8788"}
            )
            assert me_lan_check.status_code == 200
            me_lan_json = me_lan_check.json()
            assert me_lan_json["credential_change_enforced"] is True
            assert me_lan_json["credential_change_reminder"] == (
                f"当前监听或访问非回环地址，账号（{new_uname}）使用的是初始或已重置临时密码，请先修改密码后再继续使用。"
            )
            assert "（admin）" not in me_lan_json["credential_change_reminder"]

            rotated_uname = f"test-rotated-{secrets.token_urlsafe(6)}"
            rotated_pw = f"RotatedPass-{secrets.token_urlsafe(12)}"
            rot_resp = await managed_client.post(
                "/api/v1/auth/credentials",
                headers={"x-csrf-token": managed_me["csrf"]},
                json={
                    "current_password": reset_pw,
                    "new_username": rotated_uname,
                    "new_password": rotated_pw,
                },
            )
            assert rot_resp.status_code == 200, rot_resp.text
            assert rot_resp.json()["must_change_credentials"] is False

            # Disable managed user -> revokes session & hides from /users/directory
            disable_resp = await admin_client.patch(
                f"/api/v1/users/{created_user_id}",
                headers=admin_headers,
                json={"active": False},
            )
            assert disable_resp.status_code == 200
            assert disable_resp.json()["active"] is False
            assert (await managed_client.get("/api/v1/me")).status_code == 401
            dir_after_disable = (
                await regular_client.get("/api/v1/users/directory", params={"q": rotated_uname})
            ).json()
            assert all(u["id"] != created_user_id for u in dir_after_disable)

        # Verify last_admin 409 guard inside a rolled-back transaction so shared ncc-dev admins are untouched
        async with factory() as db:
            trans = await db.begin()
            try:
                await db.execute(update(User).where(User.id != admin_id).values(admin=False))
                from ncc_data.application.service import Service
                from ncc_data.domain.contracts import UserUpdateInput
                from ncc_shared.errors import DomainError

                svc = Service(db, await db.get(User, admin_id))
                try:
                    await svc.update_user(admin_id, UserUpdateInput(admin=False))
                    raise AssertionError("Expected last_admin DomainError")
                except DomainError as exc:
                    assert exc.status == 409
                    assert exc.code == "last_admin"
            finally:
                await trans.rollback()

        # Verify SYSTEM_SCOPE audits for user.create, user.update (no password plaintext), auth.credentials_change
        async with factory() as db:
            sys_audits = (
                await db.scalars(
                    select(Audit)
                    .where(
                        Audit.scope_id == SYSTEM_SCOPE,
                        Audit.actor_id.in_([admin_id, created_user_id]),
                    )
                    .order_by(Audit.created_at.desc())
                    .limit(20)
                )
            ).all()
            actions = {a.action for a in sys_audits}
            assert {"user.create", "user.update", "auth.credentials_change"} <= actions
            serialized_details = str([a.detail for a in sys_audits])
            assert reset_pw not in serialized_details
            assert rotated_pw not in serialized_details
    finally:
        if created_user_id:
            async with factory() as db, db.begin():
                u = await db.get(User, created_user_id)
                if u is not None:
                    u.active = False
                    u.password_hash = password_hash(secrets.token_urlsafe(24))


async def test_members_by_username_token_revocation_scope_archive_delete_and_audits(store):
    factory, ids = store
    owner_id, collab_id = ids
    owner_pw = factory.credentials[owner_id]
    collab_pw = factory.credentials[collab_id]

    async with factory() as db:
        owner_username = (await db.get(User, owner_id)).username
        collab_username = (await db.get(User, collab_id)).username

    settings = Settings(database_url="unused", public_origin="http://127.0.0.1:8788")
    app = create_app(settings, factory=factory)
    transport = httpx.ASGITransport(app=app)

    async with (
        httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8788") as owner_client,
        httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8788") as collab_client,
        httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8788") as cli_client,
    ):
        owner_me = await _login(owner_client, owner_username, owner_pw)
        oh = {"x-csrf-token": owner_me["csrf"]}
        collab_me = await _login(collab_client, collab_username, collab_pw)
        ch = {"x-csrf-token": collab_me["csrf"]}

        # Create scope -> records scope.create audit
        scope_resp = await owner_client.post("/api/v1/scopes", headers=oh, json={"name": "治理闭环测试书"})
        assert scope_resp.status_code == 201, scope_resp.text
        sid = scope_resp.json()["id"]
        assert scope_resp.json()["archived"] is False

        # Owner cannot add/modify themselves as member (409 owner_membership)
        self_mem = await owner_client.post(
            f"/api/v1/scopes/{sid}/members",
            headers=oh,
            json={"username": owner_username, "actions": ["read"]},
        )
        assert self_mem.status_code == 409
        assert self_mem.json()["code"] == "owner_membership"

        # Add collaborator by username (no UUID required!)
        add_mem = await owner_client.post(
            f"/api/v1/scopes/{sid}/members",
            headers=oh,
            json={"username": collab_username, "actions": ["read", "edit"]},
        )
        assert add_mem.status_code == 200, add_mem.text
        assert any(m["user_id"] == collab_id and m["username"] == collab_username for m in add_mem.json())

        # Collaborator issues a scoped CLI token -> records token.create audit
        tok_resp = await collab_client.post(
            f"/api/v1/scopes/{sid}/tokens",
            headers=ch,
            json={"actions": ["read"], "hours": 4},
        )
        assert tok_resp.status_code == 201, tok_resp.text
        collab_cli_token = tok_resp.json()["token"]
        assert (
            await cli_client.get(
                f"/api/v1/scopes/{sid}", headers={"Authorization": f"Bearer {collab_cli_token}"}
            )
        ).status_code == 200
        # Scoped credential cannot read global user directory
        assert (
            await cli_client.get(
                "/api/v1/users/directory", headers={"Authorization": f"Bearer {collab_cli_token}"}
            )
        ).status_code == 403

        # Owner creates & revokes a token -> records token.create & token.revoke audits
        owner_tok = (
            await owner_client.post(
                f"/api/v1/scopes/{sid}/tokens",
                headers=oh,
                json={"actions": ["read"], "hours": 2},
            )
        ).json()
        tok_list = (await owner_client.get(f"/api/v1/scopes/{sid}/tokens")).json()
        assert len(tok_list) == 1
        del_tok = await _delete(owner_client, f"/api/v1/scopes/{sid}/tokens/{tok_list[0]['id']}", oh)
        assert del_tok.status_code == 200
        assert owner_tok["token"] != ""

        # Remove collaborator via DELETE /members/{uid} -> deletes Membership AND revokes collaborator's CLI token!
        rem_resp = await _delete(owner_client, f"/api/v1/scopes/{sid}/members/{collab_id}", oh)
        assert rem_resp.status_code == 200, rem_resp.text
        assert rem_resp.json() == []
        assert (
            await cli_client.get(
                f"/api/v1/scopes/{sid}", headers={"Authorization": f"Bearer {collab_cli_token}"}
            )
        ).status_code == 401

        # Archive scope -> hidden by default, visible when include_archived=true, then unarchive
        arch_resp = await owner_client.patch(
            f"/api/v1/scopes/{sid}", headers=oh, json={"archived": True}
        )
        assert arch_resp.status_code == 200
        assert arch_resp.json()["archived"] is True

        active_scopes = (await owner_client.get("/api/v1/scopes")).json()
        assert all(s["id"] != sid for s in active_scopes)
        all_scopes = (
            await owner_client.get("/api/v1/scopes", params={"include_archived": "true"})
        ).json()
        assert any(s["id"] == sid and s["archived"] is True for s in all_scopes)

        unarch_resp = await owner_client.patch(
            f"/api/v1/scopes/{sid}", headers=oh, json={"archived": False, "name": "治理闭环已恢复"}
        )
        assert unarch_resp.status_code == 200
        assert unarch_resp.json()["archived"] is False
        assert unarch_resp.json()["name"] == "治理闭环已恢复"

        # Commit a chapter entity so sid has version == 1 (non-empty) + create & revoke delegation
        ch_eid = str(uuid4())
        chg = (
            await owner_client.post(
                f"/api/v1/scopes/{sid}/changes",
                headers=oh,
                json={
                    "title": "新建首章",
                    "base_version": 0,
                    "operations": [
                        {
                            "op": "create",
                            "entity_id": ch_eid,
                            "kind": "chapter",
                            "name": "第一章 朔风起",
                            "data": {"position": 1},
                            "text": "北境初雪落满城头。",
                        }
                    ],
                },
            )
        ).json()
        adopt_resp = await owner_client.post(
            f"/api/v1/scopes/{sid}/changes/{chg['id']}/adopt",
            headers={**oh, "idempotency-key": str(uuid4())},
            json={},
        )
        assert adopt_resp.status_code == 200

        del_create = await owner_client.post(
            f"/api/v1/scopes/{sid}/delegations",
            headers=oh,
            json={
                "target_ids": [ch_eid],
                "schemes": ["P1"],
                "hours": 4,
                "count": 2,
                "mode": "author_trial",
                "note": "合成测试授权",
            },
        )
        assert del_create.status_code == 201, del_create.text
        did = del_create.json()["id"]
        del_revoke = await _delete(owner_client, f"/api/v1/scopes/{sid}/delegations/{did}", oh)
        assert del_revoke.status_code == 200

        # Non-empty scope (version == 1) CANNOT be deleted -> 409 scope_not_empty
        non_empty_del = await _delete(owner_client, f"/api/v1/scopes/{sid}", oh)
        assert non_empty_del.status_code == 409
        assert non_empty_del.json()["code"] == "scope_not_empty"

        # Empty parent scope with child scope CANNOT be deleted until child is deleted; empty leaf scope CAN be deleted
        parent_empty = (
            await owner_client.post("/api/v1/scopes", headers=oh, json={"name": "空父空间"})
        ).json()["id"]
        child_empty = (
            await owner_client.post(
                "/api/v1/scopes",
                headers=oh,
                json={"name": "空子空间", "parent_id": parent_empty},
            )
        ).json()["id"]
        parent_blocked = await _delete(owner_client, f"/api/v1/scopes/{parent_empty}", oh)
        assert parent_blocked.status_code == 409
        assert parent_blocked.json()["code"] == "scope_not_empty"

        child_deleted = await _delete(owner_client, f"/api/v1/scopes/{child_empty}", oh)
        assert child_deleted.status_code == 200
        assert child_deleted.json() == {"deleted": True, "id": child_empty}
        assert (await owner_client.get(f"/api/v1/scopes/{child_empty}")).status_code == 404

        parent_deleted = await _delete(owner_client, f"/api/v1/scopes/{parent_empty}", oh)
        assert parent_deleted.status_code == 200
        assert (await owner_client.get(f"/api/v1/scopes/{parent_empty}")).status_code == 404

        # Verify audit filtering, actor_username, and newly added scope-level audits
        audits_all = (await owner_client.get(f"/api/v1/scopes/{sid}/audit", params={"limit": 50})).json()
        audit_actions = {row["action"] for row in audits_all}
        assert {
            "scope.create",
            "member.set",
            "member.remove",
            "token.create",
            "token.revoke",
            "scope.archive",
            "scope.rename",
            "delegation.revoke",
        } <= audit_actions
        assert all(row["actor_username"] in {owner_username, collab_username} for row in audits_all)

        filtered = (
            await owner_client.get(
                f"/api/v1/scopes/{sid}/audit",
                params={"action": "delegation.revoke", "actor_id": owner_id, "limit": 5, "offset": 0},
            )
        ).json()
        assert len(filtered) == 1
        assert filtered[0]["action"] == "delegation.revoke"
        assert filtered[0]["actor_username"] == owner_username

        # Insert synthetic Assessment and verify entity_name, entity_kind, created_at
        async with factory() as db, db.begin():
            db.add(
                Assessment(
                    scope_id=sid,
                    actor_id=owner_id,
                    entity_id=ch_eid,
                    content_hash="a" * 64,
                    dependency_version=1,
                    scheme="P1",
                    policy_hash=POLICY_HASH,
                    evaluator="chat:test-judge",
                    report={"summary": "节奏紧凑", "requires_secret": False},
                    score=Decimal("4.5"),
                    verdict="qualified",
                )
            )
        assessments_resp = await owner_client.get(f"/api/v1/scopes/{sid}/assessments")
        assert assessments_resp.status_code == 200
        assessments = assessments_resp.json()
        assert len(assessments) == 1
        assert assessments[0]["entity_name"] == "第一章 朔风起"
        assert assessments[0]["entity_kind"] == "chapter"
        assert isinstance(assessments[0]["created_at"], str) and "T" in assessments[0]["created_at"]


async def test_safe_map_basemap_inline_whitelist_and_cli_oauth_model_settings(
    store, tmp_path: Path, monkeypatch
):
    factory, ids = store
    owner_id, reader_id = ids
    owner_pw = factory.credentials[owner_id]
    reader_pw = factory.credentials[reader_id]

    auth_file = tmp_path / ".grok" / "auth.json"
    auth_file.parent.mkdir()
    auth_file.write_text(
        '{"xai":{"key":"sk-grok-secret-do-not-leak","refresh_token":"rt-valid","expires_at":"2000-01-01T00:00:00Z"}}',
        encoding="utf-8",
    )

    async with factory() as db:
        owner_username = (await db.get(User, owner_id)).username
        reader_username = (await db.get(User, reader_id)).username
        sys_scope = await db.get(Scope, SYSTEM_SCOPE)
        original_sys_config = copy.deepcopy(sys_scope.config if sys_scope else {})

    monkeypatch.setattr("ncc_data.creation.model_route.Path.home", lambda: tmp_path)
    monkeypatch.setattr("ncc_data.creation.model_route.shutil.which", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr("ncc_data.application.model_settings.Path.home", lambda: tmp_path)
    monkeypatch.setattr("ncc_data.application.model_settings.shutil.which", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(
        "ncc_data.application.model_settings.subprocess.run",
        lambda *a, **kw: _Completed(0, "models: grok-4\nsk-verify-no-leak\n"),
    )

    settings = Settings(database_url="unused", public_origin="http://127.0.0.1:8788")
    app = create_app(settings, factory=factory)
    transport = httpx.ASGITransport(app=app)

    try:
        async with (
            httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8788") as owner_client,
            httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8788") as reader_client,
        ):
            owner_me = await _login(owner_client, owner_username, owner_pw)
            oh = {"x-csrf-token": owner_me["csrf"]}
            await _login(reader_client, reader_username, reader_pw)

            sid = (
                await owner_client.post("/api/v1/scopes", headers=oh, json={"name": "地图与CLI路由测试书"})
            ).json()["id"]
            await owner_client.post(
                f"/api/v1/scopes/{sid}/members",
                headers=oh,
                json={"username": reader_username, "actions": ["read"]},
            )

            # Upload PNG (public), SVG (public), and TXT (secret)
            png_up = await owner_client.post(
                f"/api/v1/scopes/{sid}/attachments?requires_secret=false",
                headers=oh,
                files={"file": ("world-map.png", _TINY_PNG, "image/png")},
            )
            assert png_up.status_code == 201, png_up.text
            png_id = png_up.json()["id"]

            svg_up = await owner_client.post(
                f"/api/v1/scopes/{sid}/attachments?requires_secret=false",
                headers=oh,
                files={"file": ("xss.svg", b"<svg onload='alert(1)'></svg>", "image/svg+xml")},
            )
            assert svg_up.status_code == 201
            svg_id = svg_up.json()["id"]

            secret_up = await owner_client.post(
                f"/api/v1/scopes/{sid}/attachments?requires_secret=true",
                headers=oh,
                files={"file": ("secret-note.png", _TINY_PNG, "image/png")},
            )
            assert secret_up.status_code == 201
            secret_id = secret_up.json()["id"]

            # Reader lists source attachments: sees public PNG & SVG, never secret_id
            reader_list = await reader_client.get(
                f"/api/v1/scopes/{sid}/attachments", params={"purpose": "source"}
            )
            assert reader_list.status_code == 200
            listed_ids = {item["id"] for item in reader_list.json()}
            assert {png_id, svg_id} <= listed_ids
            assert secret_id not in listed_ids
            assert (await reader_client.get(f"/api/v1/scopes/{sid}/attachments/{secret_id}")).status_code == 404

            # Reader fetches PNG with ?inline=true -> safe inline image/png + nosniff + zero download audit spam
            inline_png = await reader_client.get(
                f"/api/v1/scopes/{sid}/attachments/{png_id}", params={"inline": "true"}
            )
            assert inline_png.status_code == 200
            assert inline_png.headers["content-type"] == "image/png"
            assert inline_png.headers["x-content-type-options"] == "nosniff"
            assert inline_png.headers["content-disposition"].startswith("inline;")

            # Reader fetches SVG with ?inline=true -> NEVER inlined, forced attachment + octet-stream!
            inline_svg = await reader_client.get(
                f"/api/v1/scopes/{sid}/attachments/{svg_id}", params={"inline": "true"}
            )
            assert inline_svg.status_code == 200
            assert inline_svg.headers["content-type"] == "application/octet-stream"
            assert inline_svg.headers["content-disposition"].startswith("attachment;")

            audits_after_inline = (
                await owner_client.get(
                    f"/api/v1/scopes/{sid}/audit", params={"action": "attachment.download"}
                )
            ).json()
            assert audits_after_inline == []

            # Persist default map basemap via PUT /studio/map-config and verify in GET /studio/overview
            map_put = await owner_client.put(
                f"/api/v1/scopes/{sid}/studio/map-config",
                headers=oh,
                json={"basemap_attachment_id": png_id},
            )
            assert map_put.status_code == 200, map_put.text
            assert map_put.json()["map_config"] == {"basemap_attachment_id": png_id}

            overview = (await reader_client.get(f"/api/v1/scopes/{sid}/studio/overview")).json()
            assert overview["map_config"] == {"basemap_attachment_id": png_id}

            # CLI OAuth model configuration save, bind default, static & live check
            save_cfg = await owner_client.post(
                "/api/v1/model-settings/configurations",
                headers=oh,
                json={
                    "name": "Grok CLI 创作通道",
                    "transport": "cli_oauth",
                    "cli_provider": "grok",
                    "model_key": "grok-4",
                    "purposes": ["plan", "write", "revise", "judge"],
                    "enabled": True,
                },
            )
            assert save_cfg.status_code == 200, save_cfg.text
            saved_view = save_cfg.json()
            cid = saved_view["saved_id"]
            assert "sk-grok-secret-do-not-leak" not in save_cfg.text

            bind_resp = await owner_client.post(
                "/api/v1/model-settings/defaults",
                headers=oh,
                json={"purpose": "write", "configuration_id": cid},
            )
            assert bind_resp.status_code == 200
            assert bind_resp.json()["effective"]["write"]["configuration_id"] == cid

            static_chk = await owner_client.post(
                f"/api/v1/model-settings/configurations/{cid}/check",
                headers=oh,
            )
            assert static_chk.status_code == 200
            assert static_chk.json()["ok"] is True
            assert static_chk.json()["mode"] == "config"

            live_chk = await owner_client.post(
                f"/api/v1/model-settings/configurations/{cid}/check",
                params={"live": "true"},
                headers=oh,
            )
            assert live_chk.status_code == 200
            assert live_chk.json()["ok"] is True
            assert live_chk.json()["mode"] == "live"
            assert "sk-verify-no-leak" not in live_chk.text
    finally:
        async with factory() as db, db.begin():
            sys_scope = await db.scalar(
                select(Scope).where(Scope.id == SYSTEM_SCOPE).with_for_update()
            )
            if sys_scope is not None:
                sys_scope.config = original_sys_config
