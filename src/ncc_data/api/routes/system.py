"""Authenticated same-origin FastAPI application. Schema changes are an explicit CLI step."""

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import text

from ncc_data.api.problems import problem
from ncc_data.application.service import Service
from ncc_shared.errors import require


def build_router(app, service, settings, factory):
    router = APIRouter()

    @router.get("/api/v1/openapi.json")
    async def openapi(svc: Service = Depends(service, scope="function")):
        return app.openapi()

    @router.get("/health/live")
    async def live():
        return {"status": "alive", "version": "4.0.0", "profile": settings.profile}

    @router.get("/health/ready")
    async def ready():
        try:
            async with factory() as db:
                await db.execute(text("SELECT 1 FROM alembic_version"))
            return {"status": "ready"}
        except Exception:
            return problem("not_ready", "数据库或迁移未就绪", 503)

    @router.get("/{path:path}")
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

    return router
