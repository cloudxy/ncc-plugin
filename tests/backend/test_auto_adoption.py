"""Author trial is real bounded execution, never synthetic calibration evidence."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from ncc_data.application.service import Service
from ncc_data.creation.worker import Worker, accept_task, create_task
from ncc_data.domain.contracts import CreationInput, DelegationInput, MemberInput, ScopeInput
from ncc_data.persistence.models import Audit, Calibration, Delegation, User, utcnow
from ncc_data.runtime.settings import Settings
from ncc_shared.errors import DomainError
from tests.backend.test_api_automation import FixtureProvider
from tests.backend.test_core import create
from tests.backend.test_scoring import report


async def setup(store, mode="author_trial", position=4):
    factory, ids = store
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        sid = (await svc.create_scope(ScopeInput(name="自动定稿合成验证")))["id"]
        target = await create(svc, sid, "第四章", "chapter", text="灯下的选择。", data={"position": position})
        delegation = await svc.delegation(
            sid,
            DelegationInput(
                target_ids=[target["id"]],
                schemes=["P1"],
                count=1,
                mode=mode,
                note="合成测试中的作者授权；不是人工校准数据。",
            ),
        )
        job = await create_task(
            svc,
            sid,
            CreationInput(objective="合成修订", entity_id=target["id"], delegation_id=delegation["id"]),
        )
    return factory, ids, sid, target, delegation, job


async def run(factory, provider=None, **settings):
    worker = Worker(
        factory, Settings(database_url="unused", **settings), provider or FixtureProvider(scores=(4.5,))
    )
    for _ in range(3):
        await worker.run_once()


async def test_trial_adopts_once_and_keeps_calibration_unverified(store):
    factory, ids, sid, target, delegation, job = await setup(store)
    await run(factory)
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        row = await svc.job(sid, job["id"])
        assert row.state == "applied", row.result
        assert row.result["automatic_adoption"]["calibration"] == "unverified"
        assert (await svc.entity(sid, target["id"]))["version"] != target["version"]
        assert (await db.get(Delegation, delegation["id"])).remaining == 0
        assert await db.scalar(select(func.count()).select_from(Calibration)) == 0
        assert (
            await db.scalar(
                select(func.count()).select_from(Audit).where(Audit.action == "creation.auto_adopt")
            )
            == 1
        )
        assert await accept_task(svc, sid, job["id"], "retry", automatic=True) == row.result["receipt"]
        assert (await db.get(Delegation, delegation["id"])).remaining == 0
        with pytest.raises(DomainError, match="托管授权"):
            await create_task(
                svc,
                sid,
                CreationInput(objective="超出次数", entity_id=target["id"], delegation_id=delegation["id"]),
            )


async def test_calibrated_mode_still_requires_real_calibration(store):
    factory, ids, sid, _, delegation, job = await setup(store, mode="calibrated")
    await run(factory)
    async with factory() as db, db.begin():
        row = await Service(db, await db.get(User, ids[0])).job(sid, job["id"])
        assert row.state == "qualified" and row.result["auto_hold"]["code"] == "calibration"
        assert (await db.get(Delegation, delegation["id"])).remaining == 1


@pytest.mark.parametrize(
    "change,code", [("revoked", "delegation"), ("expired", "delegation"), ("policy", "delegation_policy")]
)
async def test_trial_rechecks_revocation_expiry_and_policy(store, change, code):
    factory, ids, sid, target, delegation, job = await setup(store)
    async with factory() as db, db.begin():
        row = await db.get(Delegation, delegation["id"])
        if change == "revoked":
            row.revoked = True
        elif change == "expired":
            row.expires_at = utcnow() - timedelta(seconds=1)
        else:
            row.authorization = {**row.authorization, "policy_hash": "changed"}
    await run(factory)
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        row = await svc.job(sid, job["id"])
        assert row.state == "qualified" and row.result["auto_hold"]["code"] == code
        assert (await svc.entity(sid, target["id"]))["version"] == target["version"]
        assert (await db.get(Delegation, delegation["id"])).remaining == 1


async def test_trial_keeps_opening_and_quality_gates(store):
    factory, ids, sid, target, _, job = await setup(store, position=2)
    await run(factory)
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        row = await svc.job(sid, job["id"])
        assert row.state == "qualified" and row.result["auto_hold"]["code"] == "key_chapter"
        assert (await svc.entity(sid, target["id"]))["version"] == target["version"]


async def test_trial_secondary_judge_must_also_qualify(store):
    class Secondary(FixtureProvider):
        async def call(self, purpose, packet, budget):
            if purpose == "judge_secondary":
                return report("P1", 4), {"tokens": 50, "kind": "fixture"}
            return await super().call(purpose, packet, budget)

    factory, ids, sid, _, _, job = await setup(store)
    await run(factory, Secondary(scores=(4.5,)), second_judge_model="fixture:second")
    async with factory() as db, db.begin():
        row = await Service(db, await db.get(User, ids[0])).job(sid, job["id"])
        assert row.state != "applied"
        assert row.result["auto_hold"]["code"] == "quality"


async def test_trial_requires_owner_and_explicit_note(store):
    factory, ids, sid, target, _, _ = await setup(store)
    async with factory() as db, db.begin():
        owner = Service(db, await db.get(User, ids[0]))
        await owner.set_member(sid, MemberInput(user_id=ids[1], actions=["read", "edit", "assess", "adopt"]))
        with pytest.raises(DomainError, match="授权依据"):
            await owner.delegation(
                sid, DelegationInput(target_ids=[target["id"]], schemes=["P1"], mode="author_trial")
            )
        member = Service(db, await db.get(User, ids[1]))
        with pytest.raises(DomainError) as exc:
            await member.delegation(
                sid,
                DelegationInput(
                    target_ids=[target["id"]], schemes=["P1"], mode="author_trial", note="不是所有者"
                ),
            )
        assert exc.value.code == "owner_only"


async def test_p5_uses_target_content_scheme_without_unrelated_authority(store):
    factory, ids = store
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        sid = (await svc.create_scope(ScopeInput(name="人物修改合成验证")))["id"]
        target = await create(svc, sid, "人物", text="灯下的选择。")
        delegation = await svc.delegation(
            sid,
            DelegationInput(
                target_ids=[target["id"]], schemes=["P3", "P5"], mode="author_trial", note="合成人物修改授权"
            ),
        )
        job = await create_task(
            svc,
            sid,
            CreationInput(
                objective="修改人物", scheme="P5", entity_id=target["id"], delegation_id=delegation["id"]
            ),
        )
        assert job["payload"]["content_scheme"] == "P3"
        assert job["payload"]["kind"] == "character"
    await run(factory)
    async with factory() as db, db.begin():
        row = await Service(db, await db.get(User, ids[0])).job(sid, job["id"])
        assert row.state == "applied", row.result
        assert row.result["candidates"][-1]["scheme"] == "P3"


async def test_legacy_delegation_needs_policy_bound_renewal(store):
    factory, ids, sid, _, delegation, job = await setup(store, mode="calibrated")
    async with factory() as db, db.begin():
        (await db.get(Delegation, delegation["id"])).authorization = {}
    await run(factory)
    async with factory() as db, db.begin():
        row = await Service(db, await db.get(User, ids[0])).job(sid, job["id"])
        assert row.result["auto_hold"]["code"] == "delegation_policy"
