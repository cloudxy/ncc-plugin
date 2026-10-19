import pytest
import pytest_asyncio
from support.runtime import TestRuntime

from ncc_data.application.security import password_hash
from ncc_data.persistence.database import database
from ncc_data.persistence.models import User
from ncc_data.persistence.seeds import seed
from ncc_shared.database import DatabaseNotConfigured


def pytest_addoption(parser):
    parser.addoption("--ncc-config", default=None, help="config/.env；唯一测试库由正式连接派生")
    parser.addoption("--database-url", default="", help="兼容参数：必须与项目配置派生的唯一-test连接完全相同")


@pytest.fixture(scope="session")
def runtime(request):
    path = request.config.getoption("--ncc-config")
    override = request.config.getoption("--database-url")
    try:
        runtime = TestRuntime(path, override)
    except DatabaseNotConfigured as exc:
        if path or override:
            raise pytest.UsageError(str(exc)) from None
        pytest.skip("项目既定PostgreSQL配置尚未初始化；未连接、创建或清理任何数据库")
    with runtime:
        yield runtime


@pytest_asyncio.fixture
async def store(runtime):
    runtime.reset()
    engine, factory = database(runtime.settings.database_url)
    async with factory() as db, db.begin():
        await seed(db)
        actor = User(username="author", password_hash=password_hash("test-author-password"), admin=True)
        stranger = User(username="other", password_hash=password_hash("test-other-password"))
        db.add_all([actor, stranger])
        await db.flush()
        ids = actor.id, stranger.id
    try:
        yield factory, ids
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def author(store):
    factory, ids = store
    async with factory() as db, db.begin():
        actor = await db.get(User, ids[0])
        from ncc_data.application.knowledge.changes import ChangeService

        yield ChangeService(db, actor)
