"""Authenticated same-origin FastAPI application. Schema changes are an explicit CLI step."""

from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from ncc_data.api.problems import problem
from ncc_data.application.security import (
    create_session,
    password_matches,
)
from ncc_data.application.service import Service
from ncc_data.domain.contracts import (
    Login,
)
from ncc_data.persistence.models import LoginAttempt, Session, User, utcnow
from ncc_shared.errors import require
from ncc_shared.serialization import digest


def build_router(service, settings, factory, dummy_hash):
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
                identity = {"id": user.id, "username": user.username, "admin": user.admin, "csrf": csrf}
        if failure:
            return problem("login_failed", "用户名或密码错误", 401)
        response = JSONResponse(identity)
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
        return response

    @router.get("/api/v1/me")
    async def me(request: Request, svc: Service = Depends(service, scope="function")):
        return {
            "id": svc.actor.id,
            "username": svc.actor.username,
            "admin": svc.actor.admin,
            "csrf": request.cookies.get("ncc_csrf", ""),
            "version": "4.0.0",
        }

    @router.post("/api/v1/auth/logout")
    async def logout(request: Request, svc: Service = Depends(service, scope="function")):
        session = await svc.db.get(Session, request.state.session_id)
        session.revoked = True
        response = JSONResponse({"logged_out": True})
        response.delete_cookie("ncc_session")
        response.delete_cookie("ncc_csrf")
        return response

    return router
