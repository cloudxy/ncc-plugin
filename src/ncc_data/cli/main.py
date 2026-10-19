"""Explicit maintenance and authenticated HTTP client. No real-book auto migration."""

import argparse
import asyncio
import getpass
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import select, text

from ncc_data.application.security import password_hash
from ncc_data.cli.backup import pg_tool
from ncc_data.persistence.database import database
from ncc_data.persistence.models import User
from ncc_data.persistence.seeds import seed
from ncc_data.runtime.settings import Settings
from ncc_shared.configuration import configuration, initialize, template
from ncc_shared.http import APIClient


async def create_user(settings, username, password):
    engine, factory = database(settings.database_url)
    try:
        async with factory() as db, db.begin():
            if await db.scalar(select(User.id).where(User.username == username)):
                raise ValueError("账号已存在")
            first = await db.scalar(select(User.id).limit(1)) is None
            db.add(User(username=username, password_hash=password_hash(password), admin=first))
            await seed(db)
        print("账号已建立；首个账号为系统管理员。凭据未写入项目文件。")
    finally:
        await engine.dispose()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ncc-data", description="NCC私有数据与创作服务")
    parser.add_argument("--config", type=Path, help="可选的项目.env路径；正常使用自动读取项目根.env")
    parser.add_argument("--test", action="store_true", help="使用唯一的正式库-test，连接参数保持一致")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="初始化项目.env，不覆盖现有配置或改动数据库")
    init.add_argument("--from-existing", type=Path, help="导入已有NCC配置文件，原文件保持原样")
    commands.add_parser("migrate", help="显式应用迁移并安装初始定义")
    create = commands.add_parser("create-user", help="通过终端安全建立账号")
    create.add_argument("username")
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int)
    worker = commands.add_parser("worker")
    worker.add_argument("--once", action="store_true")
    commands.add_parser("doctor")
    request = commands.add_parser("request", help="使用范围凭据调用应用接口")
    request.add_argument("method", choices=["GET", "POST", "PATCH", "DELETE"])
    request.add_argument("path")
    request.add_argument("--data", type=Path)
    for name in ("backup", "restore"):
        p = commands.add_parser(name)
        p.add_argument("file")
        if name == "restore":
            p.add_argument("--confirm-database", required=True)
    workspace = commands.add_parser("workspace", help="显式导入/绑定受控工作副本")
    workspace.add_argument("action", choices=["import", "bind", "pull"])
    workspace.add_argument("directory", type=Path)
    workspace.add_argument("--scope", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            created = initialize(args.config, args.from_existing, template())
            print(
                "项目.env已初始化；请保留并填写已确定的连接参数。"
                if created
                else "项目.env已存在，原值保持不变。"
            )
            return
        client_values = configuration(args.config)
        if args.test:
            client_values = {
                **client_values,
                "NCC_API_PROFILE": "test",
                "NCC_API_URL": client_values.get("NCC_TEST_PUBLIC_ORIGIN", "http://127.0.0.1:8788"),
            }
        if args.command == "request":
            result = APIClient(client_values).request(
                args.method,
                args.path,
                json.loads(args.data.read_text()) if args.data else {} if args.method != "GET" else None,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        if args.command == "workspace":
            from ncc_data.cli.workspace import manage

            manage(args.action, args.directory, args.scope, client_values)
            return
        settings = Settings.load(args.config, "test" if args.test else "production")
        if args.command == "migrate":
            from alembic import command
            from alembic.config import Config

            migrations = Path(__file__).resolve().parents[1] / "persistence/migrations"
            config = Config(str(migrations / "alembic.ini"))
            config.set_main_option("script_location", str(migrations))
            config.attributes["database_url"] = settings.database_url
            command.upgrade(config, "head")

            async def install():
                engine, factory = database(settings.database_url)
                async with factory() as db, db.begin():
                    await seed(db)
                await engine.dispose()

            asyncio.run(install())
            print("迁移与系统定义安装完成。真实书库未迁移。")
        elif args.command == "create-user":
            password = getpass.getpass("新密码（至少12字符）：")
            if password != getpass.getpass("再次输入："):
                raise ValueError("两次密码不一致")
            asyncio.run(create_user(settings, args.username, password))
        elif args.command == "serve":
            if args.host not in {"127.0.0.1", "localhost", "::1"} and not settings.secure_cookie:
                raise ValueError("远端监听需要HTTPS同源部署配置")
            import uvicorn

            from ncc_data.api import create_app

            uvicorn.run(
                create_app(settings),
                host=args.host,
                port=args.port or urlsplit(settings.public_origin).port or 8787,
                log_level="warning",
                access_log=False,
            )
        elif args.command == "worker":
            from ncc_data.creation.worker import Worker

            engine, factory = database(settings.database_url)

            async def run():
                try:
                    await Worker(factory, settings).run(args.once)
                finally:
                    await engine.dispose()

            asyncio.run(run())
        elif args.command in {"backup", "restore"}:
            pg_tool(args, args.command == "restore", settings)
        else:

            async def doctor():
                engine, factory = database(settings.database_url)
                async with factory() as db:
                    version = await db.scalar(text("SHOW server_version"))
                    migration = await db.scalar(text("SELECT version_num FROM alembic_version"))
                await engine.dispose()
                print(
                    json.dumps(
                        {
                            "version": "4.0.0",
                            "postgresql": version,
                            "migration": migration,
                            "frontend_built": (settings.web_dist / "index.html").is_file(),
                            "model_configured": bool(settings.model_url and settings.writer_model),
                            "origin": settings.public_origin,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )

            asyncio.run(doctor())
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
