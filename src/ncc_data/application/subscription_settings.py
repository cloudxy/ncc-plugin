"""Subscription preferences on the system scope.

CLI tokens are never stored or returned. External CLI probes NEVER run while holding
PostgreSQL FOR UPDATE row locks.
"""

import asyncio
import shutil
import subprocess
from pathlib import Path

from sqlalchemy import select

from ncc_data.creation.subscription_auth import (
    cancel_oauth_login,
    channel,
    collect_single_subscription,
    collect_subscriptions,
    is_known_image_model,
    normalize_model,
    poll_oauth_login,
    saved_image_model,
    saved_text_model,
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


async def load_single_subscription(svc, provider: str):
    _guard(svc.actor)
    channel(provider)
    scope = await svc.db.get(Scope, SYSTEM_SCOPE)
    saved = _saved(scope)
    return await asyncio.to_thread(collect_single_subscription, provider, saved)


async def verify_subscription(svc, provider: str):
    """Run one-shot online CLI verification without row-locking Scope or persisting stale cross-account flags."""
    _guard(svc.actor)
    channel(provider)
    status = await asyncio.to_thread(verify_channel, provider, Path.home(), shutil.which, subprocess.run)
    verified_now = bool(status.get("ready") and status.get("verified"))
    scope = await svc.db.get(Scope, SYSTEM_SCOPE)
    if scope is not None:
        svc.db.add(
            Audit(
                scope_id=scope.id,
                actor_id=svc.actor.id,
                action="subscription_auth.verify",
                version=scope.version,
                detail={
                    "provider": provider,
                    "status": status.get("status"),
                    "ready": bool(status.get("ready")),
                    "verified": verified_now,
                },
            )
        )
        await svc.db.flush()
    view = await load_subscriptions(svc)
    for row in view["channels"]:
        if row["id"] == provider:
            row["status"] = status
            row["verified"] = verified_now
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


async def save_subscription_model(
    svc,
    provider: str,
    model: str | None = None,
    *,
    text_model: str | None = None,
    image_model: str | None = None,
    scope_id: str = SYSTEM_SCOPE,
):
    _guard(svc.actor)
    require(
        model is not None or text_model is not None or image_model is not None,
        "model",
        "文本模型与图片模型至少提供一项",
    )
    chosen_legacy = normalize_model(provider, model) if model is not None else None
    chosen_text = normalize_model(provider, text_model) if text_model is not None else None
    chosen_image = normalize_model(provider, image_model) if image_model is not None else None

    # Pre-collect subscription probe statuses BEFORE acquiring FOR UPDATE row lock.
    scope_ro = await svc.db.get(Scope, scope_id) if hasattr(svc.db, "get") else None
    pre_view = await asyncio.to_thread(collect_subscriptions, _saved(scope_ro))

    scope = await svc.db.scalar(
        select(Scope)
        .where(Scope.id == scope_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    require(scope is not None, "subscription", "系统定义范围不存在，订阅偏好未保存", 409)
    config = dict(scope.config or {})
    current = dict(_saved(scope))
    next_text = saved_text_model(current, provider)
    next_image = saved_image_model(current, provider)
    legacy_model = next_text
    if chosen_legacy is not None:
        if is_known_image_model(provider, chosen_legacy):
            next_image = chosen_legacy
        else:
            next_text = chosen_legacy
        legacy_model = chosen_legacy
    if chosen_text is not None:
        next_text = chosen_text
        legacy_model = chosen_text
    if chosen_image is not None:
        next_image = chosen_image
        if chosen_text is None and chosen_legacy is None:
            legacy_model = next_text
    current[provider] = {
        "model": legacy_model,
        "text_model": next_text,
        "image_model": next_image,
    }
    config["subscription_auth"] = current
    scope.config = config
    svc.db.add(
        Audit(
            scope_id=scope.id,
            actor_id=svc.actor.id,
            action="subscription_auth.model",
            version=scope.version,
            detail={
                "provider": provider,
                "model": legacy_model,
                "text_model": next_text,
                "image_model": next_image,
            },
        )
    )
    await svc.db.flush()
    for row in pre_view["channels"]:
        if row["id"] == provider:
            row["text_model"] = next_text
            row["image_model"] = next_image
            row["model"] = next_text
    return pre_view
