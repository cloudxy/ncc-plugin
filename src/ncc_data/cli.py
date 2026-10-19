"""Explicit maintenance and authenticated HTTP client. No real-book auto migration."""

import argparse
import asyncio
import getpass
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from sqlalchemy import select, text

from .config import Settings
from .db import database
from .models import User
from .security import password_hash
from .seeds import seed


def repo_root():
    return Path(__file__).resolve().parents[2]


def http_request(method, path, body=None):
    origin = os.environ.get("NCC_API_URL", "http://127.0.0.1:8787").rstrip("/")
    token = os.environ.get("NCC_API_TOKEN")
    if not token:
        raise ValueError("请在私有环境配置NCC_API_TOKEN范围凭据")
    parsed = urlsplit(origin)
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("远端API必须使用HTTPS")
    if not path.startswith("/") or ".." in path.split("/"):
        raise ValueError("API路径无效")
    with httpx.Client(timeout=120, follow_redirects=False) as client:
        response = client.request(
            method, origin + "/api/v1" + path, headers={"Authorization": "Bearer " + token}, json=body
        )
        if response.is_error:
            raise ValueError(response.json().get("detail", f"HTTP {response.status_code}"))
        return response.json()


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


def pg_tool(args, restoring=False):
    settings = Settings.from_env()
    from sqlalchemy.engine import make_url

    url = make_url(os.environ.get("NCC_MAINTENANCE_URL", settings.database_url))
    target = Path(args.file).expanduser().resolve()
    private_root = repo_root()
    if target.is_relative_to(private_root) and not target.is_relative_to(private_root / ".ncc-runtime"):
        raise ValueError("数据库备份不能写进受管仓库；请选择仓外目录或忽略的.ncc-runtime")
    env = os.environ.copy()
    if url.password:
        env["PGPASSWORD"] = url.password
    command = [
        "pg_restore" if restoring else "pg_dump",
        "--host",
        url.query.get("host", url.host or "localhost"),
        "--port",
        str(url.query.get("port", url.port or 5432)),
        "--username",
        url.username or "",
        "--dbname",
        url.database or "",
    ]
    if restoring:
        if args.confirm_database != url.database:
            raise ValueError("恢复必须用--confirm-database明确目标库名")
        # Restore into an empty target only. Existing production never gets an implicit --clean.
        import psycopg

        with psycopg.connect(
            host=url.query.get("host", url.host),
            port=url.query.get("port", url.port or 5432),
            user=url.username,
            password=url.password,
            dbname=url.database,
        ) as conn:
            count = conn.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'").fetchone()[0]
            if count:
                raise ValueError("恢复目标必须为空库；现有库保持原状")
        command += ["--exit-on-error", "--single-transaction", "--no-owner", "--no-privileges", str(target)]
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise ValueError("备份文件已存在，拒绝覆盖")
        command += ["--format=custom", "--no-owner", "--file", str(target)]
    pg_bin = os.environ.get("NCC_PG_BIN", "")
    if pg_bin:
        command[0] = str(Path(pg_bin) / command[0])
    previous_umask = os.umask(0o077)
    try:
        subprocess.run(command, env=env, check=True, stdout=subprocess.DEVNULL)
    finally:
        os.umask(previous_umask)
    if not restoring:
        target.chmod(0o600)
        from .utils import digest

        print(
            json.dumps(
                {
                    "file": str(target),
                    "sha256": digest(target.read_bytes()),
                    "purpose": "full-postgresql-backup",
                }
            )
        )
    else:
        # Restored credentials and stale external work cannot resume automatically.
        import psycopg

        with psycopg.connect(
            host=url.query.get("host", url.host),
            port=url.query.get("port", url.port or 5432),
            user=url.username,
            password=url.password,
            dbname=url.database,
        ) as conn:
            conn.execute("UPDATE ncc_session SET revoked=true")
            conn.execute("UPDATE ncc_delegation SET revoked=true")
            conn.execute(
                "UPDATE ncc_job SET state='paused', lease_token=NULL, lease_until=NULL WHERE state IN ('queued','running')"
            )
        print("隔离恢复完成；会话、托管授权已撤销，未完成任务暂停。请完成内容/权限/附件对账后切换。")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ncc-data", description="NCC私有数据与创作服务")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate", help="显式应用迁移并安装初始定义")
    create = commands.add_parser("create-user", help="通过终端安全建立账号")
    create.add_argument("username")
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8787)
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
        if args.command == "request":
            result = http_request(
                args.method,
                args.path,
                json.loads(args.data.read_text()) if args.data else {} if args.method != "GET" else None,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        if args.command == "workspace":
            from .workspace_client import manage

            manage(args.action, args.directory, args.scope)
            return
        settings = Settings.from_env()
        if args.command == "migrate":
            from alembic.config import Config

            from alembic import command

            source_config = repo_root() / "alembic.ini"
            bundled = Path(__file__).parent / "alembic.ini"
            config = Config(str(source_config if source_config.exists() else bundled))
            config.set_main_option(
                "script_location",
                str(
                    repo_root() / "alembic"
                    if source_config.exists()
                    else Path(__file__).parent / "migrations"
                ),
            )
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

            uvicorn.run(
                "ncc_data.api:create_app",
                factory=True,
                host=args.host,
                port=args.port,
                log_level="warning",
                access_log=False,
            )
        elif args.command == "worker":
            from .automation import Worker

            engine, factory = database(settings.database_url)

            async def run():
                try:
                    await Worker(factory, settings).run(args.once)
                finally:
                    await engine.dispose()

            asyncio.run(run())
        elif args.command in {"backup", "restore"}:
            pg_tool(args, args.command == "restore")
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
