import os
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.engine import make_url

from ncc_data.db import database
from ncc_data.models import Base, User
from ncc_data.security import password_hash
from ncc_data.seeds import seed


def pytest_addoption(parser):
    parser.addoption(
        "--database-url", default="", help="Explicit disposable PostgreSQL database, named ncc_test_*"
    )


@pytest.fixture(scope="session")
def migrated(request):
    url = request.config.getoption("--database-url")
    if not url:
        pytest.skip("需显式传入隔离PostgreSQL测试库")
    assert (make_url(url).database or "").startswith("ncc_test_")
    from alembic.config import Config

    from alembic import command

    previous = os.environ.get("NCC_DATABASE_URL")
    os.environ["NCC_DATABASE_URL"] = url
    try:
        command.upgrade(Config(str(Path(__file__).resolve().parents[2] / "alembic.ini")), "head")
    finally:
        if previous is None:
            os.environ.pop("NCC_DATABASE_URL", None)
        else:
            os.environ["NCC_DATABASE_URL"] = previous


@pytest_asyncio.fixture
async def store(request, migrated):
    url = request.config.getoption("--database-url")
    if not url:
        pytest.skip("需显式传入隔离PostgreSQL测试库")
    assert (make_url(url).database or "").startswith("ncc_test_"), "Refusing to reset a non-test database"
    engine, factory = database(url)
    async with engine.begin() as conn:
        tables = ", ".join('"' + name + '"' for name in Base.metadata.tables)
        await conn.execute(text("TRUNCATE TABLE " + tables + " CASCADE"))
    async with factory() as db, db.begin():
        await seed(db)
        actor = User(username="author", password_hash=password_hash("test-author-password"), admin=True)
        stranger = User(username="other", password_hash=password_hash("test-other-password"))
        db.add_all([actor, stranger])
        await db.flush()
        ids = actor.id, stranger.id
    yield factory, ids
    await engine.dispose()


@pytest_asyncio.fixture
async def author(store):
    factory, ids = store
    async with factory() as db, db.begin():
        actor = await db.get(User, ids[0])
        from ncc_data.changes import ChangeService

        yield ChangeService(db, actor)
