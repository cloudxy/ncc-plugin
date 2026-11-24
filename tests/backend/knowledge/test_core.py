import asyncio
from decimal import Decimal

import pytest

from ncc_data.application.knowledge.changes import ChangeService
from ncc_data.domain.contracts import ChangeInput, Query, ScopeInput, StateQuery
from ncc_data.persistence.models import User
from ncc_shared.errors import DomainError


async def commit(service, scope, operations, title="合成变更"):
    info = await service.scope_info(scope)
    change = await service.create_change(
        scope, ChangeInput(title=title, base_version=info["version"], operations=operations)
    )
    await service.adopt(scope, change["id"], change["id"])
    return change


async def create(service, scope, name="合成人物", kind="character", **extra):
    change = await commit(service, scope, [{"op": "create", "kind": kind, "name": name, **extra}])
    return await service.entity(scope, change["operations"][0]["entity_id"])


async def test_types_versions_history_and_branch(author):
    scope = (await author.create_scope(ScopeInput(name="合成书")))["id"]
    await commit(
        author,
        scope,
        [
            {
                "op": "definition",
                "definition": {
                    "key": "异火样本",
                    "version": 1,
                    "spec": {
                        "label": "异火",
                        "properties": {"rank": {"type": "integer", "minimum": 1}},
                        "required": ["rank"],
                    },
                },
            }
        ],
    )
    item = await create(author, scope, "青火", "异火样本", data={"rank": 2})
    pin = (await author.scope_info(scope))["version"]
    branch = (await author.create_scope(ScopeInput(name="IF线", kind="branch", base_id=scope)))["id"]
    await commit(
        author,
        branch,
        [{"op": "update", "entity_id": item["id"], "expected": item["version"], "data": {"rank": 5}}],
    )
    assert (await author.entity(branch, item["id"]))["data"]["rank"] == 5
    assert (await author.entity(scope, item["id"]))["data"]["rank"] == 2
    await commit(
        author,
        scope,
        [{"op": "update", "entity_id": item["id"], "expected": item["version"], "data": {"rank": 3}}],
    )
    assert (await author.entity(scope, item["id"], Query(as_of=pin)))["data"]["rank"] == 2
    assert len(await author.history(scope, item["id"])) == 2


async def test_validation_rollback_and_unknown_attributes(author):
    sid = (await author.create_scope(ScopeInput(name="校验书")))["id"]
    change = await author.create_change(
        sid,
        ChangeInput(
            title="错误批次",
            base_version=0,
            operations=[
                {"op": "create", "kind": "character", "name": "甲"},
                {"op": "create", "kind": "item", "name": "乙", "data": {"undefined": "不能丢弃"}},
            ],
        ),
    )
    result = await author.validate_change(sid, change["id"])
    assert not result["validation"]["valid"]
    assert result["validation"]["errors"][0]["code"] == "unknown_attribute"
    assert (await author.entities(sid))["items"] == []
    assert (await author.scope_info(sid))["version"] == 0


async def test_temporal_ownership_retcon_and_belief(author):
    sid = (await author.create_scope(ScopeInput(name="时间书")))["id"]
    a, b, sword = [
        await create(author, sid, name, kind)
        for name, kind in [("甲", "character"), ("乙", "character"), ("剑", "item")]
    ]
    await commit(
        author,
        sid,
        [
            {
                "op": "fact",
                "entity_id": a["id"],
                "fact": {
                    "predicate": "owns",
                    "category": "relation",
                    "object_id": sword["id"],
                    "calendar": "天元",
                    "world_from": "10",
                    "world_to": "20",
                    "source": {"kind": "author"},
                },
            }
        ],
    )
    await commit(
        author,
        sid,
        [
            {
                "op": "fact",
                "entity_id": b["id"],
                "fact": {
                    "predicate": "owns",
                    "category": "relation",
                    "object_id": sword["id"],
                    "calendar": "天元",
                    "world_from": "20",
                    "source": {"kind": "author"},
                },
            }
        ],
    )
    old_version = (await author.scope_info(sid))["version"]
    at15 = await author.facts(sid, StateQuery(predicate="owns", calendar="天元", world_at=Decimal(15)))
    assert [f["subject_id"] for f in at15["items"]] == [a["id"]]
    assert [
        f["subject_id"]
        for f in (
            await author.facts(sid, StateQuery(predicate="owns", calendar="天元", world_at=Decimal(20)))
        )["items"]
    ] == [b["id"]]
    original = at15["items"][0]
    await commit(
        author,
        sid,
        [
            {
                "op": "fact",
                "entity_id": a["id"],
                "fact": {
                    "predicate": "owns",
                    "category": "relation",
                    "object_id": sword["id"],
                    "calendar": "天元",
                    "world_from": "12",
                    "world_to": "20",
                    "supersedes": original["id"],
                    "source": {"kind": "author", "note": "追溯修正"},
                },
            }
        ],
    )
    assert not (await author.facts(sid, StateQuery(predicate="owns", calendar="天元", world_at=Decimal(11))))[
        "items"
    ]
    assert (
        await author.facts(
            sid, StateQuery(predicate="owns", as_of=old_version, calendar="天元", world_at=Decimal(11))
        )
    )["items"]
    await commit(
        author,
        sid,
        [
            {
                "op": "fact",
                "entity_id": a["id"],
                "fact": {
                    "predicate": "belief",
                    "category": "belief",
                    "value": {
                        "stance": "misbelieves",
                        "proposition": "剑仍归我",
                        "truth": False,
                        "attitude": "denies",
                    },
                    "source": {"kind": "author"},
                },
            }
        ],
    )
    assert (await author.facts(sid, StateQuery(category="belief")))["items"][0]["value"][
        "stance"
    ] == "misbelieves"


async def test_cas_idempotency_scope_isolation(store):
    factory, (actor_id, other_id) = store
    async with factory() as db, db.begin():
        actor = await db.get(User, actor_id)
        service = ChangeService(db, actor)
        sid = (await service.create_scope(ScopeInput(name="并发书")))["id"]
        a = await service.create_change(
            sid,
            ChangeInput(
                title="a", base_version=0, operations=[{"op": "create", "kind": "item", "name": "a"}]
            ),
        )
        b = await service.create_change(
            sid,
            ChangeInput(
                title="b", base_version=0, operations=[{"op": "create", "kind": "item", "name": "b"}]
            ),
        )
        aid, bid = a["id"], b["id"]

    async def apply(cid):
        async with factory() as db, db.begin():
            service = ChangeService(db, await db.get(User, actor_id))
            try:
                return await service.adopt(sid, cid, cid)
            except DomainError as exc:
                return exc.code

    results = await asyncio.gather(apply(aid), apply(bid))
    assert sum(isinstance(r, dict) for r in results) == 1
    async with factory() as db, db.begin():
        service = ChangeService(db, await db.get(User, actor_id))
        win = aid if isinstance(results[0], dict) else bid
        first = await service.apply_change(sid, win, win)
        again = await service.apply_change(sid, win, win)
        assert first == again
        outsider = ChangeService(db, await db.get(User, other_id))
        with pytest.raises(DomainError) as err:
            await outsider.entities(sid)
        assert err.value.status == 404


async def test_cjk_search_precision_and_chapter_reorder(author):
    sid = (await author.create_scope(ScopeInput(name="检索书")))["id"]
    obj = await create(
        author,
        sid,
        "青云宗",
        "organization",
        data={"amount": "900719925474099312345.0001", "rate": {"numerator": "1", "denominator": "3"}},
    )
    assert (await author.entities(sid, Query(q="青云")))["items"][0]["id"] == obj["id"]
    assert (await author.entity(sid, obj["id"]))["data"]["amount"] == "900719925474099312345.0001"
    chapter = await create(author, sid, "第一章", "chapter", data={"position": 1}, text="原文证据")
    await commit(
        author,
        sid,
        [
            {
                "op": "update",
                "entity_id": chapter["id"],
                "expected": chapter["version"],
                "data": {"position": 2},
            }
        ],
    )
    current = await author.entity(sid, chapter["id"])
    assert current["id"] == chapter["id"] and current["text"] == "原文证据"
