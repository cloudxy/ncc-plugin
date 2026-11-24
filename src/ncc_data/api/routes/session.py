"""Authenticated same-origin FastAPI application. Schema changes are an explicit CLI step."""

from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, update

from ncc_data.api.problems import problem
from ncc_data.application.security import (
    DEFAULT_ADMIN_USERNAME,
    create_session,
    credential_change_policy,
    password_hash,
    password_matches,
)
from ncc_data.application.service import Service
from ncc_data.domain.contracts import (
    CredentialChangeInput,
    Login,
)
from ncc_data.persistence.models import LoginAttempt, Session, User, utcnow
from ncc_shared.errors import require
from ncc_shared.serialization import digest


def _set_auth_cookies(response: JSONResponse, token: str, csrf: str, settings) -> None:
    response.set_cookie(
        "ncc_session",
        token,
        httponly=True,
        secure=settings.secure_cookie,
        samesite="strict",
        max_age=settings.session_hours * 3600,
    )
    response.set_cookie(
        "ncc_csrf",
        csrf,
        httponly=False,
        secure=settings.secure_cookie,
        samesite="strict",
        max_age=settings.session_hours * 3600,
    )


def build_router(service, settings, factory, dummy_hash, bind_host=None):
    router = APIRouter()

    @router.post("/api/v1/auth/login")
    async def login(value: Login, request: Request):
        require(request.headers.get("x-ncc-client") == "console", "client", "登录需要同源JSON客户端", 403)
        key = digest(value.username + ":" + (request.client.host if request.client else "unknown"))
        failure = False
        async with factory() as db, db.begin():
            attempt = await db.scalar(select(LoginAttempt).where(LoginAttempt.key == key).with_for_update())
            if not attempt:
                attempt = LoginAttempt(key=key, failures=0)
                db.add(attempt)
                await db.flush()
            if attempt.window_at < utcnow() - timedelta(minutes=5):
                attempt.window_at, attempt.failures = utcnow(), 0
            require(attempt.failures < 5, "login_rate", "登录失败次数过多，请五分钟后重试", 429)
            user = await db.scalar(select(User).where(User.username == value.username))
            valid = password_matches(value.password, user.password_hash if user else dummy_hash)
            if not user or not user.active or not valid:
                attempt.failures += 1
                failure = True
            else:
                attempt.failures = 0
                token, csrf = await create_session(db, user, settings.session_hours)
                must_change, enforced, reminder = credential_change_policy(
                    request, settings, user, bind_host=bind_host
                )
                identity = {
                    "id": user.id,
                    "username": user.username,
                    "admin": user.admin,
                    "csrf": csrf,
                    "must_change_credentials": must_change,
                    "credential_change_enforced": enforced,
                    "credential_change_reminder": reminder,
                }
        if failure:
            return problem("login_failed", "用户名或密码错误", 401)
        response = JSONResponse(identity)
        _set_auth_cookies(response, token, csrf, settings)
        return response

    @router.get("/api/v1/me")
    async def me(request: Request, svc: Service = Depends(service, scope="function")):
        must_change, enforced, reminder = credential_change_policy(
            request, settings, svc.actor, bind_host=bind_host
        )
        return {
            "id": svc.actor.id,
            "username": svc.actor.username,
            "admin": svc.actor.admin,
            "csrf": request.cookies.get("ncc_csrf", ""),
            "version": "4.0.0",
            "must_change_credentials": must_change,
            "credential_change_enforced": enforced,
            "credential_change_reminder": reminder,
        }

    @router.post("/api/v1/auth/credentials")
    async def change_credentials(
        value: CredentialChangeInput,
        request: Request,
        svc: Service = Depends(service, scope="function"),
    ):
        require(
            getattr(request.state, "session_kind", "browser") == "browser",
            "credential_kind",
            "凭据修改需要浏览器登录会话",
            403,
        )
        user = svc.actor
        require(
            password_matches(value.current_password, user.password_hash),
            "invalid_password",
            "当前密码不正确",
            403,
        )
        new_username = value.new_username.strip()
        require(
            2 <= len(new_username) <= 128
            and not any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in new_username),
            "invalid_username",
            "账号名长度须为2到128个字符且不能包含空白或控制字符",
            400,
        )
        if user.must_change_credentials:
            require(
                new_username.lower() != DEFAULT_ADMIN_USERNAME,
                "default_username_forbidden",
                "请修改默认管理员账号名，不能继续使用 admin",
                400,
            )
            require(
                value.new_password != value.current_password,
                "password_unchanged",
                "新密码不能与当前密码相同",
                400,
            )
        if new_username != user.username:
            conflict = await svc.db.scalar(
                select(User.id).where(User.username == new_username, User.id != user.id)
            )
            require(conflict is None, "duplicate_user", "账号名已存在", 409)

        user.username = new_username
        user.password_hash = password_hash(value.new_password)
        user.must_change_credentials = False

        await svc.db.execute(update(Session).where(Session.user_id == user.id).values(revoked=True))
        token, csrf = await create_session(svc.db, user, settings.session_hours)
        response = JSONResponse(
            {
                "id": user.id,
                "username": user.username,
                "admin": user.admin,
                "csrf": csrf,
                "must_change_credentials": False,
                "credential_change_enforced": False,
                "credential_change_reminder": "",
            }
        )
        _set_auth_cookies(response, token, csrf, settings)
        return response

    @router.post("/api/v1/auth/logout")
    async def logout(request: Request, svc: Service = Depends(service, scope="function")):
        session = await svc.db.get(Session, request.state.session_id)
        session.revoked = True
        response = JSONResponse({"logged_out": True})
        response.delete_cookie("ncc_session")
        response.delete_cookie("ncc_csrf")
        return response

    return router
