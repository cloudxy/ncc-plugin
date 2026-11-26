"""Authenticated same-origin FastAPI application. Schema changes are an explicit CLI step."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy import select

from ncc_data.api.schemas import ExportInput, ImportApply, ImportInput
from ncc_data.application.security import (
    authorize,
)
from ncc_data.application.service import Service
from ncc_data.persistence.models import Audit, ImportRun

SAFE_INLINE_IMAGE_TYPES = frozenset({"image/png", "image/jpeg", "image/webp", "image/gif"})


def build_router(service, settings):
    router = APIRouter()

    @router.get("/api/v1/scopes/{sid}/attachments")
    async def list_attachments(
        sid: str, purpose: str = "source", svc: Service = Depends(service, scope="function")
    ):
        return await svc.list_attachments(sid, purpose=purpose)

    @router.post("/api/v1/scopes/{sid}/attachments", status_code=201)
    async def upload(
        sid: str,
        file: UploadFile = File(...),
        requires_secret: bool | None = None,
        svc: Service = Depends(service, scope="function"),
    ):
        data = await file.read(settings.upload_limit + 1)
        return await svc.upload(
            sid,
            file.filename or "source",
            file.content_type or "application/octet-stream",
            data,
            limit=settings.upload_limit,
            requires_secret=requires_secret,
        )

    @router.get("/api/v1/scopes/{sid}/attachments/{aid}")
    async def download(
        sid: str, aid: str, inline: bool = False, svc: Service = Depends(service, scope="function")
    ):
        row = await svc.attachment(sid, aid)
        encoded_name = quote(row.name, safe="")
        if row.purpose == "export":
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
                headers={
                    "Content-Disposition": "attachment; filename*=UTF-8''" + encoded_name,
                    "X-Content-Type-Options": "nosniff",
                },
            )
        clean_media = (row.media_type or "").split(";", 1)[0].strip().lower()
        if inline and clean_media in SAFE_INLINE_IMAGE_TYPES:
            return Response(
                row.data,
                media_type=clean_media,
                headers={
                    "Content-Disposition": "inline; filename*=UTF-8''" + encoded_name,
                    "X-Content-Type-Options": "nosniff",
                },
            )
        return Response(
            row.data,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename*=UTF-8''" + encoded_name,
                "X-Content-Type-Options": "nosniff",
            },
        )

    @router.post("/api/v1/scopes/{sid}/imports/preflight")
    async def preflight(sid: str, value: ImportInput, svc: Service = Depends(service, scope="function")):
        return await svc.preflight_import(sid, value.attachment_id, value.mapping)

    @router.get("/api/v1/scopes/{sid}/imports")
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

    @router.post("/api/v1/scopes/{sid}/imports/{iid}/apply", status_code=202)
    async def apply_import(
        sid: str, iid: str, value: ImportApply, svc: Service = Depends(service, scope="function")
    ):
        return await svc.queue_import(sid, iid, value.acknowledge_unmapped)

    @router.post("/api/v1/scopes/{sid}/exports", status_code=202)
    async def export(sid: str, value: ExportInput, svc: Service = Depends(service, scope="function")):
        return await svc.queue_export(
            sid,
            value.format,
            value.as_of,
            volume_id=value.volume_id,
            only_done=value.only_done,
            author=value.author,
        )

    return router
