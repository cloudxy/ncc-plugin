"""Authenticated same-origin FastAPI application. Schema changes are an explicit CLI step."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from ncc_data.api.schemas import FeedbackInput
from ncc_data.application.security import (
    authorize,
)
from ncc_data.application.service import Service
from ncc_data.creation.worker import accept_task, create_task
from ncc_data.domain.contracts import (
    AuthorDraft,
    CalibrationInput,
    CreationInput,
    DelegationInput,
    Intervention,
)
from ncc_data.persistence.models import Audit, Delegation
from ncc_shared.errors import require
from ncc_shared.serialization import jsonable


def build_router(service):
    router = APIRouter()

    @router.get("/api/v1/scopes/{sid}/author-drafts/{key}")
    async def get_draft(sid: str, key: str, svc: Service = Depends(service, scope="function")):
        return await svc.author_draft(sid, key)

    @router.put("/api/v1/scopes/{sid}/author-drafts/{key}")
    async def save_draft(
        sid: str, key: str, value: AuthorDraft, svc: Service = Depends(service, scope="function")
    ):
        return await svc.author_draft(sid, key, value)

    @router.delete("/api/v1/scopes/{sid}/author-drafts/{key}")
    async def clear_draft(
        sid: str, key: str, version: int, svc: Service = Depends(service, scope="function")
    ):
        return await svc.clear_author_draft(sid, key, version)

    @router.post("/api/v1/scopes/{sid}/creation-tasks", status_code=202)
    async def creation(sid: str, value: CreationInput, svc: Service = Depends(service, scope="function")):
        return await create_task(svc, sid, value)

    @router.get("/api/v1/scopes/{sid}/jobs")
    async def jobs(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.jobs(sid)

    @router.get("/api/v1/scopes/{sid}/jobs/{jid}")
    async def job(sid: str, jid: str, svc: Service = Depends(service, scope="function")):
        row = await svc.job(sid, jid)
        _, actions = await authorize(svc.db, svc.actor, sid)
        require(
            not row.payload.get("requires_secret") or "secret" in actions, "not_found", "任务不可访问", 404
        )
        return svc.job_json(row, details=bool({"edit", "assess"} & set(actions)))

    @router.post("/api/v1/scopes/{sid}/jobs/{jid}/intervene")
    async def intervene(
        sid: str, jid: str, value: Intervention, svc: Service = Depends(service, scope="function")
    ):
        return await svc.intervene(sid, jid, value)

    @router.post("/api/v1/scopes/{sid}/jobs/{jid}/adopt")
    async def adopt_job(
        sid: str, jid: str, request: Request, svc: Service = Depends(service, scope="function")
    ):
        return await accept_task(svc, sid, jid, request.headers.get("idempotency-key") or "author:" + jid)

    @router.post("/api/v1/scopes/{sid}/jobs/{jid}/cancel")
    async def cancel_job(sid: str, jid: str, svc: Service = Depends(service, scope="function")):
        row = await svc.job(sid, jid, "edit", lock=True)
        row.cancel_requested, row.state, row.lease_token = True, "cancelled", None
        return svc.job_json(row)

    @router.get("/api/v1/scopes/{sid}/assessments")
    async def assessments(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.assessments(sid)

    @router.post("/api/v1/scopes/{sid}/assessments/{aid}/feedback")
    async def feedback(
        sid: str, aid: str, value: FeedbackInput, svc: Service = Depends(service, scope="function")
    ):
        return await svc.feedback(sid, aid, value.choice, value.note)

    @router.post("/api/v1/scopes/{sid}/delegations", status_code=201)
    async def delegation(sid: str, value: DelegationInput, svc: Service = Depends(service, scope="function")):
        return await svc.delegation(sid, value)

    @router.get("/api/v1/scopes/{sid}/delegations")
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

    @router.get("/api/v1/scopes/{sid}/calibrations")
    async def calibrations(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.calibrations(sid)

    @router.post("/api/v1/scopes/{sid}/calibrations")
    async def calibrate(sid: str, value: CalibrationInput, svc: Service = Depends(service, scope="function")):
        return await svc.calibrate(sid, value)

    @router.delete("/api/v1/scopes/{sid}/calibrations/{cid}")
    async def revoke_calibration(sid: str, cid: str, svc: Service = Depends(service, scope="function")):
        scope, _ = await authorize(svc.db, svc.actor, sid, "admin", lock=True)
        from ncc_data.persistence.models import Calibration

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

    @router.delete("/api/v1/scopes/{sid}/delegations/{did}")
    async def revoke_delegation(sid: str, did: str, svc: Service = Depends(service, scope="function")):
        await authorize(svc.db, svc.actor, sid, "adopt", lock=True)
        row = await svc.db.get(Delegation, did)
        require(row and row.scope_id == sid and row.actor_id == svc.actor.id, "not_found", "授权不存在", 404)
        row.revoked = True
        return {"revoked": True}

    return router
