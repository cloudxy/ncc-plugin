"""Explicit disposable PostgreSQL dump/restore drill, separate from data reset tests."""

import argparse
import asyncio
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import psycopg
from psycopg import sql
from sqlalchemy import select
from sqlalchemy.engine import make_url

from ncc_data.db import database
from ncc_data.models import Assessment, Base, Scope, User
from ncc_data.policy import POLICY, POLICY_HASH
from ncc_data.scoring import evaluate
from ncc_data.service import Service
from ncc_data.utils import digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--target-database", required=True)
    parser.add_argument("--pg-bin", required=True)
    args = parser.parse_args()
    source = make_url(args.database_url)
    assert source.database.startswith("ncc_test_") and args.target_database.startswith("ncc_test_")
    assert source.database != args.target_database

    async def seed_drill():
        engine, factory = database(args.database_url)
        async with factory() as db, db.begin():
            actor = await db.scalar(select(User).limit(1))
            scope = await db.scalar(select(Scope).where(Scope.owner_id == actor.id).limit(1))
            assert scope is not None
            svc = Service(db, actor)
            await svc.upload(scope.id, "recovery-fixture.bin", "application/octet-stream", bytes(range(256)))
            text = "合成恢复证据"
            report = {
                "dimensions": {
                    r["key"]: {"score": 4.5, "evidence": [text], "reason": "仅用于恢复完整性的合成测试记录"}
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

    def connect(name, autocommit=False):
        return psycopg.connect(
            host=source.query.get("host", source.host),
            port=source.query.get("port", source.port or 5432),
            user=source.username,
            password=source.password,
            dbname=name,
            autocommit=autocommit,
        )

    def fingerprint(name):
        result = {}
        with connect(name) as conn:
            for table in Base.metadata.tables:
                if table in {"ncc_session", "ncc_job", "ncc_delegation"}:
                    continue
                query = sql.SQL(
                    "SELECT count(*),md5(coalesce(string_agg(md5(row_to_json(t)::text),'' ORDER BY md5(row_to_json(t)::text)),'')) FROM {} t"
                ).format(sql.Identifier(table))
                count, digest = conn.execute(query).fetchone()
                result[table] = {"count": count, "digest": digest}
        return result

    with connect(source.database, True) as conn:
        assert not conn.execute(
            "SELECT 1 FROM pg_database WHERE datname=%s", (args.target_database,)
        ).fetchone()
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(args.target_database)))
    before = fingerprint(source.database)
    env = dict(os.environ, NCC_DATABASE_URL=args.database_url, NCC_PG_BIN=args.pg_bin)
    env.pop("NCC_MAINTENANCE_URL", None)
    with tempfile.TemporaryDirectory(prefix="ncc-recovery-private-") as tmp:
        backup = Path(tmp) / "synthetic.dump"
        command = [sys.executable, "-m", "ncc_data.cli"]
        result = subprocess.run([*command, "backup", str(backup)], env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert stat.S_IMODE(backup.stat().st_mode) == 0o600
        env["NCC_DATABASE_URL"] = source.set(database=args.target_database).render_as_string(
            hide_password=False
        )
        result = subprocess.run(
            [*command, "restore", str(backup), "--confirm-database", args.target_database],
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert fingerprint(args.target_database) == before
        with connect(args.target_database) as conn:
            assert conn.execute("SELECT count(*) FROM ncc_session WHERE NOT revoked").fetchone()[0] == 0
            assert (
                conn.execute("SELECT count(*) FROM ncc_job WHERE state IN ('queued','running')").fetchone()[0]
                == 0
            )
            assert conn.execute("SELECT count(*) FROM ncc_delegation WHERE NOT revoked").fetchone()[0] == 0
        result = subprocess.run(
            [*command, "restore", str(backup), "--confirm-database", args.target_database],
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0 and fingerprint(args.target_database) == before
        print(
            json.dumps(
                {
                    "synthetic_only": True,
                    "tables_compared": len(before),
                    "counts": {k: v["count"] for k, v in before.items()},
                    "full_row_digests_equal": True,
                    "backup_mode": "0600",
                    "restored_credentials_revoked": True,
                    "unfinished_jobs_paused": True,
                    "nonempty_target_refused": True,
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
