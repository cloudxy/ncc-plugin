"""Isolated synthetic CLI binaries and home directory for browser/integration verification.

Ensures browser acceptance runs NEVER invoke real host OAuth CLIs and NEVER expose
masked real host accounts in screenshots or test artifacts.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import stat
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

from ncc_data.application import subscription_settings
from ncc_data.creation import model_route, subscription_auth

SYNTHETIC_GROK_EMAIL = "test-grok@ncc.example"
SYNTHETIC_GROK_MASKED = "te***@ncc.example"
SYNTHETIC_GROK_AUTH_URL = "https://auth.ncc.test/device"
SYNTHETIC_GROK_DEVICE_CODE = "SYNTH-4829"


def _write_exec(path: Path, body: str) -> None:
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


@contextlib.contextmanager
def synthetic_subscription_env() -> Iterator[dict[str, str]]:
    """Temporarily redirect subscription auth probes & OAuth login CLIs to deterministic synthetic stubs."""
    with tempfile.TemporaryDirectory(prefix="ncc-synth-sub-") as raw_root:
        root = Path(raw_root)
        fake_home = root / "home"
        fake_bin = root / "bin"
        (fake_home / ".grok").mkdir(parents=True, exist_ok=True)
        (fake_home / ".gemini" / "antigravity-cli").mkdir(parents=True, exist_ok=True)
        fake_bin.mkdir(parents=True, exist_ok=True)

        # Synthetic Grok local auth file (clearly synthetic test account, never real host credentials)
        (fake_home / ".grok" / "auth.json").write_text(
            json.dumps(
                {
                    "default": {
                        "key": "synthetic-test-placeholder-0000",
                        "email": SYNTHETIC_GROK_EMAIL,
                        "expires_at": "2099-01-01T00:00:00Z",
                    }
                }
            ),
            encoding="utf-8",
        )
        # Synthetic AGY local state marker (triggers file_detected -> verifiable via synthetic agy stub)
        (fake_home / ".gemini" / "antigravity-cli" / "jetski_state.pbtxt").write_text(
            "synthetic_test_state: true\n",
            encoding="utf-8",
        )

        # Synthetic grok CLI stub: deterministic Device-Auth code + clean SIGTERM exit
        _write_exec(
            fake_bin / "grok",
            f"""import signal, sys, time
args = sys.argv[1:]
if len(args) >= 2 and args[0] == "login" and "--device-auth" in args:
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    print("Open {SYNTHETIC_GROK_AUTH_URL} in your browser", flush=True)
    print("Enter code: {SYNTHETIC_GROK_DEVICE_CODE}", flush=True)
    for _ in range(120):
        time.sleep(0.5)
    sys.exit(0)
if args == ["models"]:
    print("grok-4\\ngrok-3\\nimage_edit", flush=True)
    sys.exit(0)
sys.exit(0)
""",
        )

        # Synthetic codex CLI stub: deterministic ChatGPT subscription login status
        _write_exec(
            fake_bin / "codex",
            """import signal, sys, time
args = sys.argv[1:]
if args == ["login", "status"]:
    print("Logged in using ChatGPT", flush=True)
    sys.exit(0)
if len(args) >= 2 and args[0] == "login" and "--device-auth" in args:
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    print("Open https://auth.ncc.test/codex in your browser", flush=True)
    print("Enter code: CODX-7315", flush=True)
    for _ in range(120):
        time.sleep(0.5)
    sys.exit(0)
sys.exit(0)
""",
        )

        # Synthetic agy CLI stub: deterministic models output matching local agy models
        _write_exec(
            fake_bin / "agy",
            """import sys
args = sys.argv[1:]
if args == ["models"]:
    print("gemini-4-neon-high   Gemini 4 Neon (High)", flush=True)
    print("gemini-4-neon-xhigh  Gemini 4 Neon (XHigh)", flush=True)
    sys.exit(0)
sys.exit(0)
""",
        )

        class _SyntheticHomePath(Path):
            @classmethod
            def home(cls) -> Path:
                return fake_home

        orig_path_env = os.environ.get("PATH", "")
        orig_sub_auth_path = subscription_auth.Path
        orig_sub_set_path = subscription_settings.Path
        orig_route_path = model_route.Path

        os.environ["PATH"] = f"{fake_bin}{os.pathsep}{orig_path_env}"
        subscription_auth.Path = _SyntheticHomePath
        subscription_settings.Path = _SyntheticHomePath
        model_route.Path = _SyntheticHomePath
        try:
            yield {
                "home": str(fake_home),
                "bin": str(fake_bin),
                "grok_account_masked": SYNTHETIC_GROK_MASKED,
                "grok_auth_url": SYNTHETIC_GROK_AUTH_URL,
                "grok_device_code": SYNTHETIC_GROK_DEVICE_CODE,
            }
        finally:
            # Cleanly close any lingering managed login stub sessions
            sessions = list(subscription_auth._SESSIONS_BY_ID.values())
            subscription_auth._ACTIVE_BY_PROVIDER.clear()
            subscription_auth._SESSIONS_BY_ID.clear()
            for sess in sessions:
                proc = getattr(sess, "proc", None)
                if proc is not None and getattr(proc, "returncode", None) is None:
                    with contextlib.suppress(ProcessLookupError, OSError):
                        proc.terminate()
            with contextlib.suppress(Exception):
                asyncio.run(subscription_auth._sweep_expired_sessions())
            os.environ["PATH"] = orig_path_env
            subscription_auth.Path = orig_sub_auth_path
            subscription_settings.Path = orig_sub_set_path
            model_route.Path = orig_route_path
