from types import SimpleNamespace

import pytest

from ncc_data.creation.model_route import (
    apply_default,
    apply_delete,
    apply_enabled,
    describe,
    ensure_job_route,
    materialize_one,
    normalize_configuration,
    snapshot_from,
)
from ncc_data.domain.contracts import ModelConfigurationInput
from ncc_shared.errors import DomainError


def settings(**extra):
    return SimpleNamespace(
        model_url=extra.get("model_url", ""),
        model_key=extra.get("model_key", ""),
        writer_model=extra.get("writer_model", ""),
        judge_model=extra.get("judge_model", ""),
        second_judge_model=extra.get("second_judge_model", ""),
    )


def row(cid, model, purposes, **extra):
    return {
        "id": cid,
        "name": extra.get("name", cid),
        "supplier": extra.get("supplier", "兼容接口"),
        "base_url": extra.get("base_url", "https://gateway.example/v1"),
        "auth_ref": extra.get("auth_ref", "NCC_MODEL_KEY"),
        "model_key": model,
        "purposes": purposes,
        "enabled": extra.get("enabled", True),
    }


def test_environment_is_used_until_a_configuration_is_enabled():
    env = settings(model_url="https://env.example/v1", writer_model="env-writer", judge_model="env-judge")
    assert snapshot_from(None, env)["source"] == "environment"
    disabled = snapshot_from({"model_route": {"enabled": False, "writer_model": "other"}}, env)
    assert disabled["by_purpose"]["write"]["model_key"] == "env-writer"
    registry = {
        "configurations": [row("off", "off-model", ["plan", "write", "revise", "judge"], enabled=False)],
        "defaults": {},
    }
    mixed = snapshot_from({"model_registry": registry}, env)
    assert mixed["source"] == "registry"
    assert mixed["by_purpose"]["write"]["model_key"] == "env-writer"
    assert mixed["by_purpose"]["write"]["configuration_id"] == ""
    assert "off-model" not in str(mixed)


def test_two_enabled_configurations_bind_different_purposes():
    env = settings(
        model_url="https://env.example/v1",
        writer_model="env-writer",
        judge_model="env-judge",
        second_judge_model="env-second",
    )
    registry = {
        "configurations": [
            row("w", "writer-a", ["plan", "write", "revise"], base_url="https://write.example/v1", name="写作"),
            row(
                "j",
                "judge-b",
                ["judge"],
                base_url="https://judge.example/v1",
                auth_ref="JUDGE_KEY",
                name="评价",
            ),
        ],
        "defaults": {"plan": "w", "write": "w", "revise": "w", "judge": "j", "judge_secondary": ""},
    }
    snap = snapshot_from({"model_registry": registry, "model_route": {"enabled": True, "writer_model": "legacy"}}, env)
    assert snap["source"] == "registry"
    assert snap["by_purpose"]["write"]["model_key"] == "writer-a"
    assert snap["by_purpose"]["write"]["base_url"] == "https://write.example/v1"
    assert snap["by_purpose"]["judge"]["model_key"] == "judge-b"
    assert snap["by_purpose"]["judge"]["base_url"] == "https://judge.example/v1"
    assert snap["by_purpose"]["judge_secondary"]["model_key"] == "env-second"
    assert snap["by_purpose"]["judge_secondary"]["configuration_id"] == ""
    write_only = snapshot_from(
        {"model_registry": {"configurations": [registry["configurations"][0]], "defaults": {"write": "w"}}},
        env,
    )
    assert write_only["by_purpose"]["judge"]["model_key"] == "env-judge"
    assert write_only["by_purpose"]["judge"]["configuration_id"] == ""


def test_enabled_legacy_route_projects_without_pulling_an_empty_second_judge_from_the_environment():
    env = settings(writer_model="env-writer", second_judge_model="env-second", model_url="https://env.example/v1")
    saved = {
        "enabled": True,
        "supplier": "兼容接口",
        "base_url": "https://saved.example/v1/",
        "auth_ref": "NCC_MODEL_KEY",
        "writer_model": "saved-writer",
        "judge_model": "saved-judge",
        "second_judge_model": "",
    }
    snap = snapshot_from({"model_route": saved}, env)
    assert snap["source"] == "saved"
    assert snap["by_purpose"]["write"] == {
        "configuration_id": "legacy-writer",
        "name": "原写作模型",
        "base_url": "https://saved.example/v1",
        "auth_ref": "NCC_MODEL_KEY",
        "model_key": "saved-writer",
    }
    assert snap["by_purpose"]["judge"]["model_key"] == "saved-judge"
    assert snap["by_purpose"]["judge"]["configuration_id"] == "legacy-judge"
    assert "judge_secondary" not in snap["by_purpose"]
    assert snap["second_judge_model"] == ""


def test_normalize_rejects_secret_material_and_strips_the_url():
    value = ModelConfigurationInput(
        name="写作",
        enabled=True,
        base_url="https://gateway.example/v1/",
        auth_ref="NCC_MODEL_KEY",
        model_key="writer-a",
        purposes=["write", "plan", "write"],
    )
    stored = normalize_configuration(value)
    assert stored["base_url"] == "https://gateway.example/v1"
    assert stored["purposes"] == ["write", "plan"]
    assert "api_key" not in stored
    with pytest.raises(DomainError):
        normalize_configuration(value.model_copy(update={"auth_ref": "sk-live-secret-value"}))
    with pytest.raises(DomainError):
        normalize_configuration(value.model_copy(update={"base_url": "https://user:password@gateway.example/v1"}))


def test_describe_and_materialize_honor_config_precedence_and_hide_credentials(monkeypatch):
    monkeypatch.setenv("NCC_MODEL_KEY", "process-placeholder-key")
    monkeypatch.setenv("JUDGE_KEY", "judge-placeholder-key")
    monkeypatch.setenv("NCC_CUSTOM_KEY", "process-custom-placeholder")
    stored = normalize_configuration(
        ModelConfigurationInput(
            name="写作",
            enabled=True,
            base_url="https://gateway.example/v1",
            model_key="writer-a",
            purposes=["write"],
        )
    )
    cfg_settings = SimpleNamespace(
        model_url="https://env.example/v1",
        model_key="config-file-placeholder-key",
        writer_model="env-writer",
        judge_model="",
        second_judge_model="",
        credentials={"NCC_CUSTOM_KEY": "config-custom-placeholder"},
    )
    view = describe(
        {"model_registry": {"configurations": [{**stored, "id": "w"}], "defaults": {}}},
        cfg_settings,
    )
    assert view["configurations"][0]["connection"]["credential"] == "present"
    assert view["presets"][0]["id"] == "environment"
    assert view["presets"][0]["model_key"] == "env-writer"
    rendered = str(view)
    assert "process-placeholder-key" not in rendered
    assert "judge-placeholder-key" not in rendered
    assert "config-file-placeholder-key" not in rendered
    assert "config-custom-placeholder" not in rendered
    # Resolved config file value wins over process NCC_MODEL_KEY
    route = materialize_one(view["configurations"][0], cfg_settings)
    assert route.api_key == "config-file-placeholder-key"
    assert route.model == "writer-a"
    # Falls back to process NCC_MODEL_KEY when config has none
    fallback_route = materialize_one(view["configurations"][0], settings(model_key=""))
    assert fallback_route.api_key == "process-placeholder-key"
    # Custom NCC_* ref uses resolved config credentials before process env
    custom_ncc = materialize_one(
        {"base_url": "https://judge.example/v1", "auth_ref": "NCC_CUSTOM_KEY", "model_key": "judge-c"},
        cfg_settings,
    )
    assert custom_ncc.api_key == "config-custom-placeholder"
    # External env ref resolves from process env and agrees with connection()
    other_slot = {"base_url": "https://judge.example/v1", "auth_ref": "JUDGE_KEY", "model_key": "judge-b"}
    other = materialize_one(other_slot, cfg_settings)
    assert other.api_key == "judge-placeholder-key"
    assert other.model == "judge-b"
    missing_slot = {"base_url": "https://judge.example/v1", "auth_ref": "MISSING_SYNTHETIC_KEY", "model_key": "judge-m"}
    assert materialize_one(missing_slot, cfg_settings).api_key == ""
    missing_view = describe(
        {"model_registry": {"configurations": [{**stored, "id": "m", "auth_ref": "MISSING_SYNTHETIC_KEY"}], "defaults": {}}},
        cfg_settings,
    )
    assert missing_view["configurations"][0]["connection"]["credential"] == "absent"


def test_disable_or_delete_clears_the_default_binding():
    registry = {
        "configurations": [
            row("w", "writer-a", ["write"]),
            row("j", "judge-b", ["judge"]),
        ],
        "defaults": {"write": "w", "judge": "j"},
    }
    disabled = apply_enabled(registry, "j", False)
    assert disabled["defaults"]["judge"] == ""
    with pytest.raises(DomainError):
        apply_default(disabled, "judge", "j")
    removed = apply_delete(registry, "w")
    assert removed["defaults"]["write"] == ""
    assert [item["id"] for item in removed["configurations"]] == ["j"]


def test_an_in_flight_job_keeps_its_original_models():
    old = {
        "source": "environment",
        "supplier": "环境变量",
        "base_url": "https://env.example/v1",
        "auth_ref": "NCC_MODEL_KEY",
        "writer_model": "w",
        "judge_model": "j",
        "second_judge_model": "s",
    }
    pinned = ensure_job_route(old)
    assert pinned["by_purpose"]["plan"]["model_key"] == "w"
    assert pinned["by_purpose"]["judge"]["model_key"] == "j"
    assert pinned["by_purpose"]["judge_secondary"]["model_key"] == "s"
    assert pinned["second_judge_model"] == "s"
    assert ensure_job_route(pinned) == pinned
    assert materialize_one(pinned["by_purpose"]["judge"], settings(model_key="")).model == "j"
