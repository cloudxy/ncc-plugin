"""Authenticated same-origin FastAPI application. Schema changes are an explicit CLI step."""

from fastapi import APIRouter, Depends
from sqlalchemy import select

from ncc_data.api.schemas import TokenInput
from ncc_data.application.security import (
    authorize,
    create_session,
)
from ncc_data.application.service import Service
from ncc_data.domain.contracts import (
    MemberInput,
    UserInput,
)
from ncc_data.persistence.models import Session
from ncc_shared.errors import require
from ncc_shared.serialization import jsonable


def build_router(service):
    router = APIRouter()

    @router.get("/api/v1/scopes/{sid}/tokens")
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

    @router.delete("/api/v1/scopes/{sid}/tokens/{tid}")
    async def revoke_token(sid: str, tid: str, svc: Service = Depends(service, scope="function")):
        await authorize(svc.db, svc.actor, sid, "read")
        row = await svc.db.get(Session, tid)
        require(row and row.user_id == svc.actor.id and row.scope_id == sid, "not_found", "凭据不存在", 404)
        row.revoked = True
        return {"revoked": True}

    @router.get("/api/v1/scopes/{sid}/members")
    async def members(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.members(sid)

    @router.post("/api/v1/scopes/{sid}/members")
    async def set_member(sid: str, value: MemberInput, svc: Service = Depends(service, scope="function")):
        return await svc.set_member(sid, value)

    @router.post("/api/v1/users", status_code=201)
    async def create_user(value: UserInput, svc: Service = Depends(service, scope="function")):
        return await svc.create_user(value.username, value.password)

    @router.get("/api/v1/scopes/{sid}/audit")
    async def audit(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.audit(sid)

    @router.get("/api/v1/scopes/{sid}/operations")
    async def operations(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.operations_status(sid)

    @router.post("/api/v1/scopes/{sid}/tokens", status_code=201)
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

    return router
