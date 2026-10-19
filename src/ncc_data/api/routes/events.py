"""Authenticated same-origin FastAPI application. Schema changes are an explicit CLI step."""

import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from ncc_data.application.security import (
    authenticate,
    authorize,
)
from ncc_data.persistence.models import Job
from ncc_shared.errors import DomainError


def build_router(factory):
    router = APIRouter()

    @router.get("/api/v1/scopes/{sid}/events")
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

    return router
