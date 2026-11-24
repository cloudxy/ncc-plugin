import secrets

import pytest
import pytest_asyncio
from support.runtime import TestRuntime

from ncc_data.application.security import password_hash
from ncc_data.persistence.database import database
from ncc_data.persistence.models import Delegation, Job, Session, User, uid
from ncc_data.persistence.seeds import seed
from ncc_shared.database import DatabaseNotConfigured
from sqlalchemy import update


class _ScopedSessionFactory:
    """Wrap SQLAlchemy session factory so Worker only claims this test's synthetic jobs."""

    def __init__(self, factory, actor_ids, credentials=None):
        self._factory = factory
        self._base_actor_ids = tuple(actor_ids)
        self._extra_actor_ids: set[str] = set()
        self.credentials: dict[str, str] = dict(credentials or {})

    @property
    def _test_actor_ids(self) -> tuple[str, ...]:
        return tuple(set(self._base_actor_ids) | self._extra_actor_ids)

    def register_user(self, user_id: str, password: str | None = None) -> None:
        self._extra_actor_ids.add(user_id)
        if password is not None:
            self.credentials[user_id] = password

    def __call__(self, *args, **kwargs):
        return self._factory(*args, **kwargs)


async def retire_ephemeral_users(db, user_ids) -> None:
    ids = tuple(set(user_ids))
    if not ids:
        return
    await db.execute(update(Session).where(Session.user_id.in_(ids)).values(revoked=True))
    await db.execute(update(Delegation).where(Delegation.actor_id.in_(ids)).values(revoked=True))
    await db.execute(
        update(Job)
        .where(Job.actor_id.in_(ids), Job.state.in_(["queued", "running"]))
        .values(state="cancelled", cancel_requested=True, lease_token=None, lease_until=None)
    )
    await db.execute(
        update(User)
        .where(User.id.in_(ids))
        .values(active=False, password_hash=password_hash(secrets.token_urlsafe(32)))
    )


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
    engine, raw_factory = database(runtime.settings.database_url)
    suffix = secrets.token_urlsafe(9)
    author_password = secrets.token_urlsafe(24)
    other_password = secrets.token_urlsafe(24)
    async with raw_factory() as db, db.begin():
        await seed(db)
        actor = User(
            username=f"test-author-{suffix}",
            password_hash=password_hash(author_password),
            admin=True,
            active=True,
        )
        stranger = User(
            username=f"test-other-{suffix}",
            password_hash=password_hash(other_password),
            active=True,
        )
        db.add_all([actor, stranger])
        await db.flush()
        ids = actor.id, stranger.id
    factory = _ScopedSessionFactory(
        raw_factory,
        ids,
        credentials={ids[0]: author_password, ids[1]: other_password},
    )
    try:
        yield factory, ids
    finally:
        try:
            async with raw_factory() as db, db.begin():
                await retire_ephemeral_users(db, factory._test_actor_ids)
        finally:
            await engine.dispose()


@pytest_asyncio.fixture
async def author(store):
    factory, ids = store
    async with factory() as db, db.begin():
        actor = await db.get(User, ids[0])
        from ncc_data.application.knowledge.changes import ChangeService

        yield ChangeService(db, actor)
