"""All destructive/integration checks share one guarded, serial -test database."""

import asyncio
import functools
import sys
import threading
import time
from contextlib import AbstractContextManager
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import psycopg
import uvicorn
from sqlalchemy import select

from ncc_data.api import create_app
from ncc_data.application.security import password_hash
from ncc_data.persistence.database import connection_parameters, database
from ncc_data.persistence.models import Base, User
from ncc_data.persistence.seeds import seed
from ncc_data.runtime.settings import Settings
from ncc_shared.configuration import configuration
from ncc_shared.database import DatabasePair, configured_url

LOCK_KEY = 0x4E434354455354
USERNAME = "browser-author"
PASSWORD = "synthetic-browser-password"


def test_settings(path=None, override=None):
    pair = DatabasePair(configured_url(configuration(path)))
    if override:
        pair.require_test(override)
    settings = Settings.load(path, profile="test")
    pair.require_test(settings.database_url)
    return settings


class TestRuntime(AbstractContextManager):
    __test__ = False

    def __init__(self, path=None, override=None, server=False):
        self.settings = test_settings(path, override)
        self.origin = self.settings.public_origin
        self.with_server = server
        self.connection = None
        self.server = None
        self.thread = None

    def __enter__(self):
        self.connection = psycopg.connect(
            **connection_parameters(self.settings.database_url), autocommit=True
        )
        try:
            actual = self.connection.execute("SELECT current_database()").fetchone()[0]
            if actual != connection_parameters(self.settings.database_url)["dbname"]:
                raise ValueError("实际数据库与唯一-test目标不符，停止测试")
            if not self.connection.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_KEY,)).fetchone()[0]:
                raise ValueError("唯一测试库正在被其他验收使用，请等该次结束")
            self.check_schema()
            from alembic import command
            from alembic.config import Config

            import ncc_data.persistence

            migrations = Path(ncc_data.persistence.__file__).parent / "migrations"
            config = Config(str(migrations / "alembic.ini"))
            config.attributes["database_url"] = self.settings.database_url
            command.upgrade(config, "head")
            if self.with_server:
                asyncio.run(self.seed_browser())
                self.start_server()
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def check_schema(self):
        if self.connection.execute("SELECT current_schema()").fetchone()[0] != "public":
            raise ValueError("测试连接的有效schema不是public；保留既定配置并停止清理")
        foreign = self.connection.execute(
            "SELECT 1 FROM pg_tables WHERE schemaname NOT IN ('public', 'information_schema') AND NOT starts_with(schemaname, 'pg_') LIMIT 1"
        ).fetchone()
        if foreign:
            raise ValueError("测试库存在其他schema业务表，拒绝重置")
        tables = {
            r[0] for r in self.connection.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        }
        if tables - set(Base.metadata.tables) - {"alembic_version"}:
            raise ValueError("测试库存在非NCC表，拒绝清理或恢复；请先人工核查")

    def reset(self):
        self.check_schema()
        from psycopg import sql

        tables = sql.SQL(", ").join(sql.Identifier("public", t) for t in Base.metadata.tables)
        self.connection.execute(sql.SQL("TRUNCATE TABLE {}").format(tables))

    async def seed_browser(self):
        engine, factory = database(self.settings.database_url)
        try:
            async with factory() as db, db.begin():
                await seed(db)
                actor = await db.scalar(select(User).where(User.username == USERNAME))
                if actor is None:
                    db.add(User(username=USERNAME, password_hash=password_hash(PASSWORD), admin=True))
                elif not actor.admin:
                    raise ValueError("合成验收账号已存在且权限不符，请检查测试库")
        finally:
            await engine.dispose()

    def start_server(self):
        origin = urlsplit(self.origin)
        if origin.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("浏览器验收只启动本机测试服务")
        # Never reuse an existing service: it may belong to a production session.
        import socket

        with socket.socket(socket.AF_INET6 if origin.hostname == "::1" else socket.AF_INET) as probe:
            probe.bind((origin.hostname, origin.port or 8788))
        self.server = uvicorn.Server(
            uvicorn.Config(
                create_app(self.settings),
                host=origin.hostname,
                port=origin.port or 8788,
                log_level="warning",
                access_log=False,
            )
        )
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if not self.thread.is_alive():
                raise RuntimeError("测试API未能启动")
            try:
                response = httpx.get(self.origin + "/health/live", timeout=1)
                if response.status_code == 200 and response.json().get("profile") == "test":
                    return
            except httpx.TransportError:
                pass
            time.sleep(0.1)
        raise RuntimeError("测试API启动超时")

    def __exit__(self, *exc):
        if self.server:
            self.server.should_exit = True
        if self.thread:
            self.thread.join(timeout=15)
        if self.connection:
            self.connection.close()
        return False


def browser_test(function):
    @functools.wraps(function)
    def run():
        path = None
        if "--config" in sys.argv:
            index = sys.argv.index("--config")
            path = Path(sys.argv[index + 1])
            del sys.argv[index : index + 2]
        with TestRuntime(path, server=True) as runtime:
            return function(runtime)

    return run
