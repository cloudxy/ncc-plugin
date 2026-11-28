"""Global model registry and unified 6-capability defaults on the system scope.

No secret values are written. External CLI probes and HTTP connectivity checks NEVER run
while holding PostgreSQL FOR UPDATE row locks.
"""

import asyncio
import shutil
import subprocess
from pathlib import Path

import httpx
from sqlalchemy import select

from ncc_data.creation.model_route import (
    _check_url,
    active_registry,
    apply_capability_default,
    apply_configuration,
    apply_default,
    apply_delete,
    apply_enabled,
    clean_capability_defaults,
    connection,
    describe,
    materialize_one,
    normalize_configuration,
    snapshot_from,
    writable_registry,
)
from ncc_data.creation.subscription_auth import collect_subscriptions, verify_channel
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
        "capabilities": list(row.get("capabilities") or ["text"]),
        "purposes": list(row["purposes"]),
        "enabled": bool(row["enabled"]),
        "auth_ref": row["auth_ref"],
        "supplier": row["supplier"],
        "platform_id": row.get("platform_id", "custom"),
        "transport": row.get("transport", "http"),
        "cli_provider": row.get("cli_provider", ""),
    }


async def _precollect_subscriptions(db, scope_id: str, settings) -> dict:
    """Collect read-only subscription status BEFORE acquiring any FOR UPDATE lock."""
    scope = await db.get(Scope, scope_id)
    config = scope.config if scope is not None and isinstance(scope.config, dict) else {}
    saved_sub = config.get("subscription_auth") if isinstance(config.get("subscription_auth"), dict) else {}
    home = getattr(settings, "cli_home", None)
    which = getattr(settings, "cli_which", None) or shutil.which
    run = getattr(settings, "cli_run", None) or subprocess.run
    return await asyncio.to_thread(
        collect_subscriptions,
        saved_sub,
        Path(home) if home else None,
        which,
        run,
    )


async def _persist(svc, scope, settings, registry, action, detail, *, capability_defaults=None, subscription_view=None):
    """Pure locked DB write + in-memory view assembly; zero external I/O or CLI subprocesses inside lock."""
    config = dict(scope.config or {})
    config["model_registry"] = registry
    if capability_defaults is not None:
        config["capability_defaults"] = capability_defaults
    else:
        config["capability_defaults"] = clean_capability_defaults(config, registry)
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
    return describe(config, settings, subscription_view=subscription_view)


async def load_model_settings(svc, settings, *, scope_id: str = SYSTEM_SCOPE):
    _guard(svc.actor)
    sub_view = await _precollect_subscriptions(svc.db, scope_id, settings)
    scope = await svc.db.get(Scope, scope_id)
    return describe(scope.config if scope else None, settings, subscription_view=sub_view)


async def save_configuration(svc, settings, value, *, scope_id: str = SYSTEM_SCOPE):
    _guard(svc.actor)
    fields = normalize_configuration(value)
    sub_view = await _precollect_subscriptions(svc.db, scope_id, settings)
    scope = await _system_scope(svc.db, scope_id=scope_id, lock=True)
    registry = writable_registry(scope.config)
    existing = value.id or ""
    new_id = "" if existing else uid()
    registry = apply_configuration(registry, fields, existing or None, new_id)
    saved_id = existing or new_id
    row = next(item for item in registry["configurations"] if item["id"] == saved_id)
    view = await _persist(
        svc,
        scope,
        settings,
        registry,
        "model_registry.save",
        _detail(row),
        subscription_view=sub_view,
    )
    view["saved_id"] = saved_id
    return view


async def set_configuration_enabled(svc, settings, cid, enabled, *, scope_id: str = SYSTEM_SCOPE):
    _guard(svc.actor)
    sub_view = await _precollect_subscriptions(svc.db, scope_id, settings)
    scope = await _system_scope(svc.db, scope_id=scope_id, lock=True)
    registry = apply_enabled(writable_registry(scope.config), cid, enabled)
    row = next(item for item in registry["configurations"] if item["id"] == cid)
    return await _persist(
        svc,
        scope,
        settings,
        registry,
        "model_registry.enabled",
        _detail(row),
        subscription_view=sub_view,
    )


async def bind_default(svc, settings, value, *, scope_id: str = SYSTEM_SCOPE):
    _guard(svc.actor)
    sub_view = await _precollect_subscriptions(svc.db, scope_id, settings)
    scope = await _system_scope(svc.db, scope_id=scope_id, lock=True)
    registry = apply_default(writable_registry(scope.config), value.purpose, value.configuration_id)
    return await _persist(
        svc,
        scope,
        settings,
        registry,
        "model_registry.default",
        {"purpose": value.purpose, "configuration_id": registry["defaults"].get(value.purpose, "")},
        subscription_view=sub_view,
    )


async def bind_capability_default(svc, settings, value, *, scope_id: str = SYSTEM_SCOPE):
    _guard(svc.actor)
    sub_view = await _precollect_subscriptions(svc.db, scope_id, settings)
    scope = await _system_scope(svc.db, scope_id=scope_id, lock=True)
    registry = writable_registry(scope.config)
    current_caps = clean_capability_defaults(scope.config, registry)
    updated_caps = apply_capability_default(registry, current_caps, value)
    entry = updated_caps.get(value.capability)
    detail = {
        "capability": value.capability,
        "source": entry.get("source", "") if isinstance(entry, dict) else "",
        "configuration_id": entry.get("configuration_id", "") if isinstance(entry, dict) else "",
        "provider": entry.get("provider", "") if isinstance(entry, dict) else "",
        "model_key": entry.get("model_key", "") if isinstance(entry, dict) else "",
    }
    return await _persist(
        svc,
        scope,
        settings,
        registry,
        "model_registry.capability_default",
        detail,
        capability_defaults=updated_caps,
        subscription_view=sub_view,
    )


async def delete_configuration(svc, settings, cid, *, scope_id: str = SYSTEM_SCOPE):
    _guard(svc.actor)
    sub_view = await _precollect_subscriptions(svc.db, scope_id, settings)
    scope = await _system_scope(svc.db, scope_id=scope_id, lock=True)
    current, _ = active_registry(scope.config)
    row = next((item for item in current["configurations"] if item["id"] == cid), None)
    require(row is not None, "not_found", "模型配置不存在", 404)
    registry = apply_delete(writable_registry(scope.config), cid)
    return await _persist(
        svc,
        scope,
        settings,
        registry,
        "model_registry.delete",
        _detail(row),
        subscription_view=sub_view,
    )


async def check_configuration(
    svc, settings, cid, *, live: bool = False, scope_id: str = SYSTEM_SCOPE, transport=None
):
    """Read-only configuration check or live connectivity probe (zero row locks, no paid generation)."""
    _guard(svc.actor)
    scope = await svc.db.get(Scope, scope_id)
    registry, _ = active_registry(scope.config if scope else None)
    row = next((item for item in registry["configurations"] if item["id"] == cid), None)
    require(row is not None, "not_found", "模型配置不存在", 404)
    conn = await asyncio.to_thread(connection, row, settings)
    if row.get("transport") == "cli_oauth":
        if not live:
            return {
                "id": cid,
                "ok": conn["status"] == "loaded",
                "message": conn["message"],
                "mode": "config",
                "connection": conn,
            }
        provider = row.get("cli_provider") or ""
        home = getattr(settings, "cli_home", None) or Path.home()
        which = getattr(settings, "cli_which", None) or shutil.which
        run = getattr(settings, "cli_run", None) or subprocess.run
        verified = await asyncio.to_thread(verify_channel, provider, Path(home), which, run)
        ok = bool(verified.get("ready"))
        live_conn = {
            "status": "loaded" if ok else "not_configured",
            "credential": "present" if ok else "absent",
            "message": verified.get("message") or conn["message"],
        }
        return {
            "id": cid,
            "ok": ok,
            "message": verified.get("message") or conn["message"],
            "mode": "live",
            "status_code": None,
            "model_found": True if ok else None,
            "connection": live_conn,
        }
    if not live:
        return {
            "id": cid,
            "ok": conn["status"] == "loaded",
            "message": conn["message"],
            "mode": "config",
            "connection": conn,
        }
    if conn["status"] != "loaded":
        return {
            "id": cid,
            "ok": False,
            "message": conn["message"],
            "mode": "live",
            "status_code": None,
            "model_found": None,
            "connection": conn,
        }
    route = materialize_one(row, settings)
    _check_url(route.base_url)
    headers = {"Authorization": f"Bearer {route.api_key}"} if route.api_key else {}
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=False, transport=transport) as client:
            response = await client.get(f"{route.base_url}/models", headers=headers)
    except httpx.HTTPError:
        return {
            "id": cid,
            "ok": False,
            "message": "无法连接模型网关，请检查地址与本机网络（未发起生成请求，密钥未回传）。",
            "mode": "live",
            "status_code": None,
            "model_found": None,
            "connection": conn,
        }
    if response.status_code == 200:
        model_found: bool | None = None
        try:
            if len(response.content) <= 2 * 1024 * 1024:
                payload = response.json()
                if isinstance(payload, dict) and isinstance(payload.get("data"), list):
                    ids = {
                        str(item.get("id")).strip()
                        for item in payload["data"]
                        if isinstance(item, dict) and item.get("id") is not None
                    }
                    model_found = route.model in ids
        except ValueError:
            model_found = None
        if model_found is True:
            msg = f"网关连通正常（HTTP 200），已确认远端模型列表包含 {route.model}。"
        elif model_found is False:
            msg = f"网关连通正常（HTTP 200），但 /models 列表中未见 {route.model}，请核对模型标识。"
        else:
            msg = "网关连通正常（HTTP 200）。未发起付费生成请求，密钥未回传。"
        return {
            "id": cid,
            "ok": True,
            "message": msg,
            "mode": "live",
            "status_code": 200,
            "model_found": model_found,
            "connection": conn,
        }
    if response.status_code in {401, 403}:
        return {
            "id": cid,
            "ok": False,
            "message": (
                f"网关鉴权未通过（HTTP {response.status_code}），"
                f"请检查环境变量 {row['auth_ref']} 中的密钥是否有效。"
            ),
            "mode": "live",
            "status_code": response.status_code,
            "model_found": None,
            "connection": conn,
        }
    return {
        "id": cid,
        "ok": False,
        "message": f"网关返回 HTTP {response.status_code}（未发起生成请求，密钥未回传）。",
        "mode": "live",
        "status_code": response.status_code,
        "model_found": None,
        "connection": conn,
    }


async def snapshot_model_route(db, settings, *, scope_id: str = SYSTEM_SCOPE) -> dict:
    scope = await db.get(Scope, scope_id)
    return snapshot_from(scope.config if scope else None, settings)
