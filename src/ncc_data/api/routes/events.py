"""Authenticated same-origin FastAPI application. Schema changes are an explicit CLI step."""

import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from ncc_data.application.security import (
    authenticate,
    authorize,
    credential_change_policy,
)
from ncc_data.persistence.models import Job
from ncc_shared.errors import DomainError, require

CREDENTIAL_CHANGE_REQUIRED_DETAIL = (
    "当前通过真实地址访问且正在使用默认管理员账号，请先修改账号和密码后再继续使用"
)


def build_router(factory, settings=None, bind_host=None):
    router = APIRouter()

    @router.get("/api/v1/scopes/{sid}/events")
    async def events(sid: str, request: Request):
        raw_token = request.cookies.get("ncc_session")
        async with factory() as db:
            user, _ = await authenticate(db, raw_token)
            _, enforced, _ = credential_change_policy(request, settings, user, bind_host=bind_host)
            require(not enforced, "credential_change_required", CREDENTIAL_CHANGE_REQUIRED_DETAIL, 403)
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
                        _, enforced, _ = credential_change_policy(
                            request, settings, user, bind_host=bind_host
                        )
                        require(
                            not enforced,
                            "credential_change_required",
                            CREDENTIAL_CHANGE_REQUIRED_DETAIL,
                            403,
                        )
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

    return router
