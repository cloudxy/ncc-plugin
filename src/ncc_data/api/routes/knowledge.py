"""Authenticated same-origin FastAPI application. Schema changes are an explicit CLI step."""

from fastapi import APIRouter, Depends, Request

from ncc_data.api.schemas import ViewInput
from ncc_data.application.service import Service
from ncc_data.domain.contracts import (
    ChangeInput,
    EditChange,
    MaintenanceInput,
    Query,
    ScopeInput,
    StateQuery,
)
from ncc_data.domain.creation import REVISION_SCHEMES, SCHEME_LABELS
from ncc_shared.errors import require
from ncc_shared.quality.policy import POLICY, POLICY_HASH


def build_router(service):
    router = APIRouter()

    @router.get("/api/v1/policy")
    async def policy(svc: Service = Depends(service, scope="function")):
        return {
            **POLICY,
            "hash": POLICY_HASH,
            "scheme_labels": SCHEME_LABELS,
            "revision_schemes": REVISION_SCHEMES,
        }

    @router.get("/api/v1/scopes")
    async def scopes(svc: Service = Depends(service, scope="function")):
        return await svc.scopes()

    @router.post("/api/v1/scopes", status_code=201)
    async def create_scope(value: ScopeInput, svc: Service = Depends(service, scope="function")):
        require(not hasattr(svc.actor, "_access_scope"), "scoped_credential", "范围凭据不能创建其他范围", 403)
        return await svc.create_scope(value)

    @router.get("/api/v1/scopes/{sid}")
    async def scope_info(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.scope_info(sid)

    @router.get("/api/v1/scopes/{sid}/definitions")
    async def definitions(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.definitions(sid)

    @router.post("/api/v1/scopes/{sid}/entities/search")
    async def entities(sid: str, value: Query, svc: Service = Depends(service, scope="function")):
        return await svc.entities(sid, value)

    @router.get("/api/v1/scopes/{sid}/entities/{eid}")
    async def entity(
        sid: str,
        eid: str,
        as_of: int | None = None,
        include_deleted: bool = False,
        svc: Service = Depends(service, scope="function"),
    ):
        return await svc.entity(sid, eid, Query(as_of=as_of, include_deleted=include_deleted))

    @router.get("/api/v1/scopes/{sid}/entities/{eid}/history")
    async def history(sid: str, eid: str, svc: Service = Depends(service, scope="function")):
        return await svc.history(sid, eid)

    @router.get("/api/v1/scopes/{sid}/entities/{eid}/revisions/{rid}")
    async def revision(sid: str, eid: str, rid: str, svc: Service = Depends(service, scope="function")):
        return await svc.revision(sid, eid, rid)

    @router.post("/api/v1/scopes/{sid}/state/query")
    async def facts(sid: str, value: StateQuery, svc: Service = Depends(service, scope="function")):
        return await svc.facts(sid, value)

    @router.get("/api/v1/scopes/{sid}/graph/{eid}")
    async def graph(sid: str, eid: str, hops: int = 2, svc: Service = Depends(service, scope="function")):
        return await svc.graph(sid, eid, hops)

    @router.get("/api/v1/scopes/{sid}/quality")
    async def quality(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.quality(sid)

    @router.post("/api/v1/scopes/{sid}/maintenance/plan")
    async def maintenance(
        sid: str, value: MaintenanceInput, svc: Service = Depends(service, scope="function")
    ):
        return await svc.maintenance_plan(sid, value)

    @router.get("/api/v1/scopes/{sid}/changes")
    async def changes(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.changes(sid)

    @router.post("/api/v1/scopes/{sid}/changes", status_code=201)
    async def create_change(sid: str, value: ChangeInput, svc: Service = Depends(service, scope="function")):
        return await svc.create_change(sid, value)

    @router.get("/api/v1/scopes/{sid}/changes/{cid}")
    async def change(sid: str, cid: str, svc: Service = Depends(service, scope="function")):
        return svc.change_json((await svc.change(sid, cid))[2])

    @router.patch("/api/v1/scopes/{sid}/changes/{cid}")
    async def edit_change(
        sid: str, cid: str, value: EditChange, svc: Service = Depends(service, scope="function")
    ):
        return await svc.edit_change(sid, cid, value)

    @router.post("/api/v1/scopes/{sid}/changes/{cid}/validate")
    async def validate(sid: str, cid: str, svc: Service = Depends(service, scope="function")):
        return await svc.validate_change(sid, cid)

    @router.post("/api/v1/scopes/{sid}/changes/{cid}/approve")
    async def approve(sid: str, cid: str, svc: Service = Depends(service, scope="function")):
        return await svc.approve_change(sid, cid)

    @router.post("/api/v1/scopes/{sid}/changes/{cid}/apply")
    async def apply(sid: str, cid: str, request: Request, svc: Service = Depends(service, scope="function")):
        return await svc.apply_change(sid, cid, request.headers.get("idempotency-key"))

    @router.post("/api/v1/scopes/{sid}/changes/{cid}/adopt")
    async def adopt(sid: str, cid: str, request: Request, svc: Service = Depends(service, scope="function")):
        return await svc.adopt(sid, cid, request.headers.get("idempotency-key"))

    @router.post("/api/v1/scopes/{sid}/views")
    async def save_view(sid: str, value: ViewInput, svc: Service = Depends(service, scope="function")):
        return await svc.save_view(sid, value.name, value.query.model_dump(mode="json"))

    return router
