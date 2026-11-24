from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ncc_data.application.security import (
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USERNAME,
    credential_change_policy,
    default_bootstrap_password_hash,
    password_hash,
    password_matches,
)
from ncc_data.runtime.settings import Settings
from ncc_shared.errors import DomainError
from ncc_shared.http import extract_hostname, is_loopback_host

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import start  # noqa: E402


def _fake_request(host_header: str = "", url_hostname: str = ""):
    return SimpleNamespace(
        headers={"host": host_header} if host_header else {},
        url=SimpleNamespace(hostname=url_hostname),
    )


@pytest.mark.parametrize(
    ("raw", "expected_host", "expected_loopback"),
    [
        ("127.0.0.1", "127.0.0.1", True),
        ("127.0.0.1:8761", "127.0.0.1", True),
        ("http://127.0.0.1:8761", "127.0.0.1", True),
        ("localhost", "localhost", True),
        ("LOCALHOST:8761", "localhost", True),
        ("http://localhost:8761/api", "localhost", True),
        ("::1", "::1", True),
        ("[::1]", "::1", True),
        ("[::1]:8761", "::1", True),
        ("http://[::1]:8761", "::1", True),
        ("0.0.0.0", "0.0.0.0", False),
        ("0.0.0.0:8761", "0.0.0.0", False),
        ("::", "::", False),
        ("[::]:8761", "::", False),
        ("192.168.1.10", "192.168.1.10", False),
        ("192.168.1.10:8761", "192.168.1.10", False),
        ("https://192.168.1.10:8761", "192.168.1.10", False),
        ("203.0.113.25", "203.0.113.25", False),
        ("https://ncc.example.com", "ncc.example.com", False),
        ("", "", False),
    ],
)
def test_extract_hostname_and_is_loopback_host(
    raw: str, expected_host: str, expected_loopback: bool
) -> None:
    assert extract_hostname(raw) == expected_host
    assert is_loopback_host(raw) is expected_loopback


def test_credential_change_policy_inactive_for_regular_users() -> None:
    normal_user = SimpleNamespace(must_change_credentials=False)
    settings = Settings(database_url="postgresql://unused/unused", public_origin="https://203.0.113.10")
    req = _fake_request("203.0.113.10:8761")
    assert credential_change_policy(req, settings, normal_user, bind_host="0.0.0.0") == (False, False, "")


@pytest.mark.parametrize(
    ("bind_host", "origin", "host_header", "expected_enforced"),
    [
        ("127.0.0.1", "http://127.0.0.1:8761", "127.0.0.1:8761", False),
        ("localhost", "http://localhost:8761", "localhost:8761", False),
        ("::1", "http://[::1]:8761", "[::1]:8761", False),
        (None, "http://127.0.0.1:8761", "testserver", False),
        ("0.0.0.0", "http://127.0.0.1:8761", "127.0.0.1:8761", True),
        ("::", "http://127.0.0.1:8761", "127.0.0.1:8761", True),
        ("192.168.1.10", "http://127.0.0.1:8761", "testserver", True),
        ("203.0.113.9", "http://127.0.0.1:8761", "127.0.0.1:8761", True),
        ("127.0.0.1", "https://192.168.1.10:8761", "127.0.0.1:8761", True),
        ("127.0.0.1", "https://ncc.example.com", "127.0.0.1:8761", True),
        ("127.0.0.1", "http://127.0.0.1:8761", "192.168.1.10:8761", True),
        (None, "http://127.0.0.1:8761", "203.0.113.9:8761", True),
    ],
)
def test_credential_change_policy_loopback_vs_real_host(
    bind_host: str | None,
    origin: str,
    host_header: str,
    expected_enforced: bool,
) -> None:
    admin_user = SimpleNamespace(must_change_credentials=True)
    settings = Settings(database_url="postgresql://unused/unused", public_origin=origin)
    req = _fake_request(host_header)
    must_change, enforced, reminder = credential_change_policy(req, settings, admin_user, bind_host=bind_host)
    assert must_change is True
    assert enforced is expected_enforced
    assert DEFAULT_ADMIN_USERNAME in reminder
    if expected_enforced:
        assert "真实地址" in reminder and "必须" in reminder
    else:
        assert reminder == "首次使用默认管理员账号（admin），请及时修改账号名和密码。"


def test_password_hash_keeps_12_char_floor_while_bootstrap_hashes_default() -> None:
    assert DEFAULT_ADMIN_USERNAME == "admin"
    assert DEFAULT_ADMIN_PASSWORD == "123456"
    with pytest.raises(DomainError) as exc_info:
        password_hash("123456")
    assert exc_info.value.code == "weak_password"
    with pytest.raises(DomainError):
        password_hash("short-11chr")

    boot_hash = default_bootstrap_password_hash()
    assert boot_hash.startswith("scrypt$")
    assert password_matches("123456", boot_hash) is True
    assert password_matches("654321", boot_hash) is False


@pytest.mark.parametrize(
    ("host", "default_active", "expected_snippet"),
    [
        ("127.0.0.1", False, None),
        (
            "127.0.0.1",
            True,
            "[ncc] 安全提醒：当前正在使用默认管理员账号（admin / 123456），"
            "第一次使用时请进入后台修改账号与密码（当前监听回环地址，仅作提醒）。",
        ),
        (
            "localhost",
            True,
            "当前监听回环地址，仅作提醒",
        ),
        (
            "::1",
            True,
            "当前监听回环地址，仅作提醒",
        ),
        (
            "0.0.0.0",
            True,
            "[ncc] 安全强制策略：当前监听非回环地址（0.0.0.0）且仍在使用默认管理员账号，"
            "首次登录后台将强制要求修改账号与密码！",
        ),
        (
            "192.168.1.10",
            True,
            "[ncc] 安全强制策略：当前监听非回环地址（192.168.1.10）且仍在使用默认管理员账号，"
            "首次登录后台将强制要求修改账号与密码！",
        ),
    ],
)
def test_start_launcher_default_admin_notice_by_host(
    host: str,
    default_active: bool,
    expected_snippet: str | None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(start, "ensure_python_runtime", lambda **_kw: Path("/fake/python"))
    monkeypatch.setattr(start, "ensure_config_initialized", lambda *_a, **_kw: Path("/fake/.env"))
    monkeypatch.setattr(start, "ensure_frontend_dist", MagicMock())
    monkeypatch.setattr(
        start,
        "run_cli_step",
        lambda *_a, **_kw: subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(
        start,
        "run_doctor",
        lambda *_a, **_kw: {
            "profile": "production",
            "database": "ncc-pro",
            "frontend_built": True,
            "model_configured": False,
            "default_admin_active": default_active,
            "origin": "http://127.0.0.1:8761",
        },
    )

    rc = start.main(["--host", host, "--check"])
    assert rc == 0
    out = capsys.readouterr().out
    if expected_snippet is None:
        assert "安全提醒：" not in out
        assert "安全强制策略：" not in out
    else:
        assert expected_snippet in out
