"""Authenticated same-origin FastAPI application. Schema changes are an explicit CLI step."""

import asyncio
import hmac
import json
import secrets
from contextlib import asynccontextmanager
from datetime import timedelta
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from pydantic import Field, ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from .automation import accept_task, create_task
from .config import Settings
from .contracts import (
    AuthorDraft,
    CalibrationInput,
    ChangeInput,
    CreationInput,
    DelegationInput,
    EditChange,
    Intervention,
    Login,
    MaintenanceInput,
    MemberInput,
    Query,
    ScopeInput,
    StateQuery,
    Strict,
    UserInput,
)
from .db import database
from .errors import DomainError, require
from .models import (
    Audit,
    Delegation,
    ImportRun,
    Job,
    LoginAttempt,
    Session,
    User,
    utcnow,
)
from .policy import POLICY, POLICY_HASH
from .security import authenticate, authorize, create_session, password_hash, password_matches
from .service import Service
from .utils import digest, jsonable


class ImportInput(Strict):
    attachment_id: str
    mapping: dict = Field(default_factory=dict)


class ImportApply(Strict):
    acknowledge_unmapped: bool = False


class ExportInput(Strict):
    format: str = "json"
    as_of: int | None = None


class FeedbackInput(Strict):
    choice: str
    note: str = Field(default="", max_length=4000)


class ViewInput(Strict):
    name: str
    query: Query


class TokenInput(Strict):
    actions: list[str]
    hours: int = Field(default=24, ge=1, le=168)


class WorkspaceCommit(Strict):
    format: str
    base_version: int = Field(ge=0)
    files: list[dict] = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=128)
    title: str = Field(default="CLI受控回写", max_length=256)


def problem(code, detail, status=422, **extra):
    return JSONResponse(
        {
            "type": "urn:ncc:problem:" + code,
            "title": detail,
            "status": status,
            "code": code,
            "detail": detail,
            **extra,
        },
        status_code=status,
        media_type="application/problem+json",
    )


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

    @app.post("/api/v1/auth/login")
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

    @app.get("/api/v1/me")
    async def me(request: Request, svc: Service = Depends(service, scope="function")):
        return {
            "id": svc.actor.id,
            "username": svc.actor.username,
            "admin": svc.actor.admin,
            "csrf": request.cookies.get("ncc_csrf", ""),
            "version": "4.0.0",
        }

    @app.post("/api/v1/auth/logout")
    async def logout(request: Request, svc: Service = Depends(service, scope="function")):
        session = await svc.db.get(Session, request.state.session_id)
        session.revoked = True
        response = JSONResponse({"logged_out": True})
        response.delete_cookie("ncc_session")
        response.delete_cookie("ncc_csrf")
        return response

    @app.get("/api/v1/openapi.json")
    async def openapi(svc: Service = Depends(service, scope="function")):
        return app.openapi()

    @app.get("/api/v1/policy")
    async def policy(svc: Service = Depends(service, scope="function")):
        return {**POLICY, "hash": POLICY_HASH}

    @app.get("/api/v1/scopes")
    async def scopes(svc: Service = Depends(service, scope="function")):
        return await svc.scopes()

    @app.post("/api/v1/scopes", status_code=201)
    async def create_scope(value: ScopeInput, svc: Service = Depends(service, scope="function")):
        require(not hasattr(svc.actor, "_access_scope"), "scoped_credential", "范围凭据不能创建其他范围", 403)
        return await svc.create_scope(value)

    @app.get("/api/v1/scopes/{sid}")
    async def scope_info(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.scope_info(sid)

    @app.get("/api/v1/scopes/{sid}/definitions")
    async def definitions(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.definitions(sid)

    @app.post("/api/v1/scopes/{sid}/entities/search")
    async def entities(sid: str, value: Query, svc: Service = Depends(service, scope="function")):
        return await svc.entities(sid, value)

    @app.get("/api/v1/scopes/{sid}/entities/{eid}")
    async def entity(
        sid: str,
        eid: str,
        as_of: int | None = None,
        include_deleted: bool = False,
        svc: Service = Depends(service, scope="function"),
    ):
        return await svc.entity(sid, eid, Query(as_of=as_of, include_deleted=include_deleted))

    @app.get("/api/v1/scopes/{sid}/entities/{eid}/history")
    async def history(sid: str, eid: str, svc: Service = Depends(service, scope="function")):
        return await svc.history(sid, eid)

    @app.get("/api/v1/scopes/{sid}/entities/{eid}/revisions/{rid}")
    async def revision(sid: str, eid: str, rid: str, svc: Service = Depends(service, scope="function")):
        return await svc.revision(sid, eid, rid)

    @app.get("/api/v1/scopes/{sid}/workspace")
    async def workspace_snapshot(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.workspace_snapshot(sid)

    @app.post("/api/v1/scopes/{sid}/workspace/commit")
    async def workspace_commit(
        sid: str, value: WorkspaceCommit, svc: Service = Depends(service, scope="function")
    ):
        return await svc.workspace_commit(sid, value.model_dump(mode="json"))

    @app.post("/api/v1/scopes/{sid}/state/query")
    async def facts(sid: str, value: StateQuery, svc: Service = Depends(service, scope="function")):
        return await svc.facts(sid, value)

    @app.get("/api/v1/scopes/{sid}/graph/{eid}")
    async def graph(sid: str, eid: str, hops: int = 2, svc: Service = Depends(service, scope="function")):
        return await svc.graph(sid, eid, hops)

    @app.get("/api/v1/scopes/{sid}/quality")
    async def quality(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.quality(sid)

    @app.post("/api/v1/scopes/{sid}/maintenance/plan")
    async def maintenance(
        sid: str, value: MaintenanceInput, svc: Service = Depends(service, scope="function")
    ):
        return await svc.maintenance_plan(sid, value)

    @app.get("/api/v1/scopes/{sid}/author-drafts/{key}")
    async def get_draft(sid: str, key: str, svc: Service = Depends(service, scope="function")):
        return await svc.author_draft(sid, key)

    @app.put("/api/v1/scopes/{sid}/author-drafts/{key}")
    async def save_draft(
        sid: str, key: str, value: AuthorDraft, svc: Service = Depends(service, scope="function")
    ):
        return await svc.author_draft(sid, key, value)

    @app.get("/api/v1/scopes/{sid}/changes")
    async def changes(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.changes(sid)

    @app.post("/api/v1/scopes/{sid}/changes", status_code=201)
    async def create_change(sid: str, value: ChangeInput, svc: Service = Depends(service, scope="function")):
        return await svc.create_change(sid, value)

    @app.delete("/api/v1/scopes/{sid}/author-drafts/{key}")
    async def clear_draft(
        sid: str, key: str, version: int, svc: Service = Depends(service, scope="function")
    ):
        return await svc.clear_author_draft(sid, key, version)

    @app.get("/api/v1/scopes/{sid}/changes/{cid}")
    async def change(sid: str, cid: str, svc: Service = Depends(service, scope="function")):
        return svc.change_json((await svc.change(sid, cid))[2])

    @app.patch("/api/v1/scopes/{sid}/changes/{cid}")
    async def edit_change(
        sid: str, cid: str, value: EditChange, svc: Service = Depends(service, scope="function")
    ):
        return await svc.edit_change(sid, cid, value)

    @app.post("/api/v1/scopes/{sid}/changes/{cid}/validate")
    async def validate(sid: str, cid: str, svc: Service = Depends(service, scope="function")):
        return await svc.validate_change(sid, cid)

    @app.post("/api/v1/scopes/{sid}/changes/{cid}/approve")
    async def approve(sid: str, cid: str, svc: Service = Depends(service, scope="function")):
        return await svc.approve_change(sid, cid)

    @app.post("/api/v1/scopes/{sid}/changes/{cid}/apply")
    async def apply(sid: str, cid: str, request: Request, svc: Service = Depends(service, scope="function")):
        return await svc.apply_change(sid, cid, request.headers.get("idempotency-key"))

    @app.post("/api/v1/scopes/{sid}/changes/{cid}/adopt")
    async def adopt(sid: str, cid: str, request: Request, svc: Service = Depends(service, scope="function")):
        return await svc.adopt(sid, cid, request.headers.get("idempotency-key"))

    @app.post("/api/v1/scopes/{sid}/creation-tasks", status_code=202)
    async def creation(sid: str, value: CreationInput, svc: Service = Depends(service, scope="function")):
        return await create_task(svc, sid, value)

    @app.get("/api/v1/scopes/{sid}/jobs")
    async def jobs(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.jobs(sid)

    @app.get("/api/v1/scopes/{sid}/jobs/{jid}")
    async def job(sid: str, jid: str, svc: Service = Depends(service, scope="function")):
        row = await svc.job(sid, jid)
        _, actions = await authorize(svc.db, svc.actor, sid)
        require(
            not row.payload.get("requires_secret") or "secret" in actions, "not_found", "任务不可访问", 404
        )
        return svc.job_json(row, details=bool({"edit", "assess"} & set(actions)))

    @app.post("/api/v1/scopes/{sid}/jobs/{jid}/intervene")
    async def intervene(
        sid: str, jid: str, value: Intervention, svc: Service = Depends(service, scope="function")
    ):
        return await svc.intervene(sid, jid, value)

    @app.post("/api/v1/scopes/{sid}/jobs/{jid}/adopt")
    async def adopt_job(
        sid: str, jid: str, request: Request, svc: Service = Depends(service, scope="function")
    ):
        return await accept_task(svc, sid, jid, request.headers.get("idempotency-key") or "author:" + jid)

    @app.post("/api/v1/scopes/{sid}/jobs/{jid}/cancel")
    async def cancel_job(sid: str, jid: str, svc: Service = Depends(service, scope="function")):
        row = await svc.job(sid, jid, "edit", lock=True)
        row.cancel_requested, row.state, row.lease_token = True, "cancelled", None
        return svc.job_json(row)

    @app.get("/api/v1/scopes/{sid}/assessments")
    async def assessments(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.assessments(sid)

    @app.post("/api/v1/scopes/{sid}/assessments/{aid}/feedback")
    async def feedback(
        sid: str, aid: str, value: FeedbackInput, svc: Service = Depends(service, scope="function")
    ):
        return await svc.feedback(sid, aid, value.choice, value.note)

    @app.post("/api/v1/scopes/{sid}/delegations", status_code=201)
    async def delegation(sid: str, value: DelegationInput, svc: Service = Depends(service, scope="function")):
        return await svc.delegation(sid, value)

    @app.get("/api/v1/scopes/{sid}/delegations")
    async def delegations(sid: str, svc: Service = Depends(service, scope="function")):
        await authorize(svc.db, svc.actor, sid, "read")
        rows = (
            await svc.db.scalars(
                select(Delegation)
                .where(Delegation.scope_id == sid, Delegation.actor_id == svc.actor.id)
                .order_by(Delegation.created_at.desc())
                .limit(100)
            )
        ).all()
        return jsonable(
            [
                {
                    "id": r.id,
                    "target_ids": r.target_ids,
                    "schemes": r.schemes,
                    "expires_at": r.expires_at,
                    "remaining": r.remaining,
                    "revoked": r.revoked,
                    "authorization": r.authorization,
                }
                for r in rows
            ]
        )

    @app.get("/api/v1/scopes/{sid}/calibrations")
    async def calibrations(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.calibrations(sid)

    @app.post("/api/v1/scopes/{sid}/calibrations")
    async def calibrate(sid: str, value: CalibrationInput, svc: Service = Depends(service, scope="function")):
        return await svc.calibrate(sid, value)

    @app.delete("/api/v1/scopes/{sid}/calibrations/{cid}")
    async def revoke_calibration(sid: str, cid: str, svc: Service = Depends(service, scope="function")):
        scope, _ = await authorize(svc.db, svc.actor, sid, "admin", lock=True)
        from .models import Calibration

        row = await svc.db.get(Calibration, cid)
        require(
            row and row.scope_id == sid and scope.owner_id == svc.actor.id,
            "not_found",
            "校准记录不可访问",
            404,
        )
        row.active = False
        svc.db.add(
            Audit(
                scope_id=sid,
                actor_id=svc.actor.id,
                action="calibration.revoke",
                version=scope.version,
                detail={"calibration_id": cid},
            )
        )
        return {"revoked": True}

    @app.get("/api/v1/scopes/{sid}/tokens")
    async def tokens(sid: str, svc: Service = Depends(service, scope="function")):
        await authorize(svc.db, svc.actor, sid, "read")
        rows = (
            await svc.db.scalars(
                select(Session).where(
                    Session.user_id == svc.actor.id,
                    Session.scope_id == sid,
                    Session.kind == "cli",
                    Session.revoked.is_(False),
                )
            )
        ).all()
        return jsonable([{"id": r.id, "expires_at": r.expires_at, "actions": r.actions} for r in rows])

    @app.delete("/api/v1/scopes/{sid}/tokens/{tid}")
    async def revoke_token(sid: str, tid: str, svc: Service = Depends(service, scope="function")):
        await authorize(svc.db, svc.actor, sid, "read")
        row = await svc.db.get(Session, tid)
        require(row and row.user_id == svc.actor.id and row.scope_id == sid, "not_found", "凭据不存在", 404)
        row.revoked = True
        return {"revoked": True}

    @app.delete("/api/v1/scopes/{sid}/delegations/{did}")
    async def revoke_delegation(sid: str, did: str, svc: Service = Depends(service, scope="function")):
        await authorize(svc.db, svc.actor, sid, "adopt", lock=True)
        row = await svc.db.get(Delegation, did)
        require(row and row.scope_id == sid and row.actor_id == svc.actor.id, "not_found", "授权不存在", 404)
        row.revoked = True
        return {"revoked": True}

    @app.post("/api/v1/scopes/{sid}/attachments", status_code=201)
    async def upload(
        sid: str, file: UploadFile = File(...), svc: Service = Depends(service, scope="function")
    ):
        data = await file.read(settings.upload_limit + 1)
        return await svc.upload(
            sid,
            file.filename or "source",
            file.content_type or "application/octet-stream",
            data,
            limit=settings.upload_limit,
        )

    @app.get("/api/v1/scopes/{sid}/attachments/{aid}")
    async def download(sid: str, aid: str, svc: Service = Depends(service, scope="function")):
        row = await svc.attachment(sid, aid)
        svc.db.add(
            Audit(
                scope_id=sid,
                actor_id=svc.actor.id,
                action="attachment.download",
                version=(await svc.scope_info(sid))["version"],
                detail={"attachment_id": aid, "digest": row.digest},
            )
        )
        return Response(
            row.data,
            media_type="application/octet-stream",
            headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(row.name, safe="")},
        )

    @app.post("/api/v1/scopes/{sid}/imports/preflight")
    async def preflight(sid: str, value: ImportInput, svc: Service = Depends(service, scope="function")):
        return await svc.preflight_import(sid, value.attachment_id, value.mapping)

    @app.get("/api/v1/scopes/{sid}/imports")
    async def imports(sid: str, svc: Service = Depends(service, scope="function")):
        await authorize(svc.db, svc.actor, sid, "edit")
        rows = (
            await svc.db.scalars(
                select(ImportRun)
                .where(ImportRun.scope_id == sid, ImportRun.actor_id == svc.actor.id)
                .order_by(ImportRun.created_at.desc())
                .limit(100)
            )
        ).all()
        return [svc.import_json(r) for r in rows]

    @app.post("/api/v1/scopes/{sid}/imports/{iid}/apply", status_code=202)
    async def apply_import(
        sid: str, iid: str, value: ImportApply, svc: Service = Depends(service, scope="function")
    ):
        return await svc.queue_import(sid, iid, value.acknowledge_unmapped)

    @app.post("/api/v1/scopes/{sid}/exports", status_code=202)
    async def export(sid: str, value: ExportInput, svc: Service = Depends(service, scope="function")):
        return await svc.queue_export(sid, value.format, value.as_of)

    @app.get("/api/v1/scopes/{sid}/members")
    async def members(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.members(sid)

    @app.post("/api/v1/scopes/{sid}/members")
    async def set_member(sid: str, value: MemberInput, svc: Service = Depends(service, scope="function")):
        return await svc.set_member(sid, value)

    @app.post("/api/v1/users", status_code=201)
    async def create_user(value: UserInput, svc: Service = Depends(service, scope="function")):
        return await svc.create_user(value.username, value.password)

    @app.post("/api/v1/scopes/{sid}/views")
    async def save_view(sid: str, value: ViewInput, svc: Service = Depends(service, scope="function")):
        return await svc.save_view(sid, value.name, value.query.model_dump(mode="json"))

    @app.get("/api/v1/scopes/{sid}/audit")
    async def audit(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.audit(sid)

    @app.get("/api/v1/scopes/{sid}/operations")
    async def operations(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.operations_status(sid)

    @app.post("/api/v1/scopes/{sid}/tokens", status_code=201)
    async def token(sid: str, value: TokenInput, svc: Service = Depends(service, scope="function")):
        _, actions = await authorize(svc.db, svc.actor, sid)
        require(
            set(value.actions) <= set(actions) and "read" in value.actions,
            "token_actions",
            "凭据不能扩大当前权限",
            403,
        )
        token_value, _ = await create_session(svc.db, svc.actor, value.hours, "cli", sid, value.actions)
        return {"token": token_value, "scope_id": sid, "actions": value.actions, "hours": value.hours}

    @app.get("/api/v1/scopes/{sid}/events")
    async def events(sid: str, request: Request):
        raw_token = request.cookies.get("ncc_session")
        async with factory() as db:
            user, _ = await authenticate(db, raw_token)
            await authorize(db, user, sid)

        async def stream():
            cursor = ""
            access_cursor = None
            for _ in range(1800):
                if await request.is_disconnected():
                    break
                async with factory() as db:
                    try:
                        user, _ = await authenticate(db, raw_token)
                        scope, actions = await authorize(db, user, sid)
                    except DomainError:
                        yield "event: access_revoked\ndata: {}\n\n"
                        return
                    current_access = ":".join(sorted(actions))
                    if current_access != access_cursor:
                        yield "event: permissions\ndata: " + json.dumps({"actions": sorted(actions)}) + "\n\n"
                    access_cursor = current_access
                    latest = await db.scalar(
                        select(func.max(Job.updated_at)).where(Job.scope_id == sid, Job.actor_id == user.id)
                    )
                    current = f"{scope.version}:{latest}"
                    if current != cursor:
                        cursor = current
                        yield (
                            "event: invalidate\ndata: "
                            + json.dumps({"version": scope.version, "cursor": cursor})
                            + "\n\n"
                        )
                    else:
                        yield ": heartbeat\n\n"
                await asyncio.sleep(2)

        return StreamingResponse(
            stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"}
        )

    @app.get("/health/live")
    async def live():
        return {"status": "alive", "version": "4.0.0"}

    @app.get("/health/ready")
    async def ready():
        try:
            async with factory() as db:
                await db.execute(text("SELECT 1 FROM alembic_version"))
            return {"status": "ready"}
        except Exception:
            return problem("not_ready", "数据库或迁移未就绪", 503)

    @app.get("/{path:path}")
    async def spa(path: str):
        if path.startswith(("api/", "health/")):
            return problem("not_found", "接口不存在", 404)
        root = settings.web_dist.resolve()
        target = (root / path).resolve()
        require(target.is_relative_to(root), "path", "无效路径", 404)
        if target.is_file():
            return FileResponse(target)
        index = root / "index.html"
        if index.is_file():
            return FileResponse(index)
        return problem("web_unbuilt", "前端尚未构建，请先运行使用指南中的构建命令", 503)

    return app
