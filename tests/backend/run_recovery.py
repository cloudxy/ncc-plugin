"""Explicit serial dump/replay drill in the sole -test database; never creates databases."""

import argparse
import asyncio
import json
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from types import SimpleNamespace

from psycopg import sql
from sqlalchemy import select
from support.runtime import TestRuntime

from ncc_data.application.service import Service
from ncc_data.cli.backup import pg_service, pg_tool
from ncc_data.creation.scoring import evaluate
from ncc_data.persistence.database import connection_parameters, database
from ncc_data.persistence.models import Assessment, Base, Scope, User
from ncc_shared.quality.policy import POLICY, POLICY_HASH
from ncc_shared.serialization import digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path)
    parser.add_argument("--confirm-reset-test", required=True, help="明确填写正式库-test；将重放测试数据")
    args = parser.parse_args()
    runtime = TestRuntime(args.config)
    name = connection_parameters(runtime.settings.database_url)["dbname"]
    if args.confirm_reset_test != name:
        parser.error("确认库名必须与项目正式连接派生的唯一-test库完全相同")
    with runtime:
        asyncio.run(runtime.seed_browser())

        async def seed_drill():
            engine, factory = database(runtime.settings.database_url)
            async with factory() as db, db.begin():
                actor = await db.scalar(select(User).limit(1))
                scope = await db.scalar(select(Scope).where(Scope.owner_id == actor.id).limit(1))
                if scope is None:
                    from ncc_data.domain.contracts import ScopeInput

                    created = await Service(db, actor).create_scope(ScopeInput(name="合成恢复空间"))
                    scope = await db.get(Scope, created["id"])
                svc = Service(db, actor)
                await svc.upload(
                    scope.id, "recovery-fixture.bin", "application/octet-stream", bytes(range(256))
                )
                text = "合成恢复证据"
                report = {
                    "dimensions": {
                        r["key"]: {
                            "score": 4.5,
                            "evidence": [text],
                            "reason": "仅用于恢复完整性的合成测试记录",
                        }
                        for r in POLICY["profiles"]["P3"]
                    },
                    "hard": "pass",
                    "coverage": "complete",
                    "summary": "恢复测试替身；不是真实创作质量证据",
                    "observations": [],
                    "suggestions": [],
                }
                evaluation = evaluate("P3", text, report)
                db.add(
                    Assessment(
                        scope_id=scope.id,
                        actor_id=actor.id,
                        content_hash=digest(text),
                        dependency_version=scope.version,
                        scheme="P3",
                        policy_hash=POLICY_HASH,
                        evaluator="fixture:recovery",
                        report={**evaluation, "requires_secret": True},
                        score=evaluation["score"],
                        verdict=evaluation["verdict"],
                    )
                )
            await engine.dispose()

        asyncio.run(seed_drill())

        def fingerprint():
            result = {}
            for table in Base.metadata.tables:
                if table in {"ncc_session", "ncc_job", "ncc_delegation"}:
                    continue
                query = sql.SQL(
                    "SELECT count(*),md5(coalesce(string_agg(md5(row_to_json(t)::text),'' ORDER BY md5(row_to_json(t)::text)),'')) FROM {} t"
                ).format(sql.Identifier(table))
                count, checksum = runtime.connection.execute(query).fetchone()
                result[table] = {"count": count, "digest": checksum}
            return result

        before = fingerprint()
        # A successful dump is the rollback artifact. Clean/replay only objects in that dump;
        # no extra recovery database, schema or server parameter is introduced.
        directory = Path(tempfile.mkdtemp(prefix="ncc-recovery-private-"))
        backup = directory / "synthetic.dump"
        pg_tool(SimpleNamespace(file=backup), settings=runtime.settings)
        assert stat.S_IMODE(backup.stat().st_mode) == 0o600
        runtime.check_schema()
        executable = (
            str(Path(runtime.settings.pg_bin) / "pg_restore") if runtime.settings.pg_bin else "pg_restore"
        )
        with pg_service(connection_parameters(runtime.settings.database_url)) as env:
            subprocess.run(
                [
                    executable,
                    "--dbname",
                    "service=ncc",
                    "--clean",
                    "--if-exists",
                    "--exit-on-error",
                    "--single-transaction",
                    "--no-owner",
                    "--no-privileges",
                    str(backup),
                ],
                env=env,
                check=True,
            )
        runtime.connection.execute("UPDATE ncc_session SET revoked=true")
        runtime.connection.execute("UPDATE ncc_delegation SET revoked=true")
        runtime.connection.execute(
            "UPDATE ncc_job SET state='paused', lease_token=NULL, lease_until=NULL WHERE state IN ('queued','running')"
        )
        assert fingerprint() == before
        assert (
            runtime.connection.execute("SELECT count(*) FROM ncc_session WHERE NOT revoked").fetchone()[0]
            == 0
        )
        assert (
            runtime.connection.execute("SELECT count(*) FROM ncc_delegation WHERE NOT revoked").fetchone()[0]
            == 0
        )
        assert (
            runtime.connection.execute(
                "SELECT count(*) FROM ncc_job WHERE state IN ('queued','running')"
            ).fetchone()[0]
            == 0
        )
        try:
            pg_tool(
                SimpleNamespace(file=backup, confirm_database=name), restoring=True, settings=runtime.settings
            )
        except ValueError as exc:
            assert "空库" in str(exc)
        else:
            raise AssertionError("普通restore必须拒绝非空目标")
        assert fingerprint() == before
        print(
            json.dumps(
                {
                    "synthetic_only": True,
                    "database_count": 1,
                    "tables_compared": len(before),
                    "full_row_digests_equal": True,
                    "backup_mode": "0600",
                    "restored_credentials_revoked": True,
                    "unfinished_jobs_paused": True,
                    "nonempty_target_refused": True,
                    "rollback_backup": str(backup),
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
