"""Authenticated same-origin FastAPI application. Schema changes are an explicit CLI step."""

import hmac
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from ncc_data.api.problems import problem
from ncc_data.api.routes.administration import build_router as administration_router
from ncc_data.api.routes.creation import build_router as creation_router
from ncc_data.api.routes.events import build_router as events_router
from ncc_data.api.routes.exchange import build_router as exchange_router
from ncc_data.api.routes.knowledge import build_router as knowledge_router
from ncc_data.api.routes.session import build_router as session_router
from ncc_data.api.routes.system import build_router as system_router
from ncc_data.api.routes.workspace import build_router as workspace_router
from ncc_data.application.security import (
    authenticate,
    password_hash,
)
from ncc_data.application.service import Service
from ncc_data.persistence.database import database
from ncc_data.runtime.settings import Settings
from ncc_shared.errors import DomainError, require
from ncc_shared.serialization import digest, jsonable


def create_app(settings=None, factory=None):
    settings = settings or Settings.from_env()
    engine = None
    if factory is None:
        engine, factory = database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app):
        yield
        if engine:
            await engine.dispose()

    app = FastAPI(
        title="NCC 创作与资料管理",
        version="4.0.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.factory, app.state.settings = factory, settings
    dummy_hash = password_hash(secrets.token_urlsafe(24))

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        return problem(
            exc.code,
            exc.detail,
            exc.status,
            trace_id=getattr(request.state, "trace_id", ""),
            **jsonable(exc.extra),
        )

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ValidationError)
    async def invalid_request(request, exc):
        return problem(
            "invalid_request",
            "请求字段、类型或范围不符",
            errors=[{"path": list(e["loc"]), "message": e["msg"]} for e in exc.errors()],
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error(request, exc):
        return problem(
            "integrity_conflict",
            "唯一性、引用或事务约束冲突，请刷新比较",
            409,
            trace_id=getattr(request.state, "trace_id", ""),
        )

    @app.middleware("http")
    async def security_headers(request, call_next):
        request.state.trace_id = secrets.token_hex(8)
        if request.headers.get("x-ncc-profile", settings.profile) != settings.profile:
            return problem("profile_mismatch", "请求的正式/测试模式与服务不一致，操作未执行", 409)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin != settings.public_origin:
                return problem("origin", "请求来源不被允许", 403)
            length = request.headers.get("content-length")
            if length is None:
                return problem("content_length", "写请求需要明确内容长度", 411)
            if not length.isdigit() or int(length) > settings.upload_limit + 1024 * 1024:
                return problem("request_size", "请求内容超过限制", 413)
        response = await call_next(request)
        response.headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "no-referrer",
                "Cache-Control": "no-store",
                "X-Trace-ID": request.state.trace_id,
                "X-NCC-Profile": settings.profile,
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
            }
        )
        return response

    async def service(request: Request):
        async with factory() as db, db.begin():
            bearer = request.headers.get("authorization", "")
            token = bearer[7:] if bearer.startswith("Bearer ") else request.cookies.get("ncc_session")
            actor, session = await authenticate(db, token)
            if bearer:
                require(session.kind == "cli", "credential_kind", "自动化必须使用独立范围凭据", 403)
            elif request.method not in {"GET", "HEAD", "OPTIONS"}:
                require(
                    hmac.compare_digest(digest(request.headers.get("x-csrf-token", "")), session.csrf_hash),
                    "csrf",
                    "写请求缺少有效CSRF令牌",
                    403,
                )
            request.state.session_id = session.id
            yield Service(db, actor)

    app.include_router(session_router(service, settings, factory, dummy_hash))
    app.include_router(knowledge_router(service))
    app.include_router(workspace_router(service))
    app.include_router(creation_router(service))
    app.include_router(administration_router(service))
    app.include_router(exchange_router(service, settings))
    app.include_router(events_router(factory))
    app.include_router(system_router(app, service, settings, factory))
    return app
