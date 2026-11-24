from __future__ import annotations

import secrets

import httpx
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from ncc_data.api.app import create_app
from ncc_data.application.security import (
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USERNAME,
    default_bootstrap_password_hash,
    ensure_default_admin,
    password_matches,
)
from ncc_data.persistence.database import database
from ncc_data.persistence.models import Membership, Scope, User
from ncc_data.runtime.settings import Settings
from tests.backend.conftest import retire_ephemeral_users


async def test_ensure_default_admin_idempotent_on_empty_and_nonempty_tables(store):
    factory, _ = store
    # 1) Non-empty ncc-dev table: ensure_default_admin must return False without adding or mutating users.
    async with factory() as db, db.begin():
        before_count = await db.scalar(select(func.count()).select_from(User))
        assert before_count >= 2
        created = await ensure_default_admin(db)
        after_count = await db.scalar(select(func.count()).select_from(User))
        assert created is False
        assert after_count == before_count

    # 2) Empty table simulation via transaction-scoped pg_temp shadow table on ncc-dev (zero mutation to public.ncc_user).
    engine, _ = database(factory._factory.kw["bind"].url.render_as_string(hide_password=False))
    try:
        async with engine.connect() as conn:
            trans = await conn.begin()
            try:
                await conn.execute(
                    text("CREATE TEMP TABLE ncc_user (LIKE public.ncc_user INCLUDING ALL)")
                )
                await conn.execute(text("SET LOCAL search_path TO pg_temp, public"))
                temp_factory = async_sessionmaker(bind=conn, expire_on_commit=False)
                async with temp_factory() as temp_db:
                    assert await temp_db.scalar(select(func.count()).select_from(User)) == 0
                    first_created = await ensure_default_admin(temp_db)
                    assert first_created is True
                    admin_row = await temp_db.scalar(
                        select(User).where(User.username == DEFAULT_ADMIN_USERNAME)
                    )
                    assert admin_row is not None
                    assert admin_row.admin is True
                    assert admin_row.active is True
                    assert admin_row.must_change_credentials is True
                    assert password_matches(DEFAULT_ADMIN_PASSWORD, admin_row.password_hash) is True

                    second_created = await ensure_default_admin(temp_db)
                    assert second_created is False
                    assert await temp_db.scalar(select(func.count()).select_from(User)) == 1
            finally:
                await trans.rollback()
    finally:
        await engine.dispose()


async def test_default_admin_loopback_reminder_real_ip_enforcement_and_credential_rotation(store):
    factory, ids = store
    suffix = secrets.token_urlsafe(8)
    new_username = f"test-chief-editor-{suffix}"
    new_password = f"NewStrongPass-{secrets.token_urlsafe(12)}"
    created_scope_ids: list[str] = []
    boot_user_id: str | None = None

    async with factory() as db, db.begin():
        existing_other_username = (await db.get(User, ids[1])).username
        preexisting_admin = await db.scalar(select(User).where(User.username == DEFAULT_ADMIN_USERNAME))
        assert preexisting_admin is None, "Shared ncc-dev should not hold an unretired 'admin' row"
        boot = User(
            username=DEFAULT_ADMIN_USERNAME,
            password_hash=default_bootstrap_password_hash(),
            admin=True,
            active=True,
            must_change_credentials=True,
        )
        db.add(boot)
        await db.flush()
        boot_user_id = boot.id
        factory.register_user(boot_user_id)

    try:
        # --- Part A: Loopback access (127.0.0.1) -> reminder only, business endpoints allowed ---
        loopback_settings = Settings(
            database_url="postgresql://unused/unused",
            public_origin="http://127.0.0.1:8761",
        )
        loopback_app = create_app(loopback_settings, factory, bind_host="127.0.0.1")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=loopback_app),
            base_url="http://127.0.0.1:8761",
        ) as loop_client:
            login_res = await loop_client.post(
                "/api/v1/auth/login",
                headers={"x-ncc-client": "console"},
                json={"username": "admin", "password": DEFAULT_ADMIN_PASSWORD},
            )
            assert login_res.status_code == 200, login_res.text
            login_body = login_res.json()
            assert login_body["username"] == "admin"
            assert login_body["must_change_credentials"] is True
            assert login_body["credential_change_enforced"] is False
            assert "首次使用默认管理员账号" in login_body["credential_change_reminder"]

            me_loop = await loop_client.get("/api/v1/me")
            assert me_loop.status_code == 200
            assert me_loop.json()["must_change_credentials"] is True
            assert me_loop.json()["credential_change_enforced"] is False

            # Business APIs remain accessible on loopback
            scopes_loop = await loop_client.get("/api/v1/scopes")
            assert scopes_loop.status_code == 200
            create_scope_res = await loop_client.post(
                "/api/v1/scopes",
                headers={"x-csrf-token": login_body["csrf"]},
                json={"name": f"测试回环书-{suffix}"},
            )
            assert create_scope_res.status_code == 201, create_scope_res.text
            scope_id = create_scope_res.json()["id"]
            created_scope_ids.append(scope_id)

        # --- Part B: Real IP / non-loopback host -> enforced gate (403 credential_change_required) ---
        lan_settings = Settings(
            database_url="postgresql://unused/unused",
            public_origin="https://192.168.1.10:8761",
        )
        lan_app = create_app(lan_settings, factory, bind_host="192.168.1.10")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=lan_app),
            base_url="https://192.168.1.10:8761",
        ) as lan_client, httpx.AsyncClient(
            transport=httpx.ASGITransport(app=lan_app),
            base_url="https://192.168.1.10:8761",
        ) as stale_client:
            # Second session on stale_client to verify old-session revocation later
            stale_login = await stale_client.post(
                "/api/v1/auth/login",
                headers={"x-ncc-client": "console"},
                json={"username": "admin", "password": DEFAULT_ADMIN_PASSWORD},
            )
            assert stale_login.status_code == 200

            lan_login = await lan_client.post(
                "/api/v1/auth/login",
                headers={"x-ncc-client": "console"},
                json={"username": "admin", "password": DEFAULT_ADMIN_PASSWORD},
            )
            assert lan_login.status_code == 200
            lan_body = lan_login.json()
            assert lan_body["must_change_credentials"] is True
            assert lan_body["credential_change_enforced"] is True
            assert lan_body["credential_change_reminder"] != ""
            csrf = lan_body["csrf"]
            csrf_headers = {"x-csrf-token": csrf}

            # Whitelisted /api/v1/me still succeeds and reports enforced=True
            me_lan = await lan_client.get("/api/v1/me")
            assert me_lan.status_code == 200
            assert me_lan.json()["credential_change_enforced"] is True

            # Business APIs and SSE events are blocked with 403 credential_change_required
            blocked_scopes = await lan_client.get("/api/v1/scopes")
            assert blocked_scopes.status_code == 403
            assert blocked_scopes.json()["code"] == "credential_change_required"

            blocked_post = await lan_client.post(
                "/api/v1/scopes",
                headers=csrf_headers,
                json={"name": "被拦截书"},
            )
            assert blocked_post.status_code == 403
            assert blocked_post.json()["code"] == "credential_change_required"

            blocked_sse = await lan_client.get(f"/api/v1/scopes/{scope_id}/events")
            assert blocked_sse.status_code == 403
            assert blocked_sse.json()["code"] == "credential_change_required"

            # Also verify non-loopback Host header alone triggers enforcement even when bind_host is None
            header_only_app = create_app(loopback_settings, factory, bind_host=None)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=header_only_app),
                base_url="http://127.0.0.1:8761",
            ) as hdr_client:
                await hdr_client.post(
                    "/api/v1/auth/login",
                    headers={"x-ncc-client": "console"},
                    json={"username": "admin", "password": DEFAULT_ADMIN_PASSWORD},
                )
                hdr_blocked = await hdr_client.get(
                    "/api/v1/scopes", headers={"host": "192.168.1.10:8761"}
                )
                assert hdr_blocked.status_code == 403
                assert hdr_blocked.json()["code"] == "credential_change_required"

            # --- Part C: /api/v1/auth/credentials negative validations ---
            # 1) Wrong current_password -> 403 invalid_password
            bad_cur = await lan_client.post(
                "/api/v1/auth/credentials",
                headers=csrf_headers,
                json={
                    "current_password": "wrong-password",
                    "new_username": new_username,
                    "new_password": new_password,
                },
            )
            assert bad_cur.status_code == 403
            assert bad_cur.json()["code"] == "invalid_password"

            # 2) Keeping default username 'admin' (case-insensitive) -> 400 default_username_forbidden
            keep_admin = await lan_client.post(
                "/api/v1/auth/credentials",
                headers=csrf_headers,
                json={
                    "current_password": DEFAULT_ADMIN_PASSWORD,
                    "new_username": "Admin",
                    "new_password": new_password,
                },
            )
            assert keep_admin.status_code == 400
            assert keep_admin.json()["code"] == "default_username_forbidden"

            # 3) Short password (< 12 chars) -> 422 invalid_request (Pydantic min_length=12)
            short_pw = await lan_client.post(
                "/api/v1/auth/credentials",
                headers=csrf_headers,
                json={
                    "current_password": DEFAULT_ADMIN_PASSWORD,
                    "new_username": new_username,
                    "new_password": "short123",
                },
            )
            assert short_pw.status_code in {400, 422}
            assert short_pw.json()["code"] in {"invalid_request", "weak_password"}

            # 4) Duplicate existing username -> 409 duplicate_user
            dup_user = await lan_client.post(
                "/api/v1/auth/credentials",
                headers=csrf_headers,
                json={
                    "current_password": DEFAULT_ADMIN_PASSWORD,
                    "new_username": existing_other_username,
                    "new_password": new_password,
                },
            )
            assert dup_user.status_code == 409
            assert dup_user.json()["code"] == "duplicate_user"

            # --- Part D: Valid credential change -> rotates session, revokes stale sessions, unlocks APIs ---
            ok_change = await lan_client.post(
                "/api/v1/auth/credentials",
                headers=csrf_headers,
                json={
                    "current_password": DEFAULT_ADMIN_PASSWORD,
                    "new_username": new_username,
                    "new_password": new_password,
                },
            )
            assert ok_change.status_code == 200, ok_change.text
            updated = ok_change.json()
            assert updated["username"] == new_username
            assert updated["must_change_credentials"] is False
            assert updated["credential_change_enforced"] is False
            assert updated["credential_change_reminder"] == ""
            assert updated["csrf"] != csrf

            # Stale client's old session cookie is immediately revoked -> 401
            stale_me = await stale_client.get("/api/v1/me")
            assert stale_me.status_code == 401

            # Active client received fresh session + csrf cookies and can now call business APIs on real IP
            unlocked_scopes = await lan_client.get("/api/v1/scopes")
            assert unlocked_scopes.status_code == 200
            assert any(s["id"] == scope_id for s in unlocked_scopes.json())

            # Old admin/123456 login fails; new credentials succeed with must_change_credentials=False
            old_login = await stale_client.post(
                "/api/v1/auth/login",
                headers={"x-ncc-client": "console"},
                json={"username": "admin", "password": DEFAULT_ADMIN_PASSWORD},
            )
            assert old_login.status_code == 401
            fresh_login = await stale_client.post(
                "/api/v1/auth/login",
                headers={"x-ncc-client": "console"},
                json={"username": new_username, "password": new_password},
            )
            assert fresh_login.status_code == 200
            assert fresh_login.json()["must_change_credentials"] is False
            assert fresh_login.json()["credential_change_enforced"] is False
    finally:
        async with factory() as db, db.begin():
            if created_scope_ids:
                await db.execute(delete(Membership).where(Membership.scope_id.in_(created_scope_ids)))
                await db.execute(delete(Scope).where(Scope.id.in_(created_scope_ids)))
            if boot_user_id is not None:
                user_row = await db.get(User, boot_user_id)
                if user_row is not None and user_row.username == DEFAULT_ADMIN_USERNAME:
                    user_row.username = f"test-retired-admin-{suffix}"
                await retire_ephemeral_users(db, [boot_user_id])
