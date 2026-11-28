import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ncc_data.application.subscription_settings import save_subscription_model, verify_subscription
from ncc_data.cli.main import _slot_configured
from ncc_data.creation.gateway import ChatProvider
from ncc_data.creation.model_catalog import (
    platforms_catalog,
    subscription_model_entry,
)
from ncc_data.creation.model_route import (
    ResolvedRoute,
    apply_capability_default,
    apply_configuration,
    apply_delete,
    apply_enabled,
    clean_capability_defaults,
    describe,
    ensure_job_route,
    materialize_one,
    normalize_configuration,
    presets,
    snapshot_from,
)
from ncc_data.creation.subscription_auth import (
    cancel_oauth_login,
    collect_single_subscription,
    collect_subscriptions,
    extract_device_auth_info,
    normalize_model,
    open_login,
    poll_oauth_login,
    start_oauth_login,
    subscription_model_capabilities,
    verify_channel,
)
from ncc_data.domain.contracts import CapabilityDefaultInput, ModelConfigurationInput
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
    view = collect_subscriptions(
        {}, home=tmp_path, which=lambda name: None, run=lambda *args, **kwargs: Completed(1)
    )
    rendered = json.dumps(view)
    assert secret not in rendered
    assert "refresh_token" not in rendered
    grok = next(row for row in view["channels"] if row["id"] == "grok")
    assert grok["status"]["ready"] is True
    assert grok["status"]["account"] == "au***@example.com"
    assert grok["model"] == "grok-4"
    assert grok["text_model"] == "grok-4"
    assert grok["image_model"] == "image_edit"
    text_ids = [item["id"] for item in grok["text_models"]]
    image_ids = [item["id"] for item in grok["image_models"]]
    assert "grok-4" in text_ids
    assert "image_edit" in image_ids
    assert "image_edit" not in text_ids
    assert "grok-4" not in image_ids
    model_ids = [item["id"] for item in grok["models"]]
    assert "grok-4" in model_ids
    assert "image_edit" in model_ids


def test_grok_refresh_token_keeps_channel_ready_when_short_access_token_expires(tmp_path: Path):
    access_secret = "sk-short-lived-access-token"
    refresh_secret = "rt-long-lived-refresh-token-xyz"
    auth = tmp_path / ".grok" / "auth.json"
    auth.parent.mkdir()
    auth.write_text(
        json.dumps(
            {
                "https://api.x.ai": {
                    "key": access_secret,
                    "refresh_token": refresh_secret,
                    "email": "writer@example.com",
                    "expires_at": "2000-01-01T00:00:00Z",
                }
            }
        ),
        encoding="utf-8",
    )
    view = collect_subscriptions(
        {},
        home=tmp_path,
        which=lambda name: "/bin/grok" if name == "grok" else None,
        run=lambda *args, **kwargs: Completed(1),
    )
    rendered = json.dumps(view)
    assert access_secret not in rendered
    assert refresh_secret not in rendered
    grok = next(row for row in view["channels"] if row["id"] == "grok")
    assert grok["status"]["ready"] is True
    assert grok["status"]["status"] == "authorized"
    assert view["ready_count"] == 1


def test_expired_grok_login_is_not_treated_as_an_api_key(tmp_path: Path):
    secret = "sk-expired-secret-value-zzzz"
    auth = tmp_path / ".grok" / "auth.json"
    auth.parent.mkdir()
    auth.write_text(
        json.dumps(
            {"account": {"key": secret, "email": "author@example.com", "expires_at": "2000-01-01T00:00:00Z"}}
        ),
        encoding="utf-8",
    )
    view = collect_subscriptions(
        {}, home=tmp_path, which=lambda name: "/bin/grok" if name == "grok" else None
    )
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

    unverified_view = collect_subscriptions(
        {}, home=tmp_path, which=which, run=lambda *args, **kwargs: Completed(1)
    )
    agy_row = next(row for row in unverified_view["channels"] if row["id"] == "agy")
    assert agy_row["status"]["status"] == "file_detected"
    assert agy_row["status"]["cli_installed"] is True
    assert agy_row["status"]["ready"] is False
    assert unverified_view["ready_count"] == 0

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


@pytest.mark.asyncio
async def test_verify_subscription_recomputes_ready_count(monkeypatch):
    class FakeDB:
        def __init__(self):
            self.added = []

        async def get(self, model, key):
            return SimpleNamespace(id=key, version=0, config={})

        def add(self, obj):
            self.added.append(obj)

        async def flush(self):
            return None

    fake_svc = SimpleNamespace(actor=SimpleNamespace(id="admin-1", admin=True), db=FakeDB())
    monkeypatch.setattr(
        "ncc_data.application.subscription_settings.collect_subscriptions",
        lambda saved: {
            "channels": [
                {"id": "grok", "status": {"ready": False, "status": "unauthorized"}},
                {"id": "codex", "status": {"ready": False, "status": "unauthorized"}},
                {"id": "agy", "status": {"ready": False, "status": "file_detected"}},
            ],
            "ready_count": 0,
        },
    )
    monkeypatch.setattr(
        "ncc_data.application.subscription_settings.verify_channel",
        lambda provider, *a, **kw: {
            "ready": True,
            "status": "authorized",
            "cli_installed": True,
            "verified": True,
            "message": "AGY 在线验证通过",
        },
    )
    result = await verify_subscription(fake_svc, "agy")
    assert result["ready_count"] == 1
    agy = next(r for r in result["channels"] if r["id"] == "agy")
    assert agy["status"]["ready"] is True


def test_model_names_reject_secrets_and_login_never_spawns_osascript():
    assert normalize_model("grok", "grok-imagine-image") == "grok-imagine-image"
    assert normalize_model("grok", "grok-4") == "grok-4"
    with pytest.raises(DomainError):
        normalize_model("codex", "sk-live-secret-value")
    with pytest.raises(DomainError):
        open_login("other", which=lambda name: None)

    def which_all_present(name):
        return f"/usr/bin/{name}"

    def forbid_run(*args, **kwargs):
        raise AssertionError("open_login must never spawn osascript or a local terminal")

    for provider, expected_command in (
        ("grok", "grok login --oauth"),
        ("codex", "codex login"),
        ("agy", "agy"),
    ):
        result = open_login(provider, which=which_all_present, run=forbid_run)
        assert result["started"] is False
        assert result["command"] == expected_command
        assert f"请在本地终端执行 {expected_command} 完成授权" in result["message"]
        assert "刷新授权状态" in result["message"]


@pytest.mark.asyncio
async def test_managed_device_auth_lifecycle_zero_osascript_and_redaction(tmp_path: Path):
    url, code = extract_device_auth_info(
        "\x1b[32mOpen https://accounts.x.ai/device in your browser\x1b[0m\n"
        "Enter code: ABCD-9876\n"
        "debug_secret=sk-should-never-appear-1234567890\n"
    )
    assert url == "https://accounts.x.ai/device"
    assert code == "ABCD-9876"

    class FakeStream:
        def __init__(self, payload: bytes):
            self._buf = payload

        async def read(self, n: int = 512) -> bytes:
            if not self._buf:
                await asyncio.sleep(0.02)
                return b""
            chunk, self._buf = self._buf[:n], self._buf[n:]
            return chunk

    class FakeProc:
        def __init__(self, argv: list[str], env: dict[str, str], output: str):
            self.argv = argv
            self.env = env
            self.stdout = FakeStream(output.encode("utf-8"))
            self.returncode: int | None = None
            self.terminated = False

        def terminate(self):
            self.terminated = True
            self.returncode = -15

        def kill(self):
            self.terminated = True
            self.returncode = -9

        async def wait(self):
            if self.returncode is None:
                await asyncio.sleep(0.01)
            return self.returncode

    spawned: list[FakeProc] = []

    async def fake_spawner(argv: list[str], env: dict[str, str]):
        assert "osascript" not in argv[0]
        for forbidden in (
            "XAI_API_KEY",
            "OPENAI_API_KEY",
            "NCC_MODEL_KEY",
            "ARK_API_KEY",
            "DEEPSEEK_API_KEY",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
        ):
            assert forbidden not in env
        proc = FakeProc(
            argv,
            env,
            "Visit https://auth.openai.com/codex/device and enter code WXYZ-4321\nsk-secret-token-leak-check\n",
        )
        spawned.append(proc)
        return proc

    manual_agy = await start_oauth_login(
        "agy",
        home=tmp_path,
        which=lambda name: f"/usr/local/bin/{name}",
        spawner=fake_spawner,
    )
    assert manual_agy["mode"] == "manual"
    assert manual_agy["started"] is False
    assert manual_agy["state"] == "manual"
    assert manual_agy["command"] == "agy"
    assert len(spawned) == 0

    started = await start_oauth_login(
        "codex",
        home=tmp_path,
        which=lambda name: f"/usr/local/bin/{name}",
        run=lambda *a, **kw: Completed(1, "Not logged in"),
        spawner=fake_spawner,
        env={
            "OPENAI_API_KEY": "sk-must-be-stripped-123456789",
            "ANTHROPIC_API_KEY": "sk-ant-must-be-stripped",
            "GEMINI_API_KEY": "gemini-must-be-stripped",
            "GOOGLE_API_KEY": "google-must-be-stripped",
        },
        startup_wait=0.5,
    )
    assert started["mode"] == "device_auth"
    assert started["started"] is True
    assert started["state"] == "pending"
    assert started["auth_url"] == "https://auth.openai.com/codex/device"
    assert started["device_code"] == "WXYZ-4321"
    assert "sk-secret-token-leak-check" not in json.dumps(started)
    assert spawned[0].argv == ["/usr/local/bin/codex", "login", "--device-auth"]

    # Starting a second session for the same provider terminates the previous process
    started2 = await start_oauth_login(
        "codex",
        home=tmp_path,
        which=lambda name: f"/usr/local/bin/{name}",
        run=lambda *a, **kw: Completed(1, "Not logged in"),
        spawner=fake_spawner,
        startup_wait=0.5,
    )
    assert spawned[0].terminated is True
    sid2 = started2["session_id"]

    # List & single-channel refresh MUST NOT expose device_code or auth_url in active_session summary!
    list_during_auth = collect_subscriptions(
        {},
        home=tmp_path,
        which=lambda name: f"/usr/local/bin/{name}",
        run=lambda *a, **kw: Completed(1, "Not logged in"),
    )
    codex_list_summary = next(r for r in list_during_auth["channels"] if r["id"] == "codex")["active_session"]
    assert codex_list_summary is not None
    assert codex_list_summary["session_id"] == sid2
    assert "device_code" not in codex_list_summary
    assert "auth_url" not in codex_list_summary
    assert "WXYZ-4321" not in json.dumps(list_during_auth)
    assert "auth.openai.com/codex/device" not in json.dumps(list_during_auth)

    single_during_auth = collect_single_subscription(
        "codex",
        {},
        home=tmp_path,
        which=lambda name: f"/usr/local/bin/{name}",
        run=lambda *a, **kw: Completed(1, "Not logged in"),
    )
    assert single_during_auth["active_session"]["session_id"] == sid2
    assert "device_code" not in single_during_auth["active_session"]
    assert "auth_url" not in single_during_auth["active_session"]

    # Simulate user completing device-auth in browser
    spawned[1].returncode = 0
    polled = await poll_oauth_login(
        "codex",
        sid2,
        home=tmp_path,
        which=lambda name: f"/usr/local/bin/{name}",
        run=lambda *a, **kw: Completed(0, "Logged in using ChatGPT"),
    )
    assert polled["state"] == "authorized"
    assert polled["channel"]["status"]["ready"] is True
    assert "sk-secret-token-leak-check" not in json.dumps(polled)

    cancelled = await cancel_oauth_login("codex", sid2)
    assert cancelled == {"cancelled": True}


@pytest.mark.asyncio
async def test_cli_oauth_model_route_and_chat_provider_call(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("XAI_API_KEY", "sk-env-xai-key-should-be-stripped")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-openai-key-should-be-stripped")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env-key-should-be-stripped")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-env-key-should-be-stripped")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-env-key-should-be-stripped")

    cfg = normalize_configuration(
        ModelConfigurationInput(
            name="Grok 订阅写作",
            transport="cli_oauth",
            cli_provider="grok",
            model_key="grok-4",
            purposes=["plan", "write", "revise", "judge"],
            enabled=True,
        )
    )
    assert cfg["transport"] == "cli_oauth"
    assert cfg["cli_provider"] == "grok"
    assert cfg["base_url"] == ""
    assert cfg["enabled"] is True

    auth = tmp_path / ".grok" / "auth.json"
    auth.parent.mkdir()
    auth.write_text(
        json.dumps({"xai": {"key": "sk-local-oauth-token", "refresh_token": "rt-ok", "expires_at": "2000-01-01T00:00:00Z"}}),
        encoding="utf-8",
    )
    fake_settings = SimpleNamespace(
        model_url="",
        model_key="",
        writer_model="",
        judge_model="",
        second_judge_model="",
        model_timeout=15.0,
        cli_home=tmp_path,
        cli_which=lambda name: f"/usr/local/bin/{name}",
        cli_run=lambda *a, **kw: Completed(0, "Logged in using ChatGPT"),
    )

    preset_ids = [p["id"] for p in presets(fake_settings)]
    assert preset_ids[0] == "environment"
    assert {"cli-grok", "cli-codex", "cli-agy"} <= set(preset_ids)

    registry_scope = {
        "model_registry": {
            "configurations": [{**cfg, "id": "cli-grok-1"}],
            "defaults": {"write": "cli-grok-1", "judge": "cli-grok-1"},
        }
    }
    desc = describe(registry_scope, fake_settings)
    assert desc["configurations"][0]["connection"]["status"] == "loaded"
    assert desc["configurations"][0]["connection"]["credential"] == "present"
    assert "sk-local-oauth-token" not in json.dumps(desc)

    snap = snapshot_from(registry_scope, fake_settings)
    write_slot = snap["by_purpose"]["write"]
    assert write_slot["transport"] == "cli_oauth"
    assert write_slot["cli_provider"] == "grok"
    assert _slot_configured(write_slot) is True

    pinned = ensure_job_route(snap)
    assert pinned["by_purpose"]["write"]["transport"] == "cli_oauth"
    resolved = materialize_one(pinned["by_purpose"]["write"], fake_settings)
    assert resolved == ResolvedRoute(
        base_url="",
        api_key="",
        model="grok-4",
        transport="cli_oauth",
        cli_provider="grok",
    )

    captured = {}

    def fake_cli_runner(provider, model, system, prompt, timeout, clean_env):
        captured["provider"] = provider
        captured["model"] = model
        captured["env"] = dict(clean_env)
        return '```json\n{"text": "风雪夜归人。", "data": {}, "claims": []}\n```'

    chat = ChatProvider(fake_settings, cli_runner=fake_cli_runner)
    chat.route = resolved
    result, meta = await chat.call("write", {"objective": "写一段开场"}, budget=8000)
    assert result["text"] == "风雪夜归人。"
    assert meta["kind"] == "cli_oauth_estimate"
    assert meta["provider"] == "grok"
    assert meta["model"] == "grok-4"
    assert captured["provider"] == "grok"
    assert "XAI_API_KEY" not in captured["env"]
    assert "OPENAI_API_KEY" not in captured["env"]
    assert "ANTHROPIC_API_KEY" not in captured["env"]
    assert "GEMINI_API_KEY" not in captured["env"]
    assert "GOOGLE_API_KEY" not in captured["env"]

    with pytest.raises(DomainError) as exc_info:
        await chat.call("write", {"objective": "预算不足检查"}, budget=300)
    assert exc_info.value.code == "token_budget"


@pytest.mark.asyncio
async def test_subscription_text_and_image_models_persist_independently(monkeypatch):
    legacy_view = collect_subscriptions(
        {
            "grok": {"model": "grok-imagine-image-2.0"},
            "codex": {"model": "o3"},
        },
        home=Path("/nowhere"),
        which=lambda name: None,
        run=lambda *a, **kw: Completed(1),
    )
    by_id = {row["id"]: row for row in legacy_view["channels"]}
    assert by_id["grok"]["text_model"] == "grok-4"
    assert by_id["grok"]["image_model"] == "grok-imagine-image-2.0"
    assert by_id["codex"]["text_model"] == "o3"
    assert by_id["codex"]["image_model"] == "image-generation"
    assert by_id["agy"]["text_model"] == "gemini-4-neon-high"
    assert by_id["agy"]["image_model"] == "image-generator"
    agy_text_ids = [item["id"] for item in by_id["agy"]["text_models"]]
    assert "gemini-4-neon-high" in agy_text_ids
    assert "gemini-4-neon-xhigh" in agy_text_ids

    # Previously saved historical AGY preference (gemini-2.5-pro) is preserved verbatim without being overwritten
    historical_agy = collect_subscriptions(
        {"agy": {"text_model": "gemini-2.5-pro"}},
        home=Path("/nowhere"),
        which=lambda name: None,
        run=lambda *a, **kw: Completed(1),
    )
    hist_agy_row = next(row for row in historical_agy["channels"] if row["id"] == "agy")
    assert hist_agy_row["text_model"] == "gemini-2.5-pro"

    scope = SimpleNamespace(id="system", version=1, config={})

    class FakeDB:
        def __init__(self):
            self.added = []

        async def scalar(self, stmt):
            return scope

        def add(self, obj):
            self.added.append(obj)

        async def flush(self):
            return None

    fake_svc = SimpleNamespace(actor=SimpleNamespace(id="admin-1", admin=True), db=FakeDB())
    monkeypatch.setattr(
        "ncc_data.application.subscription_settings.collect_subscriptions",
        lambda saved: collect_subscriptions(
            saved, home=Path("/nowhere"), which=lambda name: None, run=lambda *a, **kw: Completed(1)
        ),
    )

    both = await save_subscription_model(
        fake_svc,
        "grok",
        text_model="grok-3",
        image_model="grok-imagine-image-2.0",
    )
    grok = next(row for row in both["channels"] if row["id"] == "grok")
    assert grok["text_model"] == "grok-3"
    assert grok["model"] == "grok-3"
    assert grok["image_model"] == "grok-imagine-image-2.0"

    text_only = await save_subscription_model(fake_svc, "grok", text_model="grok-4-fast")
    grok = next(row for row in text_only["channels"] if row["id"] == "grok")
    assert grok["text_model"] == "grok-4-fast"
    assert grok["image_model"] == "grok-imagine-image-2.0"

    image_only = await save_subscription_model(fake_svc, "grok", image_model="grok-imagine-image")
    grok = next(row for row in image_only["channels"] if row["id"] == "grok")
    assert grok["text_model"] == "grok-4-fast"
    assert grok["image_model"] == "grok-imagine-image"

    with pytest.raises(DomainError):
        await save_subscription_model(fake_svc, "grok", text_model="sk-secret-key-123456")
    with pytest.raises(DomainError):
        await save_subscription_model(fake_svc, "grok", image_model="my-access-token")


def test_six_capability_defaults_validation_video_fallback_and_text_routing():
    # Official vendor evidence: distinguish callable models vs built-in CLI tools, and API-only models vs CLI channels
    assert subscription_model_capabilities("grok", "grok-4") == (("text",), "catalog")
    assert subscription_model_entry("grok", "grok-4")["entry_kind"] == "model"
    assert subscription_model_capabilities("grok", "image_edit") == (("text_to_image", "image_to_image"), "catalog")
    assert subscription_model_entry("grok", "image_edit")["entry_kind"] == "builtin_tool"
    # xAI video/image API models are NOT assumed available on grok CLI subscription without channel evidence
    assert subscription_model_capabilities("grok", "grok-imagine-video") == ((), "unknown")
    assert subscription_model_capabilities("codex", "image-generation") == (("text_to_image", "image_to_image"), "catalog")
    assert subscription_model_entry("codex", "image-generation")["entry_kind"] == "builtin_tool"
    assert subscription_model_capabilities("codex", "gpt-image-1") == ((), "unknown")
    assert subscription_model_capabilities("agy", "gemini-4-neon-high") == (("text",), "catalog")
    assert subscription_model_capabilities("agy", "gemini-4-neon-xhigh") == (("text",), "catalog")
    assert subscription_model_entry("agy", "gemini-4-neon-xhigh")["entry_kind"] == "model"
    assert subscription_model_capabilities("agy", "image-generator") == (("text_to_image", "image_to_image"), "catalog")
    assert subscription_model_entry("agy", "image-generator")["entry_kind"] == "builtin_tool"
    assert subscription_model_capabilities("agy", "gemini-2.5-pro") == ((), "unknown")
    assert subscription_model_capabilities("grok", "custom-video-image-text-99") == ((), "unknown")

    # OpenAI API catalog uses non-deprecated gpt-image-1.5 / gpt-image-1-mini (not deprecated gpt-image-1)
    openai_platform = next(p for p in platforms_catalog() if p["id"] == "openai")
    openai_ids = [m["id"] for m in openai_platform["models"]]
    assert "gpt-image-1.5" in openai_ids
    assert "gpt-image-1" not in openai_ids

    api_text = {
        **normalize_configuration(
            ModelConfigurationInput(
                name="DeepSeek 文本",
                supplier="DeepSeek",
                platform_id="deepseek",
                base_url="https://api.deepseek.com",
                auth_ref="DEEPSEEK_API_KEY",
                model_key="deepseek-reasoner",
                capabilities=["text"],
                purposes=["judge"],
                enabled=True,
            )
        ),
        "id": "api-judge",
    }
    api_t2v = {
        **normalize_configuration(
            ModelConfigurationInput(
                name="方舟文生视频",
                supplier="火山方舟",
                platform_id="ark",
                base_url="https://ark.cn-beijing.volces.com/api/v3",
                auth_ref="ARK_API_KEY",
                model_key="doubao-seedance-1-0-lite-t2v-250428",
                capabilities=["video", "text_to_video"],
                purposes=[],
                enabled=True,
            )
        ),
        "id": "api-t2v",
    }
    api_i2v = {
        **normalize_configuration(
            ModelConfigurationInput(
                name="方舟图生视频",
                supplier="火山方舟",
                platform_id="ark",
                base_url="https://ark.cn-beijing.volces.com/api/v3",
                auth_ref="ARK_API_KEY",
                model_key="doubao-seedance-1-0-lite-i2v-250428",
                capabilities=["video", "image_to_video"],
                purposes=[],
                enabled=True,
            )
        ),
        "id": "api-i2v",
    }
    api_disabled = {
        **normalize_configuration(
            ModelConfigurationInput(
                name="停用历史生图",
                supplier="OpenAI",
                platform_id="openai",
                base_url="https://api.openai.com/v1",
                auth_ref="OPENAI_API_KEY",
                model_key="gpt-image-1",
                capabilities=["text_to_image", "image_to_image"],
                purposes=[],
                enabled=False,
            )
        ),
        "id": "api-img-off",
    }
    legacy_cli_row = {
        **normalize_configuration(
            ModelConfigurationInput(
                name="旧 Grok 审评 CLI",
                transport="cli_oauth",
                cli_provider="grok",
                model_key="grok-3",
                capabilities=["text"],
                purposes=["write", "judge"],
                enabled=True,
            )
        ),
        "id": "legacy-cli-1",
    }
    registry = {
        "configurations": [api_text, api_t2v, api_i2v, api_disabled, legacy_cli_row],
        "defaults": {"plan": "", "write": "", "revise": "", "judge": "api-judge", "judge_secondary": ""},
    }

    # Bind global text default to subscription grok-4, text_to_image to grok image_edit,
    # image_to_image to codex image-generation, video to api-t2v (text_to_video ONLY!)
    caps = {}
    caps = apply_capability_default(
        registry,
        caps,
        CapabilityDefaultInput(capability="text", source="subscription", provider="grok", model_key="grok-4"),
    )
    caps = apply_capability_default(
        registry,
        caps,
        CapabilityDefaultInput(
            capability="text_to_image", source="subscription", provider="grok", model_key="image_edit"
        ),
    )
    caps = apply_capability_default(
        registry,
        caps,
        CapabilityDefaultInput(
            capability="image_to_image", source="subscription", provider="codex", model_key="image-generation"
        ),
    )
    caps = apply_capability_default(
        registry,
        caps,
        CapabilityDefaultInput(
            capability="video",
            source="api",
            configuration_id="api-t2v",
            model_key="doubao-seedance-1-0-lite-t2v-250428",
        ),
    )

    # Reject: incompatible video modes, unknown subscription model, disabled API config,
    # spoofing a cli_oauth row as source="api", and stale/mismatched model_key!
    for bad_input in (
        CapabilityDefaultInput(
            capability="image_to_video",
            source="api",
            configuration_id="api-t2v",
            model_key="doubao-seedance-1-0-lite-t2v-250428",
        ),
        CapabilityDefaultInput(
            capability="text_to_video",
            source="api",
            configuration_id="api-i2v",
            model_key="doubao-seedance-1-0-lite-i2v-250428",
        ),
        CapabilityDefaultInput(
            capability="text_to_image", source="subscription", provider="grok", model_key="grok-4"
        ),
        CapabilityDefaultInput(
            capability="text", source="subscription", provider="grok", model_key="custom-unlisted-model"
        ),
        CapabilityDefaultInput(
            capability="text_to_image",
            source="api",
            configuration_id="api-img-off",
            model_key="gpt-image-1",
        ),
        CapabilityDefaultInput(
            capability="text",
            source="api",
            configuration_id="legacy-cli-1",
            model_key="grok-3",
        ),
        CapabilityDefaultInput(
            capability="text",
            source="api",
            configuration_id="api-judge",
            model_key="stale-different-model",
        ),
    ):
        with pytest.raises(DomainError):
            apply_capability_default(registry, caps, bad_input)

    fake_settings = SimpleNamespace(
        model_url="",
        model_key="",
        writer_model="",
        judge_model="",
        second_judge_model="",
        cli_home=Path("/nowhere"),
        cli_which=lambda name: None,
        cli_run=lambda *a, **kw: Completed(1),
    )
    scope_cfg = {"model_registry": registry, "capability_defaults": caps}
    desc = describe(scope_cfg, fake_settings)

    # Historical deprecated gpt-image-1 config remains visible with deprecated_notice;
    # cli_oauth row is NOT listed as an API candidate!
    hist_cfg = next(c for c in desc["configurations"] if c["id"] == "api-img-off")
    assert "已停用" in hist_cfg["deprecated_notice"]
    api_text_candidate_ids = [
        c["configuration_id"] for c in desc["capability_candidates"]["text"] if c["source"] == "api"
    ]
    assert "legacy-cli-1" not in api_text_candidate_ids

    # Fallback classification: when capability_defaults['text'] is unset and write falls back to legacy_cli_row,
    # source MUST be classified as 'subscription', NEVER 'api'!
    legacy_only_desc = describe(
        {
            "model_registry": {
                "configurations": [legacy_cli_row],
                "defaults": {"write": "legacy-cli-1"},
            }
        },
        fake_settings,
    )
    assert legacy_only_desc["effective_capabilities"]["text"]["source"] == "subscription"
    assert legacy_only_desc["effective_capabilities"]["text"]["fallback_from"] == "legacy_cli_route"

    # Generic video fallback applies ONLY to text_to_video (matching input), NEVER to image_to_video!
    eff_t2v = desc["effective_capabilities"]["text_to_video"]
    eff_i2v = desc["effective_capabilities"]["image_to_video"]
    assert eff_t2v["fallback"] is True
    assert eff_t2v["fallback_from"] == "video"
    assert eff_t2v["model_key"] == "doubao-seedance-1-0-lite-t2v-250428"
    assert eff_i2v["fallback"] is False
    assert eff_i2v["status"] == "unset"
    assert "图生视频" in eff_i2v["fallback_blocked_reason"]

    # Text default resolves plan/write/revise to subscription grok-4, preserves explicit judge override,
    # and NEVER activates judge_secondary implicitly!
    snap = snapshot_from(scope_cfg, fake_settings)
    assert snap["by_purpose"]["write"]["transport"] == "cli_oauth"
    assert snap["by_purpose"]["write"]["cli_provider"] == "grok"
    assert snap["by_purpose"]["write"]["model_key"] == "grok-4"
    assert snap["by_purpose"]["plan"]["model_key"] == "grok-4"
    assert snap["by_purpose"]["revise"]["model_key"] == "grok-4"
    assert snap["by_purpose"]["judge"]["model_key"] == "deepseek-reasoner"
    assert "judge_secondary" not in snap["by_purpose"]
    assert _slot_configured(snap["by_purpose"]["write"]) is True

    # Switching same text default from Subscription -> API preserves judge_secondary unset & updates write cleanly
    caps_api_text = apply_capability_default(
        registry,
        caps,
        CapabilityDefaultInput(
            capability="text",
            source="api",
            configuration_id="api-judge",
            model_key="deepseek-reasoner",
        ),
    )
    api_text_snap = snapshot_from({"model_registry": registry, "capability_defaults": caps_api_text}, fake_settings)
    assert api_text_snap["by_purpose"]["write"]["model_key"] == "deepseek-reasoner"
    assert "judge_secondary" not in api_text_snap["by_purpose"]

    # Pinned job route stays unchanged when capability_defaults changes later
    pinned = ensure_job_route(snap)
    caps_changed = apply_capability_default(
        registry,
        caps,
        CapabilityDefaultInput(capability="text", source="subscription", provider="codex", model_key="gpt-5"),
    )
    new_snap = snapshot_from({"model_registry": registry, "capability_defaults": caps_changed}, fake_settings)
    assert new_snap["by_purpose"]["write"]["model_key"] == "gpt-5"
    assert pinned["by_purpose"]["write"]["model_key"] == "grok-4"

    # Subscription-only text default with empty model_registry still resolves write route
    sub_only_snap = snapshot_from({"capability_defaults": {"text": caps["text"]}}, fake_settings)
    assert sub_only_snap["by_purpose"]["write"]["cli_provider"] == "grok"
    assert sub_only_snap["by_purpose"]["write"]["model_key"] == "grok-4"

    # Disabling, changing model_key, or deleting an API config clears its capability_defaults cleanly
    disabled_reg = apply_enabled(registry, "api-t2v", False)
    assert clean_capability_defaults({"capability_defaults": caps}, disabled_reg)["video"] is None
    edited_reg = apply_configuration(
        registry,
        {**api_t2v, "model_key": "doubao-seedance-1-0-pro-250528"},
        "api-t2v",
        "",
    )
    assert clean_capability_defaults({"capability_defaults": caps}, edited_reg)["video"] is None
    deleted_reg = apply_delete(registry, "api-t2v")
    assert clean_capability_defaults({"capability_defaults": caps}, deleted_reg)["video"] is None
    assert clean_capability_defaults({"capability_defaults": caps}, deleted_reg)["text"]["model_key"] == "grok-4"


@pytest.mark.asyncio
async def test_write_paths_precollect_subscriptions_before_row_lock(monkeypatch):
    """Ensure save_configuration / bind_capability_default / save_subscription_model never run CLI probes under FOR UPDATE."""
    from ncc_data.application.model_settings import bind_capability_default, save_configuration

    events: list[str] = []
    scope = SimpleNamespace(id="system", version=1, config={})

    class OrderedDB:
        async def get(self, model, key):
            events.append("db.get")
            return scope

        async def scalar(self, stmt):
            events.append("db.for_update")
            return scope

        def add(self, obj):
            return None

        async def flush(self):
            events.append("db.flush")

    fake_svc = SimpleNamespace(actor=SimpleNamespace(id="admin-1", admin=True), db=OrderedDB())
    fake_settings = SimpleNamespace(
        model_url="",
        model_key="",
        writer_model="",
        judge_model="",
        second_judge_model="",
        cli_home=Path("/nowhere"),
        cli_which=lambda name: None,
        cli_run=lambda *a, **kw: Completed(1),
    )

    def tracked_collect(*args, **kwargs):
        events.append("cli.collect")
        return collect_subscriptions({}, home=Path("/nowhere"), which=lambda n: None, run=lambda *a, **k: Completed(1))

    monkeypatch.setattr("ncc_data.application.model_settings.collect_subscriptions", tracked_collect)
    monkeypatch.setattr("ncc_data.application.subscription_settings.collect_subscriptions", tracked_collect)

    events.clear()
    await save_configuration(
        fake_svc,
        fake_settings,
        ModelConfigurationInput(
            name="锁顺序验证",
            base_url="https://api.deepseek.com",
            auth_ref="DEEPSEEK_API_KEY",
            model_key="deepseek-chat",
            capabilities=["text"],
            purposes=["write"],
            enabled=True,
        ),
    )
    assert events.index("cli.collect") < events.index("db.for_update")
    assert events.count("cli.collect") == 1

    events.clear()
    await bind_capability_default(
        fake_svc,
        fake_settings,
        CapabilityDefaultInput(capability="text", source="subscription", provider="grok", model_key="grok-4"),
    )
    assert events.index("cli.collect") < events.index("db.for_update")
    assert events.count("cli.collect") == 1

    events.clear()
    await save_subscription_model(fake_svc, "grok", text_model="grok-3")
    assert events.index("cli.collect") < events.index("db.for_update")
    assert events.count("cli.collect") == 1
