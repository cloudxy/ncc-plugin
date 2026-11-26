"""Subscription preferences on the system scope. CLI tokens are not stored or returned."""

import asyncio
import shutil
import subprocess
from pathlib import Path

from sqlalchemy import select

from ncc_data.creation.subscription_auth import (
    cancel_oauth_login,
    collect_subscriptions,
    normalize_model,
    poll_oauth_login,
    start_oauth_login,
    verify_channel,
)
from ncc_data.domain.definitions import SYSTEM_SCOPE
from ncc_data.persistence.models import Audit, Scope
from ncc_shared.errors import require


def _guard(actor):
    require(getattr(actor, "admin", False), "administrator", "模型配置需要系统管理员", 403)
    require(not hasattr(actor, "_access_scope"), "scoped_credential", "范围凭据不能修改模型配置", 403)


def _saved(scope):
    raw = (scope.config or {}).get("subscription_auth") if scope is not None else None
    return raw if isinstance(raw, dict) else {}


async def load_subscriptions(svc):
    _guard(svc.actor)
    scope = await svc.db.get(Scope, SYSTEM_SCOPE)
    saved = _saved(scope)
    return await asyncio.to_thread(collect_subscriptions, saved)


async def verify_subscription(svc, provider: str):
    _guard(svc.actor)
    scope = await svc.db.get(Scope, SYSTEM_SCOPE)
    status = await asyncio.to_thread(verify_channel, provider, Path.home(), shutil.which, subprocess.run)
    if scope is not None:
        svc.db.add(
            Audit(
                scope_id=scope.id,
                actor_id=svc.actor.id,
                action="subscription_auth.verify",
                version=scope.version,
                detail={"provider": provider, "status": status.get("status"), "ready": bool(status.get("ready"))},
            )
        )
        await svc.db.flush()
    view = await load_subscriptions(svc)
    for row in view["channels"]:
        if row["id"] == provider:
            row["status"] = status
    view["ready_count"] = sum(1 for row in view["channels"] if row["status"]["ready"])
    return view


async def start_subscription_login(svc, provider: str):
    _guard(svc.actor)
    scope = await svc.db.get(Scope, SYSTEM_SCOPE)
    saved = _saved(scope)
    result = await start_oauth_login(provider, saved=saved)
    if scope is not None:
        svc.db.add(
            Audit(
                scope_id=scope.id,
                actor_id=svc.actor.id,
                action="subscription_auth.login",
                version=scope.version,
                detail={
                    "provider": provider,
                    "mode": result.get("mode"),
                    "started": bool(result.get("started")),
                    "state": result.get("state"),
                },
            )
        )
        await svc.db.flush()
    return result


async def poll_subscription_login(svc, provider: str, session_id: str):
    _guard(svc.actor)
    scope = await svc.db.get(Scope, SYSTEM_SCOPE)
    saved = _saved(scope)
    return await poll_oauth_login(provider, session_id, saved=saved)


async def cancel_subscription_login(svc, provider: str, session_id: str):
    _guard(svc.actor)
    scope = await svc.db.get(Scope, SYSTEM_SCOPE)
    result = await cancel_oauth_login(provider, session_id)
    if scope is not None:
        svc.db.add(
            Audit(
                scope_id=scope.id,
                actor_id=svc.actor.id,
                action="subscription_auth.login_cancel",
                version=scope.version,
                detail={"provider": provider, "session_id": session_id},
            )
        )
        await svc.db.flush()
    return result


async def save_subscription_model(svc, provider: str, model: str, *, scope_id: str = SYSTEM_SCOPE):
    _guard(svc.actor)
    chosen = normalize_model(provider, model)
    scope = await svc.db.scalar(
        select(Scope)
        .where(Scope.id == scope_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    require(scope is not None, "subscription", "系统定义范围不存在，订阅偏好未保存", 409)
    config = dict(scope.config or {})
    current = dict(_saved(scope))
    current[provider] = {"model": chosen}
    config["subscription_auth"] = current
    scope.config = config
    svc.db.add(
        Audit(
            scope_id=scope.id,
            actor_id=svc.actor.id,
            action="subscription_auth.model",
            version=scope.version,
            detail={"provider": provider, "model": chosen},
        )
    )
    await svc.db.flush()
    return await asyncio.to_thread(collect_subscriptions, current)
