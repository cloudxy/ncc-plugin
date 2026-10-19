"""Authenticated same-origin FastAPI application. Schema changes are an explicit CLI step."""

from fastapi import APIRouter, Depends

from ncc_data.api.schemas import WorkspaceCommit
from ncc_data.application.service import Service


def build_router(service):
    router = APIRouter()

    @router.get("/api/v1/scopes/{sid}/workspace")
    async def workspace_snapshot(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.workspace_snapshot(sid)

    @router.post("/api/v1/scopes/{sid}/workspace/commit")
    async def workspace_commit(
        sid: str, value: WorkspaceCommit, svc: Service = Depends(service, scope="function")
    ):
        return await svc.workspace_commit(sid, value.model_dump(mode="json"))

    return router
