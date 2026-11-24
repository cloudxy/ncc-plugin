import json
from pathlib import Path

import pytest

from ncc_data.creation.subscription_auth import (
    collect_subscriptions,
    normalize_model,
    open_login,
    verify_channel,
)
from ncc_shared.errors import DomainError


class Completed:
    def __init__(self, code, stdout="", stderr=""):
        self.returncode = code
        self.stdout = stdout
        self.stderr = stderr


def test_grok_login_file_does_not_leave_the_token(tmp_path: Path):
    secret = "sk-live-secret-value-abcdef"
    auth = tmp_path / ".grok" / "auth.json"
    auth.parent.mkdir()
    auth.write_text(
        json.dumps(
            {
                "account": {
                    "key": secret,
                    "email": "author@example.com",
                    "expires_at": "2099-01-01T00:00:00Z",
                }
            }
        ),
        encoding="utf-8",
    )
    view = collect_subscriptions({}, home=tmp_path, which=lambda name: None, run=lambda *args, **kwargs: Completed(1))
    rendered = json.dumps(view)
    assert secret not in rendered
    assert "refresh_token" not in rendered
    grok = next(row for row in view["channels"] if row["id"] == "grok")
    assert grok["status"]["ready"] is True
    assert grok["status"]["account"] == "au***@example.com"
    assert grok["model"] == "image_edit"


def test_expired_grok_login_is_not_treated_as_an_api_key(tmp_path: Path):
    secret = "sk-expired-secret-value-zzzz"
    auth = tmp_path / ".grok" / "auth.json"
    auth.parent.mkdir()
    auth.write_text(
        json.dumps({"account": {"key": secret, "email": "author@example.com", "expires_at": "2000-01-01T00:00:00Z"}}),
        encoding="utf-8",
    )
    view = collect_subscriptions({}, home=tmp_path, which=lambda name: "/bin/grok" if name == "grok" else None)
    grok = next(row for row in view["channels"] if row["id"] == "grok")
    assert grok["status"]["status"] == "expired"
    assert grok["status"]["ready"] is False
    assert secret not in json.dumps(view)


def test_codex_subscription_is_separate_from_an_api_key_login():
    secret = "sk-codex-output-must-not-leak"

    def which(name):
        return "/bin/codex" if name == "codex" else None

    def run(argv, **kwargs):
        assert argv == ["/bin/codex", "login", "status"]
        assert "OPENAI_API_KEY" not in kwargs["env"]
        return Completed(0, f"Logged in using ChatGPT\n{secret}\n")

    ready = collect_subscriptions({}, home=Path("/nowhere"), which=which, run=run, env={})
    codex = next(row for row in ready["channels"] if row["id"] == "codex")
    assert codex["status"]["ready"] is True
    assert secret not in json.dumps(ready)

    def run_key(argv, **kwargs):
        return Completed(0, "Logged in using an API key")

    keyed = collect_subscriptions({}, home=Path("/nowhere"), which=which, run=run_key, env={})
    status = next(row for row in keyed["channels"] if row["id"] == "codex")["status"]
    assert status["status"] == "api_key_only"
    assert status["ready"] is False


def test_verify_does_not_return_cli_output_and_rejects_empty_success(tmp_path: Path):
    def which(name):
        return "/bin/agy" if name == "agy" else None

    state = tmp_path / ".gemini" / "antigravity-cli" / "jetski_state.pbtxt"
    state.parent.mkdir(parents=True)
    state.write_text('ui_theme: "dark"\n', encoding="utf-8")

    # Theme-only state file is file_detected, NOT authorized or counted in ready_count
    unverified_view = collect_subscriptions(
        {}, home=tmp_path, which=which, run=lambda *args, **kwargs: Completed(1)
    )
    agy_row = next(row for row in unverified_view["channels"] if row["id"] == "agy")
    assert agy_row["status"]["status"] == "file_detected"
    assert agy_row["status"]["cli_installed"] is True
    assert agy_row["status"]["ready"] is False
    assert unverified_view["ready_count"] == 0

    # Empty output with exit code 0 is NOT verified or authorized
    empty_status = verify_channel("agy", tmp_path, which, lambda *a, **k: Completed(0, ""), env={})
    assert empty_status["verified"] is False
    assert empty_status["ready"] is False
    assert empty_status["status"] == "check_failed"

    def run(argv, **kwargs):
        return Completed(0, "models: image-generator\nsk-verify-secret-value\n")

    status = verify_channel("agy", tmp_path, which, run, env={})
    assert status["verified"] is True
    assert status["ready"] is True
    assert status["status"] == "authorized"
    assert "sk-verify-secret-value" not in json.dumps(status)


def test_model_names_reject_secrets_and_login_stays_on_the_allowlist():
    assert normalize_model("grok", "grok-imagine-image") == "grok-imagine-image"
    with pytest.raises(DomainError):
        normalize_model("codex", "sk-live-secret-value")
    with pytest.raises(DomainError):
        open_login("other", which=lambda name: None)

    def which(name):
        if name == "osascript":
            return None
        return "/bin/grok" if name == "grok" else None

    result = open_login("grok", which=which, run=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("ran")))
    assert result["started"] is False
    assert result["command"] == "grok login --oauth"
