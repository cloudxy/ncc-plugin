import httpx
import pytest

from ncc_data.api.app import create_app
from ncc_data.application.service import Service
from ncc_data.creation.worker import Worker, accept_task, create_task
from ncc_data.domain.contracts import CreationInput, Intervention, ScopeInput
from ncc_data.persistence.models import User
from ncc_data.runtime.settings import Settings
from tests.backend.test_scoring import report


class FixtureProvider:
    """Only a test double: never shipped as an application provider or a score-quality claim."""

    identity = "fixture:judge"

    def __init__(self, scores=(3.5, 4.5)):
        self.scores, self.judgements = scores, 0

    async def call(self, purpose, packet, budget):
        if purpose == "judge":
            from ncc_shared.quality.policy import POLICY

            scheme = next(key for key, rubric in POLICY["profiles"].items() if rubric == packet["rubric"])
            score = 4.5 if scheme == "P2" else self.scores[min(self.judgements, len(self.scores) - 1)]
            if scheme == "P1":
                self.judgements += 1
            result = report(scheme, score)
        else:
            result = {"text": "灯下的选择。少年放下剑，决定救人。", "data": {}, "claims": []}
        return result, {"tokens": 100, "kind": "fixture", "model": "fixture"}


async def test_login_csrf_scope_and_cli_token(store):
    factory, _ = store
    settings = Settings(database_url="unused", public_origin="http://testserver")
    app = create_app(settings, factory)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/scopes")).status_code == 401
        response = await client.post(
            "/api/v1/auth/login",
            headers={"x-ncc-client": "console"},
            json={"username": "author", "password": "test-author-password"},
        )
        assert response.status_code == 200, response.text
        csrf = response.json()["csrf"]
        assert (await client.post("/api/v1/scopes", json={"name": "测试书"})).status_code == 403
        headers = {"x-csrf-token": csrf}
        response = await client.post("/api/v1/scopes", headers=headers, json={"name": "测试书"})
        assert response.status_code == 201, response.text
        sid = response.json()["id"]
        assert (
            await client.post(
                "/api/v1/scopes",
                headers={**headers, "origin": "https://untrusted.invalid"},
                json={"name": "x"},
            )
        ).status_code == 403
        token = (
            await client.post(
                f"/api/v1/scopes/{sid}/tokens", headers=headers, json={"actions": ["read"], "hours": 1}
            )
        ).json()["token"]
        bearer = {"authorization": "Bearer " + token}
        assert (await client.get(f"/api/v1/scopes/{sid}", headers=bearer)).status_code == 200
        denied = await client.post(
            f"/api/v1/scopes/{sid}/changes",
            headers=bearer,
            json={
                "title": "不能提权",
                "base_version": 0,
                "operations": [{"op": "create", "kind": "item", "name": "x"}],
            },
        )
        assert denied.status_code == 403, denied.text
        assert (await client.post("/api/v1/auth/logout", headers=headers, json={})).status_code == 200
        assert (await client.get("/api/v1/scopes")).status_code == 401


async def test_durable_revision_and_author_adoption(store):
    factory, ids = store
    async with factory() as db, db.begin():
        service = Service(db, await db.get(User, ids[0]))
        sid = (await service.create_scope(ScopeInput(name="自动化书")))["id"]
        job = await create_task(
            service, sid, CreationInput(objective="合成续写", kind="chapter", scheme="P1", name="第一章")
        )
        jid = job["id"]
    worker = Worker(factory, Settings(database_url="unused"), FixtureProvider())
    assert await worker.run_once()
    async with factory() as db, db.begin():
        service = Service(db, await db.get(User, ids[0]))
        job = await service.job(sid, jid)
        assert job.state == "qualified", job.result
        assert len(job.result["candidates"]) == 2
        assert job.progress["revisions"] == 1
        receipt = await accept_task(service, sid, jid, "pick-once")
        assert receipt["version"] == 1
        assert (await service.entities(sid))["items"][0]["name"] == "第一章"
        assert await accept_task(service, sid, jid, "pick-once") == receipt


async def test_generation_does_not_overwrite_intervention(store):
    factory, ids = store
    async with factory() as db, db.begin():
        service = Service(db, await db.get(User, ids[0]))
        sid = (await service.create_scope(ScopeInput(name="接管书")))["id"]
        job = await create_task(service, sid, CreationInput(objective="测试"))
        jid = job["id"]
    worker = Worker(factory, Settings(database_url="unused"), FixtureProvider())
    claimed = await worker.claim()
    async with factory() as db, db.begin():
        service = Service(db, await db.get(User, ids[0]))
        await service.intervene(sid, jid, Intervention(action="pause"))
    from ncc_shared.errors import DomainError

    async with factory() as db, db.begin():
        with pytest.raises(DomainError) as exc:
            await worker.fenced(db, *claimed)
        assert exc.value.code == "lease_lost"
