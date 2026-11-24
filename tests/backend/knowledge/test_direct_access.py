"""Run only in the single project -test database through the common guarded fixture."""

import pytest
from sqlalchemy import select, text

from ncc_data.application.access import DataAccess
from ncc_data.application.security import create_session
from ncc_data.application.service import Service
from ncc_data.domain.contracts import ScopeInput
from ncc_data.persistence.models import Audit, Receipt, User
from ncc_data.runtime.settings import Settings
from ncc_shared.errors import DomainError


async def setup_access(store, actions=None):
    factory, ids = store
    async with factory() as db, db.begin():
        actor = await db.get(User, ids[0])
        scope = await Service(db, actor).create_scope(ScopeInput(name="直接接入合成空间"))
        token, _ = await create_session(
            db,
            actor,
            kind="cli",
            scope_id=scope["id"],
            actions=actions or ["read", "edit", "adopt", "secret"],
        )
    return (
        DataAccess(Settings(database_url="postgresql://unused/unused"), token, factory),
        scope["id"],
        factory,
    )


async def test_create_read_update_history_and_retry_are_one_business_write_path(store):
    access, scope, factory = await setup_access(store)
    original = {
        "title": "合成人物",
        "base_version": 0,
        "request_id": "direct-create-1",
        "operations": [{"op": "create", "kind": "character", "name": "合成角色", "text": "原始设定"}],
    }
    first = await access.apply(scope, original)
    assert await access.apply(scope, original) == first
    entity = await access.read("entity", scope, first["entity_ids"][0])
    assert entity["text"] == "原始设定"
    update = {
        "title": "合成修改",
        "base_version": first["version"],
        "request_id": "direct-update-1",
        "operations": [
            {"op": "update", "entity_id": entity["id"], "expected": entity["version"], "text": "更新后的设定"}
        ],
    }
    second = await access.apply(scope, update)
    assert await access.apply(scope, update) == second
    current = await access.read("entity", scope, entity["id"])
    assert current["text"] == "更新后的设定" and current["version"] != entity["version"]
    history = await access.read("history", scope, entity["id"])
    assert len(history) == 2
    old = await access.read("revision", scope, entity["id"], history[-1]["id"])
    assert old["text"] == "原始设定"
    async with factory() as db:
        receipts = (await db.scalars(select(Receipt).where(Receipt.scope_id == scope))).all()
        audits = (
            await db.scalars(select(Audit).where(Audit.scope_id == scope, Audit.action == "change.apply"))
        ).all()
        assert len(receipts) == len(audits) == 2
    update["operations"][0]["text"] = "不同内容复用请求"
    with pytest.raises(DomainError) as error:
        await access.apply(scope, update)
    assert error.value.code == "idempotency_reuse"


async def test_read_transaction_is_enforced_by_postgresql(store):
    access, scope, _ = await setup_access(store)
    status = await access.status()
    assert status["read_only"] is True and status["schema_ready"] is True
    with pytest.raises(DomainError) as error:
        async with access.transaction() as (db, _):
            await db.execute(text("UPDATE ncc_scope SET name='forbidden' WHERE id=:id"), {"id": scope})
    assert error.value.code == "database_unavailable"
    assert (await access.read("scope", scope))["name"] == "直接接入合成空间"


async def test_read_credential_cannot_write_through_direct_cli_service(store):
    access, scope, _ = await setup_access(store, ["read"])
    assert (await access.read("scope", scope))["id"] == scope
    with pytest.raises(DomainError) as error:
        await access.apply(
            scope,
            {
                "title": "forbidden",
                "base_version": 0,
                "request_id": "forbidden-create",
                "operations": [{"op": "create", "kind": "character", "name": "forbidden"}],
            },
        )
    assert error.value.code == "forbidden"
