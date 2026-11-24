from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ncc_shared.database import PRODUCTION_DATABASE, TEST_DATABASE

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import start  # noqa: E402


def parse_args(*argv: str):
    return start.build_parser().parse_args(list(argv))


def flags_for(*argv: str) -> list[str]:
    return start.cli_common_flags(parse_args(*argv))


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        ((), ["--profile", "production"]),
        (("--database", "ncc-pro"), ["--profile", "production"]),
        (("--database", "ncc-dev"), ["--profile", "local"]),
        (("--test",), ["--test"]),
        (("--production",), ["--production"]),
        (("--profile", "local"), ["--profile", "local"]),
        (("--profile", "production"), ["--profile", "production"]),
        (("--profile", "test"), ["--profile", "test"]),
        (("--config", "/tmp/x.env"), ["--config", "/tmp/x.env", "--profile", "production"]),
        (
            ("--config", "/tmp/x.env", "--database", "ncc-dev"),
            ["--config", "/tmp/x.env", "--profile", "local"],
        ),
        (("--config", "/tmp/x.env", "--test"), ["--config", "/tmp/x.env", "--test"]),
        (
            ("--config", "/tmp/x.env", "--profile", "test"),
            ["--config", "/tmp/x.env", "--profile", "test"],
        ),
    ],
)
def test_cli_common_flags_mapping_and_passthrough(argv: tuple[str, ...], expected: list[str]) -> None:
    assert flags_for(*argv) == expected


@pytest.mark.parametrize(
    "argv",
    [
        ["--database", "ncc-pro", "--test"],
        ["--database", "ncc-dev", "--production"],
        ["--database", "ncc-pro", "--profile", "local"],
    ],
)
def test_database_conflicts_with_mode_flags(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        start.build_parser().parse_args(argv)
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "not allowed with argument" in captured.err


def test_invalid_database_value_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        start.build_parser().parse_args(["--database", "other-db"])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "invalid choice" in captured.err
    assert "ncc-dev" in captured.err and "ncc-pro" in captured.err


def test_database_choices_stay_in_sync_with_shared_constants() -> None:
    action = next(act for act in start.build_parser()._actions if act.dest == "database")
    assert set(action.choices) == {PRODUCTION_DATABASE, TEST_DATABASE}
    assert PRODUCTION_DATABASE == "ncc-pro"
    assert TEST_DATABASE == "ncc-dev"


@pytest.mark.parametrize(
    ("argv", "expected_target", "expected_hint", "forbidden_substring"),
    [
        (
            [],
            "production / ncc-pro",
            "./start.py --database ncc-pro --migrate",
            "ncc-dev",
        ),
        (
            ["--database", "ncc-dev"],
            "local / ncc-dev",
            "./start.py --database ncc-dev --migrate",
            "ncc-pro",
        ),
        (
            ["--test"],
            "test / ncc-dev",
            "./start.py --test --migrate",
            "ncc-pro",
        ),
        (
            ["--profile", "local"],
            "local / ncc-dev",
            "./start.py --profile local --migrate",
            "ncc-pro",
        ),
        (
            ["--config", "/tmp/x.env"],
            "production / ncc-pro",
            "./start.py --config /tmp/x.env --database ncc-pro --migrate",
            "ncc-dev",
        ),
        (
            ["--config", "/tmp/x.env", "--database", "ncc-dev"],
            "local / ncc-dev",
            "./start.py --config /tmp/x.env --database ncc-dev --migrate",
            "ncc-pro",
        ),
    ],
)
def test_run_doctor_missing_table_shows_target_and_exact_migrate_command(
    argv: list[str],
    expected_target: str,
    expected_hint: str,
    forbidden_substring: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(start, "IS_WINDOWS", False)
    monkeypatch.setattr(
        start,
        "run_cli_step",
        lambda *_a, **_kw: subprocess.CompletedProcess(
            args=["ncc-data", "doctor"],
            returncode=1,
            stdout="",
            stderr='psycopg.errors.UndefinedTable: relation "alembic_version" does not exist\n',
        ),
    )
    args = parse_args(*argv)
    common_flags = start.cli_common_flags(args)
    with pytest.raises(SystemExit) as exc_info:
        start.run_doctor(Path("/venv/python"), common_flags, Path("/tmp/x.env"), args=args)
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert f"运行前自检未通过（目标：{expected_target}）" in err
    assert expected_hint in err
    assert "./start.py --migrate\n" not in err
    assert forbidden_substring not in err


@pytest.mark.parametrize(
    ("mode_argv", "expected_common", "expected_profile", "expected_db"),
    [
        ([], ["--profile", "production"], "production", "ncc-pro"),
        (["--database", "ncc-dev"], ["--profile", "local"], "local", "ncc-dev"),
    ],
)
def test_main_forwards_common_flags_to_check_migrate_and_create_user(
    mode_argv: list[str],
    expected_common: list[str],
    expected_profile: str,
    expected_db: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_py = Path("/fake/.venv/bin/python")
    fake_cfg = Path("/fake/config/.env")
    cli_calls: list[list[str]] = []
    doctor_calls: list[list[str]] = []

    monkeypatch.setattr(start, "ensure_python_runtime", lambda **_kw: fake_py)
    monkeypatch.setattr(start, "ensure_config_initialized", lambda *_a, **_kw: fake_cfg)
    monkeypatch.setattr(start, "ensure_frontend_dist", MagicMock())

    def fake_run_cli_step(_py: Path, sub_args: list[str], *, capture: bool = False):
        cli_calls.append(list(sub_args))
        return subprocess.CompletedProcess(args=sub_args, returncode=0, stdout="", stderr="")

    def fake_run_doctor(_py: Path, common_flags: list[str], _cfg: Path, **_kw):
        doctor_calls.append(list(common_flags))
        return {}

    monkeypatch.setattr(start, "run_cli_step", fake_run_cli_step)
    monkeypatch.setattr(start, "run_doctor", fake_run_doctor)

    # 1) --check + --migrate: both migrate step and doctor step receive identical common_flags,
    #    and empty doctor dict falls back to effective_profile(args) rather than hardcoded "local".
    rc_check = start.main([*mode_argv, "--migrate", "--check"])
    assert rc_check == 0
    assert cli_calls == [[*expected_common, "migrate"]]
    assert doctor_calls == [expected_common]
    out = capsys.readouterr().out
    assert f"profile={expected_profile}" in out

    # 2) --create-user: forwards identical common_flags and exits before doctor.
    cli_calls.clear()
    doctor_calls.clear()
    rc_user = start.main([*mode_argv, "--create-user", "author_admin_demo"])
    assert rc_user == 0
    assert cli_calls == [[*expected_common, "create-user", "author_admin_demo"]]
    assert doctor_calls == []
    assert expected_db == ("ncc-pro" if expected_profile == "production" else "ncc-dev")
