"""Authenticated direct PostgreSQL access shared by read-only MCP and the full CLI."""

from contextlib import asynccontextmanager

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from ncc_data.application.security import authenticate, authorize
from ncc_data.application.service import Service
from ncc_data.domain.access import DirectChange
from ncc_data.domain.contracts import ChangeInput, Query, StateQuery
from ncc_data.persistence.database import database
from ncc_data.persistence.models import Receipt
from ncc_shared.errors import DomainError, require
from ncc_shared.serialization import digest, jsonable

READ_OPERATIONS = frozenset(
    {"scopes", "scope", "definitions", "search", "entity", "facts", "history", "revision"}
)


class DataAccess:
    def __init__(self, settings, token="", factory=None):
        self.settings, self.token = settings, token
        self.engine = None
        if factory is None:
            try:
                self.engine, factory = database(settings.database_url)
            except SQLAlchemyError:
                raise DomainError(
                    "database_configuration", "数据库连接配置无效；连接凭据不会输出", 503
                ) from None
        self.factory = factory

    async def close(self):
        if self.engine is not None:
            await self.engine.dispose()

    @asynccontextmanager
    async def transaction(self, readonly=True, authenticated=True):
        if authenticated:
            require(
                bool(self.token),
                "credential_required",
                "请在config/.env配置范围凭据NCC_API_TOKEN；MCP可使用专用NCC_MCP_TOKEN",
                401,
            )
        try:
            async with self.factory() as db, db.begin():
                if readonly:
                    await db.execute(text("SET TRANSACTION READ ONLY"))
                await db.execute(text("SET LOCAL statement_timeout = '15000ms'"))
                actor = None
                if authenticated:
                    actor, session = await authenticate(db, self.token)
                    require(session.kind == "cli", "credential_kind", "直接数据操作必须使用独立范围凭据", 403)
                yield db, Service(db, actor) if actor else None
        except SQLAlchemyError:
            raise DomainError(
                "database_unavailable",
                "数据库连接或操作失败，请核查既定连接、迁移状态与权限；连接凭据不会输出",
                503,
            ) from None

    async def status(self):
        async with self.transaction(authenticated=False) as (db, _):
            row = (
                await db.execute(
                    text(
                        "SELECT current_database(), current_setting('transaction_read_only'), to_regclass('public.ncc_scope') IS NOT NULL"
                    )
                )
            ).one()
            return {
                "configured": True,
                "connected": True,
                "database": row[0],
                "read_only": row[1] == "on",
                "schema_ready": row[2],
                "profile": self.settings.profile,
            }

    async def read(self, operation, scope_id=None, entity_id=None, revision_id=None, query=None):
        require(operation in READ_OPERATIONS, "read_operation", "此通道仅支持已登记的读取操作")
        require(operation == "scopes" or bool(scope_id), "scope_required", "读取需要明确作品/资料范围")
        if operation in {"entity", "history", "revision"}:
            require(bool(entity_id), "entity_required", "读取需要对象ID")
        if operation == "revision":
            require(bool(revision_id), "revision_required", "读取需要修订ID")
        parsed = (StateQuery if operation == "facts" else Query).model_validate(query or {})
        async with self.transaction() as (_, service):
            if operation == "scopes":
                result = await service.scopes()
            elif operation == "scope":
                result = await service.scope_info(scope_id)
            elif operation == "definitions":
                result = await service.definitions(scope_id)
            elif operation == "search":
                result = await service.entities(scope_id, parsed)
            elif operation == "entity":
                result = await service.entity(scope_id, entity_id, parsed)
            elif operation == "facts":
                result = await service.facts(scope_id, parsed)
            elif operation == "history":
                result = await service.history(scope_id, entity_id)
            else:
                result = await service.revision(scope_id, entity_id, revision_id)
            return jsonable(result)

    async def apply(self, scope_id, payload):
        value = DirectChange.model_validate(payload)
        original_hash = digest(value.model_dump(mode="json", exclude={"request_id"}))
        async with self.transaction(readonly=False) as (db, service):
            await authorize(db, service.actor, scope_id, "adopt", lock=True)
            await authorize(db, service.actor, scope_id, "edit")
            previous = await db.scalar(
                select(Receipt).where(
                    Receipt.scope_id == scope_id,
                    Receipt.actor_id == service.actor.id,
                    Receipt.key == value.request_id,
                )
            )
            if previous is not None:
                require(
                    previous.result.get("direct_input_hash") == original_hash,
                    "idempotency_reuse",
                    "同一请求ID不能用于不同变更",
                    409,
                )
                await service.change(scope_id, previous.result["change_id"], "adopt")
                return jsonable(previous.result)
            change = await service.create_change(
                scope_id, ChangeInput.model_validate(value.model_dump(exclude={"request_id"}))
            )
            result = await service.adopt(scope_id, change["id"], value.request_id)
            receipt = await db.scalar(
                select(Receipt).where(
                    Receipt.scope_id == scope_id,
                    Receipt.actor_id == service.actor.id,
                    Receipt.key == value.request_id,
                )
            )
            result = {
                **result,
                "request_id": value.request_id,
                "direct_input_hash": original_hash,
                "entity_ids": [op["entity_id"] for op in change["operations"] if op.get("entity_id")],
            }
            receipt.result = result
            return jsonable(result)
