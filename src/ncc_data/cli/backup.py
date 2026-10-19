import json
import os
import subprocess
import tempfile
from configparser import ConfigParser
from contextlib import contextmanager
from pathlib import Path

from ncc_data.persistence.database import connection_parameters
from ncc_data.runtime.settings import Settings
from ncc_shared.paths import project_root


@contextmanager
def pg_service(parameters):
    """Keep all libpq options and secrets out of argv; remove the private file on exit."""
    with tempfile.TemporaryDirectory(prefix="ncc-pg-service-") as directory:
        service = Path(directory) / "pg_service.conf"
        config = ConfigParser(interpolation=None)
        options = {}
        for key, value in parameters.items():
            if key == "password":
                continue
            if "\n" in str(value) or "\r" in str(value):
                raise ValueError("维护连接参数包含服务文件不支持的换行")
            options[key] = str(value)
        config["ncc"] = options
        fd = os.open(service, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            config.write(stream)
        env = dict(os.environ, PGSERVICEFILE=str(service), PGSERVICE="ncc")
        if parameters.get("password") is not None:
            env["PGPASSWORD"] = parameters["password"]
        yield env


def pg_tool(args, restoring=False, settings=None):
    settings = settings or Settings.load()

    parameters = connection_parameters(settings.database_url)
    target = Path(args.file).expanduser().resolve()
    private_root = project_root()
    if target.is_relative_to(private_root) and not target.is_relative_to(private_root / ".ncc-runtime"):
        raise ValueError("数据库备份不能写进受管仓库；请选择仓外目录或忽略的.ncc-runtime")
    command = [
        "pg_restore" if restoring else "pg_dump",
        "--dbname",
        "service=ncc",
    ]
    if restoring:
        if args.confirm_database != parameters["dbname"]:
            raise ValueError("恢复必须用--confirm-database明确目标库名")
        # Restore into an empty target only. Existing production never gets an implicit --clean.
        import psycopg

        with psycopg.connect(**parameters) as conn:
            count = conn.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'").fetchone()[0]
            if count:
                raise ValueError("恢复目标必须为空库；现有库保持原状")
        command += ["--exit-on-error", "--single-transaction", "--no-owner", "--no-privileges", str(target)]
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise ValueError("备份文件已存在，拒绝覆盖")
        command += ["--format=custom", "--no-owner", "--file", str(target)]
    pg_bin = settings.pg_bin
    if pg_bin:
        command[0] = str(Path(pg_bin) / command[0])
    previous_umask = os.umask(0o077)
    try:
        with pg_service(parameters) as env:
            subprocess.run(command, env=env, check=True, stdout=subprocess.DEVNULL)
    finally:
        os.umask(previous_umask)
    if not restoring:
        target.chmod(0o600)
        from ncc_shared.serialization import digest

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

        with psycopg.connect(**parameters) as conn:
            conn.execute("UPDATE ncc_session SET revoked=true")
            conn.execute("UPDATE ncc_delegation SET revoked=true")
            conn.execute(
                "UPDATE ncc_job SET state='paused', lease_token=NULL, lease_until=NULL WHERE state IN ('queued','running')"
            )
        print("隔离恢复完成；会话、托管授权已撤销，未完成任务暂停。请完成内容/权限/附件对账后切换。")
