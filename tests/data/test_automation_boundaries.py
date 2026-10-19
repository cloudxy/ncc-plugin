import pytest

from ncc_data.automation import Worker, accept_task, create_task
from ncc_data.config import Settings
from ncc_data.contracts import AuthorDraft, CalibrationInput, CreationInput, ScopeInput
from ncc_data.errors import DomainError
from ncc_data.models import User
from ncc_data.service import Service
from tests.data.test_api_automation import FixtureProvider
from tests.data.test_core import create
from tests.data.test_scoring import report


async def setup(store, **kwargs):
    factory, ids = store
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        sid = (await svc.create_scope(ScopeInput(name="边界验证")))["id"]
        target = await create(
            svc, sid, "第四章", "chapter", text="前段。灯下的选择。后段。", data={"position": 4}
        )
        job = await create_task(
            svc, sid, CreationInput(objective="仅修改选段", entity_id=target["id"], **kwargs)
        )
    return factory, ids, sid, target, job


async def test_assess_only_never_rewrites(store):
    factory, ids, sid, target, job = await setup(store, mode="assess")
    worker = Worker(factory, Settings(database_url="unused"), FixtureProvider())
    for _ in range(2):
        await worker.run_once()
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        row = await svc.job(sid, job["id"])
        assert row.state == "succeeded"
        assert row.result["candidates"][0]["evaluation"]["score"] == "70.0"
        assert (await svc.entity(sid, target["id"]))["content_hash"] == target["content_hash"]
        with pytest.raises(DomainError, match="单独评分"):
            await accept_task(svc, sid, job["id"], "cannot-adopt")


async def test_human_autosave_fences_inflight_call(store):
    factory, ids, sid, target, job = await setup(store)
    worker = Worker(factory, Settings(database_url="unused"), FixtureProvider())
    claim = await worker.claim()
    # Index jobs may precede the creation; explicitly lease its creation task.
    while claim[0] != job["id"]:
        async with factory() as db, db.begin():
            row, _ = await worker.fenced(db, *claim)
            row.state = "succeeded"
        claim = await worker.claim()
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        draft = await svc.author_draft(
            sid,
            target["id"],
            AuthorDraft(
                version=0,
                entity_id=target["id"],
                baseline=target["version"],
                name=target["name"],
                text="作者改写的草稿",
            ),
        )
        assert draft["version"] == 1
        with pytest.raises(DomainError):
            await svc.clear_author_draft(sid, target["id"], 0)
        assert (await svc.author_draft(sid, target["id"]))["text"] == "作者改写的草稿"
        await svc.clear_author_draft(sid, target["id"], 1)
        assert "text" not in await svc.author_draft(sid, target["id"])
        assert (await svc.job(sid, job["id"])).state == "paused"
    async with factory() as db, db.begin():
        with pytest.raises(DomainError) as exc:
            await worker.fenced(db, *claim)
        assert exc.value.code == "lease_lost"


async def test_revision_budget_and_selection_scope(store):
    factory, ids, sid, target, job = await setup(store, scheme="P5", selection_start=3, selection_end=9)
    worker = Worker(factory, Settings(database_url="unused"), FixtureProvider(scores=(4.5,)))
    for _ in range(2):
        await worker.run_once()
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        row = await svc.job(sid, job["id"])
        assert row.state == "qualified", row.result
        candidate = row.result["candidates"][-1]
        assert candidate["text"].startswith(target["text"][:3])
        assert candidate["text"].endswith(target["text"][9:])
        assert candidate["scheme"] == "P1"
        assert candidate["revision_evaluation"]["score"] == "90.0"


async def test_second_judge_disagreement_blocks_adoption(store):
    class Disagree(FixtureProvider):
        async def call(self, purpose, packet, budget):
            if purpose == "judge_secondary":
                return report("P1", 2), {"tokens": 50, "kind": "fixture"}
            return await super().call(purpose, packet, budget)

    factory, ids, sid, _, job = await setup(store)
    worker = Worker(
        factory, Settings(database_url="unused", second_judge_model="fixture:second"), Disagree(scores=(4.5,))
    )
    for _ in range(2):
        await worker.run_once()
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        row = await svc.job(sid, job["id"])
        assert row.state == "waiting" and row.result["candidates"][-1]["disputed"]
        with pytest.raises(DomainError):
            await accept_task(svc, sid, job["id"], "disputed")


async def test_low_score_stops_after_two_revisions(store):
    factory, ids, sid, _, job = await setup(store)
    worker = Worker(factory, Settings(database_url="unused"), FixtureProvider(scores=(2,)))
    for _ in range(2):
        await worker.run_once()
    async with factory() as db, db.begin():
        row = await Service(db, await db.get(User, ids[0])).job(sid, job["id"])
        assert row.state == "waiting" and row.progress["revisions"] == 2
        assert len(row.result["candidates"]) == 3


async def test_calibration_sample_shortage_cannot_activate(store):
    factory, ids, sid, _, job = await setup(store, mode="assess")
    for _ in range(2):
        await Worker(factory, Settings(database_url="unused"), FixtureProvider(scores=(4.5,))).run_once()
    async with factory() as db, db.begin():
        svc = Service(db, await db.get(User, ids[0]))
        row = await svc.job(sid, job["id"])
        aid = row.result["candidates"][0]["assessment_id"]
        result = await svc.calibrate(
            sid,
            CalibrationInput(
                scheme="P1",
                evaluator="fixture:judge",
                activate=True,
                note="合成测试：单样本不应获信任",
                samples=[{"source_group": "one", "split": "holdout", "assessment_ids": [aid]}],
            ),
        )
        assert not result["active"] and not result["report"]["sample_sufficient"]
