"""Authenticated same-origin FastAPI application. Schema changes are an explicit CLI step."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from ncc_data.api.schemas import TokenInput
from ncc_data.application.model_settings import (
    bind_capability_default,
    bind_default,
    check_configuration,
    delete_configuration,
    load_model_settings,
    save_configuration,
    set_configuration_enabled,
)
from ncc_data.application.security import (
    authorize,
    create_session,
)
from ncc_data.application.service import Service
from ncc_data.application.subscription_settings import (
    cancel_subscription_login,
    load_single_subscription,
    load_subscriptions,
    poll_subscription_login,
    save_subscription_model,
    start_subscription_login,
    verify_subscription,
)
from ncc_data.domain.contracts import (
    CapabilityDefaultInput,
    MemberInput,
    ModelConfigurationInput,
    ModelDefaultInput,
    ModelEnabledInput,
    SubscriptionModelInput,
    UserInput,
    UserUpdateInput,
)
from ncc_data.persistence.models import Audit, Session
from ncc_shared.errors import require
from ncc_shared.serialization import jsonable


def build_router(service, settings):
    router = APIRouter()

    @router.get("/api/v1/model-settings")
    async def model_settings(svc: Service = Depends(service, scope="function")):
        return await load_model_settings(svc, settings)

    @router.post("/api/v1/model-settings/configurations")
    async def post_configuration(value: ModelConfigurationInput, svc: Service = Depends(service, scope="function")):
        return await save_configuration(svc, settings, value)

    @router.post("/api/v1/model-settings/configurations/{cid}/enabled")
    async def post_configuration_enabled(
        cid: str, value: ModelEnabledInput, svc: Service = Depends(service, scope="function")
    ):
        return await set_configuration_enabled(svc, settings, cid, value.enabled)

    @router.post("/api/v1/model-settings/configurations/{cid}/check")
    async def post_configuration_check(
        cid: str, live: bool = False, svc: Service = Depends(service, scope="function")
    ):
        return await check_configuration(svc, settings, cid, live=live)

    @router.post("/api/v1/model-settings/defaults")
    async def post_default(value: ModelDefaultInput, svc: Service = Depends(service, scope="function")):
        return await bind_default(svc, settings, value)

    @router.post("/api/v1/model-settings/capability-defaults")
    async def post_capability_default(
        value: CapabilityDefaultInput, svc: Service = Depends(service, scope="function")
    ):
        return await bind_capability_default(svc, settings, value)

    @router.delete("/api/v1/model-settings/configurations/{cid}")
    async def remove_configuration(cid: str, svc: Service = Depends(service, scope="function")):
        return await delete_configuration(svc, settings, cid)

    @router.get("/api/v1/model-settings/subscriptions")
    async def subscriptions(svc: Service = Depends(service, scope="function")):
        return await load_subscriptions(svc)

    @router.get("/api/v1/model-settings/subscriptions/{provider}")
    async def subscription_single(provider: str, svc: Service = Depends(service, scope="function")):
        return await load_single_subscription(svc, provider)

    @router.post("/api/v1/model-settings/subscriptions/{provider}/verify")
    async def subscription_verify(provider: str, svc: Service = Depends(service, scope="function")):
        return await verify_subscription(svc, provider)

    @router.post("/api/v1/model-settings/subscriptions/{provider}/login")
    async def subscription_login(provider: str, svc: Service = Depends(service, scope="function")):
        return await start_subscription_login(svc, provider)

    @router.get("/api/v1/model-settings/subscriptions/{provider}/login/{session_id}")
    async def subscription_login_status(
        provider: str, session_id: str, svc: Service = Depends(service, scope="function")
    ):
        return await poll_subscription_login(svc, provider, session_id)

    @router.delete("/api/v1/model-settings/subscriptions/{provider}/login/{session_id}")
    async def subscription_login_cancel(
        provider: str, session_id: str, svc: Service = Depends(service, scope="function")
    ):
        return await cancel_subscription_login(svc, provider, session_id)

    @router.post("/api/v1/model-settings/subscriptions/{provider}/model")
    async def subscription_model(
        provider: str, value: SubscriptionModelInput, svc: Service = Depends(service, scope="function")
    ):
        return await save_subscription_model(
            svc,
            provider,
            value.model,
            text_model=value.text_model,
            image_model=value.image_model,
        )

    @router.get("/api/v1/scopes/{sid}/tokens")
    async def tokens(sid: str, svc: Service = Depends(service, scope="function")):
        await authorize(svc.db, svc.actor, sid, "read")
        rows = (
            await svc.db.scalars(
                select(Session).where(
                    Session.user_id == svc.actor.id,
                    Session.scope_id == sid,
                    Session.kind == "cli",
                    Session.revoked.is_(False),
                )
            )
        ).all()
        return jsonable([{"id": r.id, "expires_at": r.expires_at, "actions": r.actions} for r in rows])

    @router.delete("/api/v1/scopes/{sid}/tokens/{tid}")
    async def revoke_token(sid: str, tid: str, svc: Service = Depends(service, scope="function")):
        scope, _ = await authorize(svc.db, svc.actor, sid, "read")
        row = await svc.db.get(Session, tid)
        require(row and row.user_id == svc.actor.id and row.scope_id == sid, "not_found", "凭据不存在", 404)
        row.revoked = True
        svc.db.add(
            Audit(
                scope_id=sid,
                actor_id=svc.actor.id,
                action="token.revoke",
                version=scope.version,
                detail={"token_id": tid},
            )
        )
        return {"revoked": True}

    @router.get("/api/v1/scopes/{sid}/members")
    async def members(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.members(sid)

    @router.post("/api/v1/scopes/{sid}/members")
    async def set_member(sid: str, value: MemberInput, svc: Service = Depends(service, scope="function")):
        return await svc.set_member(sid, value)

    @router.delete("/api/v1/scopes/{sid}/members/{uid}")
    async def remove_member(sid: str, uid: str, svc: Service = Depends(service, scope="function")):
        return await svc.remove_member(sid, uid)

    @router.get("/api/v1/users")
    async def list_users(svc: Service = Depends(service, scope="function")):
        return await svc.list_users()

    @router.get("/api/v1/users/directory")
    async def user_directory(q: str = "", svc: Service = Depends(service, scope="function")):
        return await svc.user_directory(q=q)

    @router.post("/api/v1/users", status_code=201)
    async def create_user(value: UserInput, svc: Service = Depends(service, scope="function")):
        return await svc.create_user(value.username, value.password)

    @router.patch("/api/v1/users/{uid}")
    async def update_user(uid: str, value: UserUpdateInput, svc: Service = Depends(service, scope="function")):
        return await svc.update_user(uid, value)

    @router.get("/api/v1/scopes/{sid}/audit")
    async def audit(
        sid: str,
        action: str | None = None,
        actor_id: str | None = None,
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0, le=100_000),
        svc: Service = Depends(service, scope="function"),
    ):
        return await svc.audit(sid, action=action, actor_id=actor_id, limit=limit, offset=offset)

    @router.get("/api/v1/scopes/{sid}/operations")
    async def operations(sid: str, svc: Service = Depends(service, scope="function")):
        return await svc.operations_status(sid)

    @router.post("/api/v1/scopes/{sid}/tokens", status_code=201)
    async def token(sid: str, value: TokenInput, svc: Service = Depends(service, scope="function")):
        scope, actions = await authorize(svc.db, svc.actor, sid)
        require(
            set(value.actions) <= set(actions) and "read" in value.actions,
            "token_actions",
            "凭据不能扩大当前权限",
            403,
        )
        token_value, _ = await create_session(svc.db, svc.actor, value.hours, "cli", sid, value.actions)
        svc.db.add(
            Audit(
                scope_id=sid,
                actor_id=svc.actor.id,
                action="token.create",
                version=scope.version,
                detail={"actions": sorted(set(value.actions)), "hours": value.hours},
            )
        )
        return {"token": token_value, "scope_id": sid, "actions": value.actions, "hours": value.hours}

    return router
