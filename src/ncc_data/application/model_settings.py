"""Global model registry on the existing system scope. No secret values are written."""

from sqlalchemy import select

from ncc_data.creation.model_route import (
    active_registry,
    apply_configuration,
    apply_default,
    apply_delete,
    apply_enabled,
    connection,
    describe,
    normalize_configuration,
    snapshot_from,
    writable_registry,
)
from ncc_data.domain.definitions import SYSTEM_SCOPE
from ncc_data.persistence.models import Audit, Scope, uid
from ncc_shared.errors import require


def _guard(actor):
    require(getattr(actor, "admin", False), "administrator", "模型配置需要系统管理员", 403)
    require(not hasattr(actor, "_access_scope"), "scoped_credential", "范围凭据不能修改模型配置", 403)


async def _system_scope(db, scope_id: str = SYSTEM_SCOPE, *, lock: bool = True):
    stmt = select(Scope).where(Scope.id == scope_id).execution_options(populate_existing=True)
    if lock:
        stmt = stmt.with_for_update()
    scope = await db.scalar(stmt)
    require(scope is not None, "model_registry", "系统定义范围不存在，模型配置未保存", 409)
    return scope


def _detail(row) -> dict:
    return {
        "name": row["name"],
        "model_key": row["model_key"],
        "purposes": list(row["purposes"]),
        "enabled": bool(row["enabled"]),
        "auth_ref": row["auth_ref"],
        "supplier": row["supplier"],
    }


async def _persist(svc, scope, settings, registry, action, detail):
    config = dict(scope.config or {})
    config["model_registry"] = registry
    scope.config = config
    svc.db.add(
        Audit(
            scope_id=scope.id,
            actor_id=svc.actor.id,
            action=action,
            version=scope.version,
            detail=detail,
        )
    )
    await svc.db.flush()
    view = describe(config, settings)
    return view


async def load_model_settings(svc, settings, *, scope_id: str = SYSTEM_SCOPE):
    _guard(svc.actor)
    scope = await svc.db.get(Scope, scope_id)
    return describe(scope.config if scope else None, settings)


async def save_configuration(svc, settings, value, *, scope_id: str = SYSTEM_SCOPE):
    _guard(svc.actor)
    fields = normalize_configuration(value)
    scope = await _system_scope(svc.db, scope_id=scope_id, lock=True)
    registry = writable_registry(scope.config)
    existing = value.id or ""
    new_id = "" if existing else uid()
    registry = apply_configuration(registry, fields, existing or None, new_id)
    saved_id = existing or new_id
    row = next(item for item in registry["configurations"] if item["id"] == saved_id)
    view = await _persist(svc, scope, settings, registry, "model_registry.save", _detail(row))
    view["saved_id"] = saved_id
    return view


async def set_configuration_enabled(svc, settings, cid, enabled, *, scope_id: str = SYSTEM_SCOPE):
    _guard(svc.actor)
    scope = await _system_scope(svc.db, scope_id=scope_id, lock=True)
    registry = apply_enabled(writable_registry(scope.config), cid, enabled)
    row = next(item for item in registry["configurations"] if item["id"] == cid)
    return await _persist(svc, scope, settings, registry, "model_registry.enabled", _detail(row))


async def bind_default(svc, settings, value, *, scope_id: str = SYSTEM_SCOPE):
    _guard(svc.actor)
    scope = await _system_scope(svc.db, scope_id=scope_id, lock=True)
    registry = apply_default(writable_registry(scope.config), value.purpose, value.configuration_id)
    return await _persist(
        svc,
        scope,
        settings,
        registry,
        "model_registry.default",
        {"purpose": value.purpose, "configuration_id": registry["defaults"].get(value.purpose, "")},
    )


async def delete_configuration(svc, settings, cid, *, scope_id: str = SYSTEM_SCOPE):
    _guard(svc.actor)
    scope = await _system_scope(svc.db, scope_id=scope_id, lock=True)
    current, _ = active_registry(scope.config)
    row = next((item for item in current["configurations"] if item["id"] == cid), None)
    require(row is not None, "not_found", "模型配置不存在", 404)
    registry = apply_delete(writable_registry(scope.config), cid)
    return await _persist(svc, scope, settings, registry, "model_registry.delete", _detail(row))


async def check_configuration(svc, settings, cid, *, scope_id: str = SYSTEM_SCOPE):
    _guard(svc.actor)
    scope = await svc.db.get(Scope, scope_id)
    registry, _ = active_registry(scope.config if scope else None)
    row = next((item for item in registry["configurations"] if item["id"] == cid), None)
    require(row is not None, "not_found", "模型配置不存在", 404)
    return {"id": cid, "connection": connection(row, settings)}


async def snapshot_model_route(db, settings, *, scope_id: str = SYSTEM_SCOPE) -> dict:
    scope = await db.get(Scope, scope_id)
    return snapshot_from(scope.config if scope else None, settings)
