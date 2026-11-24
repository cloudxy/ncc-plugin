"""Explicit maintenance and authenticated HTTP client. No real-book auto migration."""

import argparse
import asyncio
import getpass
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import ValidationError
from sqlalchemy import select, text

from ncc_data.application.security import ensure_default_admin, password_hash
from ncc_data.cli.backup import pg_tool
from ncc_data.persistence.database import connection_parameters, database
from ncc_data.persistence.models import User
from ncc_data.persistence.seeds import seed
from ncc_data.runtime.settings import Settings, resolve_profile
from ncc_shared.configuration import configuration, initialize, template
from ncc_shared.errors import DomainError
from ncc_shared.http import APIClient, is_loopback_host
from ncc_shared.paths import config_path


def cli_profile(args):
    chosen = []
    if getattr(args, "test", False):
        chosen.append("test")
    if getattr(args, "production", False):
        chosen.append("production")
    explicit = getattr(args, "profile", None)
    if explicit:
        chosen.append(explicit)
    if len(set(chosen)) > 1:
        raise ValueError("--test、--production 与 --profile 不能同时指定不同模式")
    return chosen[0] if chosen else None


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


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", type=Path, default=argparse.SUPPRESS, help="可选的config/.env路径；正常使用自动读取config/.env")
    common.add_argument("--test", action="store_true", default=argparse.SUPPRESS, help="使用同连接的ncc-dev及测试端口，连接参数保持一致")
    common.add_argument("--production", action="store_true", default=argparse.SUPPRESS, help="明确选择线上正式库ncc-pro（或设NCC_ENV=production）")
    common.add_argument("--profile", choices=["local", "production", "test"], default=argparse.SUPPRESS, help="显式指定运行profile")

    parser = argparse.ArgumentParser(prog="ncc-data", description="NCC私有数据与创作服务")
    parser.add_argument("--config", type=Path, help="可选的config/.env路径；正常使用自动读取config/.env")
    parser.add_argument("--test", action="store_true", help="使用同连接的ncc-dev及测试端口，连接参数保持一致")
    parser.add_argument("--production", action="store_true", help="明确选择线上正式库ncc-pro（或设NCC_ENV=production）")
    parser.add_argument("--profile", choices=["local", "production", "test"], help="显式指定运行profile")
    commands = parser.add_subparsers(dest="command", required=True)
    from ncc_data.cli.data import register

    register(commands)
    mcp_config = commands.add_parser("mcp-config", parents=[common], help="注册本项目只读MCP，不写入连接凭据")
    mcp_config.add_argument("--host", choices=["codex", "claude", "both"], default="both")
    commands.add_parser("mcp", parents=[common], help="启动只读PostgreSQL MCP（stdio），共用项目配置")
    init = commands.add_parser("init", parents=[common], help="初始化config/.env，不覆盖现有配置或改动数据库")
    init.add_argument("--from-existing", type=Path, help="导入已有NCC配置文件，原文件保持原样")
    commands.add_parser("migrate", parents=[common], help="显式应用迁移并安装初始定义")
    create = commands.add_parser("create-user", parents=[common], help="通过终端安全建立账号")
    create.add_argument("username")
    serve = commands.add_parser("serve", parents=[common])
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int)
    worker = commands.add_parser("worker", parents=[common])
    worker.add_argument("--once", action="store_true")
    commands.add_parser("doctor", parents=[common])
    request = commands.add_parser("request", parents=[common], help="使用范围凭据调用应用接口")
    request.add_argument("method", choices=["GET", "POST", "PATCH", "DELETE"])
    request.add_argument("path")
    request.add_argument("--data", type=Path)
    for name in ("backup", "restore"):
        p = commands.add_parser(name, parents=[common])
        p.add_argument("file")
        if name == "restore":
            p.add_argument("--confirm-database", required=True)
    workspace = commands.add_parser("workspace", parents=[common], help="显式导入/绑定受控工作副本")
    workspace.add_argument("action", choices=["import", "bind", "pull"])
    workspace.add_argument("directory", type=Path)
    workspace.add_argument("--scope", required=True)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            created = initialize(args.config, args.from_existing, template())
            print(
                f"配置文件已就绪：{args.config or config_path()}；初始化或迁移不改变已有配置值。"
                if created
                else f"配置文件已存在：{args.config or config_path()}；原值保持不变。"
            )
            return
        selected_profile = cli_profile(args)
        if args.command == "mcp-config":
            from ncc_data.mcp.configuration import install

            resolved_mcp = selected_profile
            if resolved_mcp is None:
                try:
                    resolved_mcp = resolve_profile(configuration(args.config))
                except ValueError:
                    resolved_mcp = "local"
            print(
                json.dumps(
                    install(
                        args.host,
                        profile=resolved_mcp,
                        config=args.config,
                        explicit_flag=selected_profile == "production",
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        if args.command == "mcp":
            from ncc_data.mcp.server import create_server

            create_server(args.config, selected_profile).run(transport="stdio")
            return
        if args.command == "data":
            from ncc_data.cli.data import run

            print(json.dumps(run(args), ensure_ascii=False, indent=2))
            return
        client_values = configuration(args.config)
        effective_profile = selected_profile or resolve_profile(client_values)
        client_values = {**client_values, "NCC_API_PROFILE": effective_profile}
        if effective_profile == "test":
            client_values = {
                **client_values,
                "NCC_API_URL": client_values.get("NCC_TEST_PUBLIC_ORIGIN", "http://127.0.0.1:8788"),
            }
        if args.command == "request":
            result = APIClient(client_values, profile=effective_profile).request(
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
        settings = Settings.load(args.config, selected_profile)
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
                try:
                    async with factory() as db, db.begin():
                        await seed(db)
                        created = await ensure_default_admin(db)
                    return created
                finally:
                    await engine.dispose()

            created_admin = asyncio.run(install())
            print("迁移与系统定义安装完成。真实书库未迁移。")
            if created_admin:
                print(
                    "安全提醒：已初始化默认管理员账号 admin（初始密码：123456）。"
                    "第一次使用时必须进入后台修改账号与密码（本机 127.0.0.1 仅作提醒，真实 IP 访问将强制修改）。"
                )
        elif args.command == "create-user":
            password = getpass.getpass("新密码（至少12字符）：")
            if password != getpass.getpass("再次输入："):
                raise ValueError("两次密码不一致")
            asyncio.run(create_user(settings, args.username, password))
        elif args.command == "serve":
            if not is_loopback_host(args.host) and not settings.secure_cookie:
                raise ValueError("远端监听需要HTTPS同源部署配置")
            import uvicorn

            from ncc_data.api import create_app

            uvicorn.run(
                create_app(settings, bind_host=args.host),
                host=args.host,
                port=args.port or urlsplit(settings.public_origin).port or 8761,
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
                try:
                    async with factory() as db:
                        version = await db.scalar(text("SHOW server_version"))
                        migration = await db.scalar(text("SELECT version_num FROM alembic_version"))
                        has_col = await db.scalar(
                            text(
                                "SELECT 1 FROM information_schema.columns "
                                "WHERE table_schema = current_schema() "
                                "AND table_name = 'ncc_user' "
                                "AND column_name = 'must_change_credentials'"
                            )
                        )
                        default_admin_active = (
                            bool(
                                await db.scalar(
                                    select(User.id)
                                    .where(
                                        User.active.is_(True),
                                        User.must_change_credentials.is_(True),
                                    )
                                    .limit(1)
                                )
                            )
                            if has_col
                            else False
                        )
                finally:
                    await engine.dispose()
                print(
                    json.dumps(
                        {
                            "version": "4.0.0",
                            "profile": settings.profile,
                            "database": connection_parameters(settings.database_url)["dbname"],
                            "postgresql": version,
                            "migration": migration,
                            "frontend_built": (settings.web_dist / "index.html").is_file(),
                            "model_configured": bool(settings.model_url and settings.writer_model),
                            "default_admin_active": default_admin_active,
                            "origin": settings.public_origin,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )

            asyncio.run(doctor())
    except DomainError as exc:
        print("ERROR: " + exc.code + ": " + exc.detail, file=sys.stderr)
        raise SystemExit(1) from None
    except ValidationError:
        print("ERROR: 数据字段、类型或版本无效；输入内容不会输出", file=sys.stderr)
        raise SystemExit(1) from None
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
