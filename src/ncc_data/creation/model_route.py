"""Several chat configurations, one binding per purpose. Credential values never enter results."""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from ncc_data.domain.contracts import ModelConfigurationInput
from ncc_shared.errors import require

ENV_REF = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
CLI_MODEL_ID = re.compile(r"^[A-Za-z0-9_.:/-]{1,128}$")
CLI_PROVIDERS = ("grok", "codex", "agy")
SECRET_HINT = re.compile(r"(bearer\s+|api[_-]?key\s*=|sk-[A-Za-z0-9]{8,})", re.I)
PURPOSES = ("plan", "write", "revise", "judge", "judge_secondary")
PURPOSE_LABELS = (
    ("plan", "场景计划"),
    ("write", "正文与设定"),
    ("revise", "修订"),
    ("judge", "独立评价"),
    ("judge_secondary", "第二评价"),
)
ROUTE_KEYS = (
    "enabled",
    "supplier",
    "base_url",
    "auth_ref",
    "writer_model",
    "judge_model",
    "second_judge_model",
)
MAX_CONFIGS = 40


@dataclass(frozen=True)
class ResolvedRoute:
    base_url: str
    api_key: str
    model: str
    transport: str = "http"
    cli_provider: str = ""


def _clean(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def empty_registry() -> dict:
    return {"configurations": [], "defaults": {purpose: "" for purpose in PURPOSES}}


def stored_route(raw) -> dict | None:
    if not isinstance(raw, dict):
        return None
    return {key: raw.get(key) for key in ROUTE_KEYS}


def normalize_configuration(value: ModelConfigurationInput) -> dict:
    name = _clean(value.name)
    supplier = _clean(value.supplier) or "兼容接口"
    transport = _clean(getattr(value, "transport", "http")) or "http"
    cli_provider = _clean(getattr(value, "cli_provider", ""))
    base = _clean(value.base_url).rstrip("/")
    auth = _clean(value.auth_ref) or "NCC_MODEL_KEY"
    model = _clean(value.model_key)
    require(1 <= len(name) <= 80, "name", "配置名称需要 1 到 80 个字")
    require(transport in {"http", "cli_oauth"}, "transport", "未知的模型传输方式")
    for field, text in (("name", name), ("supplier", supplier), ("base_url", base), ("model_key", model)):
        require(SECRET_HINT.search(text) is None, field, "不要填写密钥，只填写地址、模型标识或环境变量名")
    purposes = []
    for item in value.purposes:
        require(item in PURPOSES, "purposes", "用途只能是计划、正文、修订、评价或第二评价")
        if item not in purposes:
            purposes.append(item)
    require(purposes, "purposes", "至少选择一个用途")
    if transport == "cli_oauth":
        require(cli_provider in CLI_PROVIDERS, "cli_provider", "CLI 订阅通道只能是 grok、codex 或 agy")
        if model:
            require(
                CLI_MODEL_ID.fullmatch(model) is not None
                and "token" not in model.lower()
                and "secret" not in model.lower(),
                "model_key",
                "不要填写密钥，只填写公开的模型标识",
            )
        if value.enabled:
            require(bool(model), "model_registry", "启用 CLI 订阅路由时需要模型标识")
        effective_supplier = supplier if supplier != "兼容接口" else f"{cli_provider.upper()} 订阅"
        return {
            "name": name,
            "supplier": effective_supplier,
            "transport": "cli_oauth",
            "cli_provider": cli_provider,
            "base_url": "",
            "auth_ref": "NCC_MODEL_KEY",
            "model_key": model,
            "purposes": purposes,
            "enabled": bool(value.enabled),
        }
    require(ENV_REF.match(auth) is not None, "auth_ref", "凭证只填写环境变量名，例如 NCC_MODEL_KEY，不要填写密钥")
    if value.enabled:
        require(base and model, "model_registry", "启用时需要网关地址和模型标识")
    if base:
        _check_url(base)
    return {
        "name": name,
        "supplier": supplier,
        "transport": "http",
        "cli_provider": "",
        "base_url": base,
        "auth_ref": auth,
        "model_key": model,
        "purposes": purposes,
        "enabled": bool(value.enabled),
    }


def _check_url(base: str):
    parts = urlsplit(base)
    require(parts.scheme in {"http", "https"} and parts.hostname, "base_url", "网关地址需要 http 或 https")
    require(not parts.username and not parts.password, "base_url", "不要把密钥写进地址")
    require(not parts.query and not parts.fragment, "base_url", "网关地址只保留到主机和路径")


def _clean_stored(row) -> dict | None:
    if not isinstance(row, dict):
        return None
    cid = _clean(row.get("id"))
    if not cid or len(cid) > 80 or not re.fullmatch(r"[A-Za-z0-9-]+", cid):
        return None
    name = (_clean(row.get("name")) or cid)[:80]
    supplier = (_clean(row.get("supplier")) or "兼容接口")[:64]
    transport = "cli_oauth" if _clean(row.get("transport")) == "cli_oauth" else "http"
    cli_provider = _clean(row.get("cli_provider")) if transport == "cli_oauth" else ""
    if transport == "cli_oauth" and cli_provider not in CLI_PROVIDERS:
        return None
    base = "" if transport == "cli_oauth" else _clean(row.get("base_url")).rstrip("/")[:512]
    auth = _clean(row.get("auth_ref")) or "NCC_MODEL_KEY"
    if ENV_REF.match(auth) is None:
        auth = "NCC_MODEL_KEY"
    model = _clean(row.get("model_key"))[:128]
    purposes = []
    raw = row.get("purposes")
    if isinstance(raw, list):
        for item in raw:
            if item in PURPOSES and item not in purposes:
                purposes.append(item)
    if not purposes:
        return None
    enabled = bool(row.get("enabled"))
    if transport == "cli_oauth":
        if enabled and not (cli_provider and model):
            enabled = False
    elif enabled and not (base and model):
        enabled = False
    return {
        "id": cid,
        "name": name,
        "supplier": supplier,
        "transport": transport,
        "cli_provider": cli_provider,
        "base_url": base,
        "auth_ref": auth,
        "model_key": model,
        "purposes": purposes,
        "enabled": enabled,
    }


def clean_registry(raw) -> dict:
    configurations = []
    seen = set()
    for row in raw.get("configurations") or []:
        item = _clean_stored(row)
        if item is None or item["id"] in seen:
            continue
        seen.add(item["id"])
        configurations.append(item)
        if len(configurations) >= MAX_CONFIGS:
            break
    return {"configurations": configurations, "defaults": _valid_defaults(configurations, raw.get("defaults"))}


def _valid_defaults(configurations, raw) -> dict:
    by_id = {row["id"]: row for row in configurations}
    incoming = raw if isinstance(raw, dict) else {}
    defaults = {}
    for purpose in PURPOSES:
        chosen = _clean(incoming.get(purpose))
        row = by_id.get(chosen)
        defaults[purpose] = chosen if row and row["enabled"] and purpose in row["purposes"] else ""
    return defaults


def _clear_invalid_defaults(registry) -> None:
    registry["defaults"] = _valid_defaults(registry["configurations"], registry.get("defaults"))


def _copy_registry(registry) -> dict:
    configurations = [{**row, "purposes": list(row.get("purposes") or [])} for row in registry.get("configurations") or []]
    defaults = {purpose: "" for purpose in PURPOSES}
    raw = registry.get("defaults") or {}
    for purpose in PURPOSES:
        value = raw.get(purpose, "")
        defaults[purpose] = value if isinstance(value, str) else ""
    return {"configurations": configurations, "defaults": defaults}


def synthesize_legacy(saved) -> dict:
    """An enabled single route becomes stable rows until the first explicit registry save."""
    base = _clean(saved.get("base_url")).rstrip("/")
    auth = _clean(saved.get("auth_ref")) or "NCC_MODEL_KEY"
    supplier = _clean(saved.get("supplier")) or "兼容接口"
    writer = _clean(saved.get("writer_model"))
    judge = _clean(saved.get("judge_model"))
    second = _clean(saved.get("second_judge_model"))
    enabled = bool(saved.get("enabled")) and bool(base) and bool(writer)
    writer_purposes = ["plan", "write", "revise"]
    configs = []
    if not judge or judge == writer:
        writer_purposes.append("judge")
    configs.append(
        {
            "id": "legacy-writer",
            "name": "原写作模型",
            "supplier": supplier,
            "base_url": base,
            "auth_ref": auth,
            "model_key": writer,
            "purposes": writer_purposes,
            "enabled": enabled,
        }
    )
    if judge and judge != writer:
        configs.append(
            {
                "id": "legacy-judge",
                "name": "原评价模型",
                "supplier": supplier,
                "base_url": base,
                "auth_ref": auth,
                "model_key": judge,
                "purposes": ["judge"],
                "enabled": enabled,
            }
        )
    if second:
        configs.append(
            {
                "id": "legacy-second",
                "name": "原第二评价",
                "supplier": supplier,
                "base_url": base,
                "auth_ref": auth,
                "model_key": second,
                "purposes": ["judge_secondary"],
                "enabled": enabled,
            }
        )
    defaults = {purpose: "" for purpose in PURPOSES}
    if enabled:
        for row in configs:
            for purpose in row["purposes"]:
                defaults[purpose] = row["id"]
    return {"configurations": configs, "defaults": defaults}


def active_registry(scope_config) -> tuple[dict, str]:
    """Persisted registry wins. An enabled legacy route is only an in-memory view."""
    config = scope_config or {}
    raw = config.get("model_registry")
    if isinstance(raw, dict) and isinstance(raw.get("configurations"), list):
        return clean_registry(raw), "registry"
    legacy = stored_route(config.get("model_route"))
    if legacy and legacy.get("enabled"):
        return synthesize_legacy(legacy), "saved"
    return empty_registry(), "environment"


def writable_registry(scope_config) -> dict:
    registry, source = active_registry(scope_config)
    if source == "environment":
        return empty_registry()
    return registry


def _find(registry, cid):
    return next((row for row in registry["configurations"] if row["id"] == cid), None)


def apply_configuration(registry, fields, existing_id, new_id) -> dict:
    reg = _copy_registry(registry)
    stored = {**fields, "purposes": list(fields["purposes"])}
    if existing_id:
        row = _find(reg, existing_id)
        require(row is not None, "not_found", "模型配置不存在", 404)
        row.clear()
        row.update({"id": existing_id, **stored})
    else:
        require(len(reg["configurations"]) < MAX_CONFIGS, "model_registry", "模型配置最多保存 40 项")
        reg["configurations"].append({"id": new_id, **stored})
    _clear_invalid_defaults(reg)
    return reg


def apply_enabled(registry, cid, enabled) -> dict:
    reg = _copy_registry(registry)
    row = _find(reg, cid)
    require(row is not None, "not_found", "模型配置不存在", 404)
    if enabled:
        if row.get("transport") == "cli_oauth":
            require(
                row.get("cli_provider") in CLI_PROVIDERS and row.get("model_key"),
                "model_registry",
                "启用 CLI 订阅路由时需要订阅通道和模型标识",
            )
        else:
            require(row.get("base_url") and row.get("model_key"), "model_registry", "启用时需要网关地址和模型标识")
    row["enabled"] = bool(enabled)
    _clear_invalid_defaults(reg)
    return reg


def apply_default(registry, purpose, configuration_id) -> dict:
    require(purpose in PURPOSES, "purpose", "未知用途")
    reg = _copy_registry(registry)
    chosen = _clean(configuration_id)
    if not chosen:
        reg["defaults"][purpose] = ""
        return reg
    row = _find(reg, chosen)
    require(row is not None, "not_found", "模型配置不存在", 404)
    require(row.get("enabled"), "model_registry", "只能把默认用途绑到已启用的配置")
    require(purpose in row.get("purposes", []), "model_registry", "这个配置不包含所选用途")
    reg["defaults"][purpose] = chosen
    return reg


def apply_delete(registry, cid) -> dict:
    reg = _copy_registry(registry)
    kept = [row for row in reg["configurations"] if row["id"] != cid]
    require(len(kept) < len(reg["configurations"]), "not_found", "模型配置不存在", 404)
    reg["configurations"] = kept
    _clear_invalid_defaults(reg)
    return reg


def _slot(row) -> dict:
    slot = {
        "configuration_id": row["id"],
        "name": row.get("name") or "",
        "base_url": _clean(row.get("base_url")).rstrip("/"),
        "auth_ref": _clean(row.get("auth_ref")) or "NCC_MODEL_KEY",
        "model_key": _clean(row.get("model_key")),
    }
    if row.get("transport") == "cli_oauth":
        slot["transport"] = "cli_oauth"
        slot["cli_provider"] = _clean(row.get("cli_provider"))
    return slot


def _env_model(purpose, settings) -> str:
    writer = _clean(getattr(settings, "writer_model", ""))
    judge = _clean(getattr(settings, "judge_model", "")) or writer
    second = _clean(getattr(settings, "second_judge_model", ""))
    if purpose == "judge":
        return judge
    if purpose == "judge_secondary":
        return second
    return writer


def _env_slot(purpose, settings):
    model = _env_model(purpose, settings)
    if purpose == "judge_secondary" and not model:
        return None
    return {
        "configuration_id": "",
        "name": "进程环境",
        "base_url": _clean(getattr(settings, "model_url", "")).rstrip("/"),
        "auth_ref": "NCC_MODEL_KEY",
        "model_key": model,
    }


def _resolve(registry, purpose, settings):
    chosen = (registry.get("defaults") or {}).get(purpose) or ""
    row = _find(registry, chosen)
    if row and row.get("enabled") and purpose in row.get("purposes", []):
        return _slot(row)
    for item in registry.get("configurations") or []:
        if item.get("enabled") and purpose in (item.get("purposes") or []):
            return _slot(item)
    if settings is None:
        return None
    return _env_slot(purpose, settings)


def _snapshot(registry, settings, source, fallback: bool) -> dict:
    by = {}
    for purpose in PURPOSES:
        slot = _resolve(registry, purpose, settings if fallback else None)
        if not slot or not slot.get("model_key"):
            continue
        by[purpose] = slot
    second = (by.get("judge_secondary") or {}).get("model_key") or ""
    return {"source": source, "by_purpose": by, "second_judge_model": second}


def environment_snapshot(settings) -> dict:
    return _snapshot(empty_registry(), settings, "environment", True)


def snapshot_from(scope_config, settings) -> dict:
    registry, source = active_registry(scope_config)
    if source == "environment":
        return environment_snapshot(settings)
    # A saved single route already names every purpose, including an empty second judge.
    return _snapshot(registry, settings, source, fallback=source == "registry")


def _legacy_job_snapshot(route) -> dict:
    base = _clean(route.get("base_url")).rstrip("/")
    auth = _clean(route.get("auth_ref")) or "NCC_MODEL_KEY"
    supplier = _clean(route.get("supplier")) or "已固定的模型"
    writer = _clean(route.get("writer_model"))
    judge = _clean(route.get("judge_model")) or writer
    second = _clean(route.get("second_judge_model"))

    def slot(cid, model):
        return {
            "configuration_id": cid,
            "name": supplier,
            "base_url": base,
            "auth_ref": auth,
            "model_key": model,
        }

    by = {purpose: slot("legacy-writer", writer) for purpose in ("plan", "write", "revise")}
    by["judge"] = slot("legacy-judge" if judge and judge != writer else "legacy-writer", judge)
    if second:
        by["judge_secondary"] = slot("legacy-second", second)
    source = route.get("source") if route.get("source") in {"registry", "environment", "saved"} else "saved"
    return {"source": source, "by_purpose": by, "second_judge_model": second}


def ensure_job_route(stored) -> dict:
    """Keep a job on the route it started with. Older pins gain by_purpose without reading new settings."""
    if not isinstance(stored, dict):
        return {"source": "saved", "by_purpose": {}, "second_judge_model": ""}
    if isinstance(stored.get("by_purpose"), dict):
        by = {}
        for purpose, slot in stored["by_purpose"].items():
            if purpose not in PURPOSES or not isinstance(slot, dict):
                continue
            model = _clean(slot.get("model_key"))
            if purpose == "judge_secondary" and not model:
                continue
            entry = {
                "configuration_id": _clean(slot.get("configuration_id")),
                "name": _clean(slot.get("name")),
                "base_url": _clean(slot.get("base_url")).rstrip("/"),
                "auth_ref": _clean(slot.get("auth_ref")) or "NCC_MODEL_KEY",
                "model_key": model,
            }
            if slot.get("transport") == "cli_oauth":
                entry["transport"] = "cli_oauth"
                entry["cli_provider"] = _clean(slot.get("cli_provider"))
            by[purpose] = entry
        source = stored.get("source") if stored.get("source") in {"registry", "environment", "saved"} else "saved"
        second = (by.get("judge_secondary") or {}).get("model_key") or ""
        return {"source": source, "by_purpose": by, "second_judge_model": second}
    return _legacy_job_snapshot(stored)


def purpose_slot(snapshot, purpose) -> dict:
    by = snapshot.get("by_purpose") if isinstance(snapshot, dict) else None
    slot = by.get(purpose) if isinstance(by, dict) else None
    return slot if isinstance(slot, dict) else {}


def resolve_credential(auth_ref: str, settings) -> str:
    """Resolve API credential honoring file-first Settings precedence before process environment."""
    ref = _clean(auth_ref) or "NCC_MODEL_KEY"
    if ref == "NCC_MODEL_KEY":
        configured = _clean(getattr(settings, "model_key", "")) if settings is not None else ""
        if configured:
            return configured
    if settings is not None:
        creds = getattr(settings, "credentials", None)
        if isinstance(creds, dict):
            mapped = _clean(creds.get(ref, ""))
            if mapped:
                return mapped
    return _clean(os.environ.get(ref, ""))


def key_present(row, settings) -> bool:
    ref = _clean(row.get("auth_ref")) or "NCC_MODEL_KEY"
    return bool(resolve_credential(ref, settings))


def _cli_oauth_connection(row, settings) -> dict:
    from ncc_data.creation.subscription_auth import agy_status, codex_status, grok_status

    provider = _clean(row.get("cli_provider"))
    model = _clean(row.get("model_key"))
    if provider not in CLI_PROVIDERS or not model:
        return {
            "status": "not_configured",
            "credential": "absent",
            "message": "未选择 CLI 订阅通道或模型标识。不会生成演示内容。",
        }
    home = getattr(settings, "cli_home", None) or Path.home()
    which = getattr(settings, "cli_which", None) or shutil.which
    run = getattr(settings, "cli_run", None) or subprocess.run
    if provider == "grok":
        sub = grok_status(Path(home), which)
    elif provider == "codex":
        sub = codex_status(which, run)
    else:
        sub = agy_status(Path(home), which)
    if not sub.get("cli_installed"):
        return {
            "status": "not_configured",
            "credential": "absent",
            "message": sub.get("message") or f"未检测到本机 {provider} CLI。",
        }
    if sub.get("ready") or (provider == "agy" and sub.get("status") == "file_detected"):
        return {
            "status": "loaded",
            "credential": "present",
            "message": sub.get("message") or f"本机 {provider} CLI 订阅通道已就绪。",
        }
    return {
        "status": "not_configured",
        "credential": "absent",
        "message": sub.get("message") or f"本机 {provider} CLI 尚未完成订阅授权。",
    }


def connection(row, settings) -> dict:
    if row.get("transport") == "cli_oauth":
        return _cli_oauth_connection(row, settings)
    if not row.get("base_url") or not row.get("model_key"):
        return {
            "status": "not_configured",
            "credential": "absent",
            "message": "未配置网关地址或模型标识。不会生成演示内容，也未向模型发起请求。",
        }
    present = key_present(row, settings)
    if present:
        message = "凭证已按当前配置解析载入。未向模型发起请求，也不证明生成质量。"
    else:
        message = "地址和模型已配置。凭证尚未配置；本机无密钥网关仍可使用。未向模型发起请求。"
    return {
        "status": "loaded",
        "credential": "present" if present else "absent",
        "message": message,
    }


def materialize_one(slot, settings) -> ResolvedRoute:
    if slot.get("transport") == "cli_oauth":
        return ResolvedRoute(
            base_url="",
            api_key="",
            model=_clean(slot.get("model_key")),
            transport="cli_oauth",
            cli_provider=_clean(slot.get("cli_provider")),
        )
    ref = _clean(slot.get("auth_ref")) or "NCC_MODEL_KEY"
    key = resolve_credential(ref, settings)
    return ResolvedRoute(
        base_url=_clean(slot.get("base_url")).rstrip("/"),
        api_key=key,
        model=_clean(slot.get("model_key")),
    )


def _public(row, settings) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "supplier": row["supplier"],
        "transport": row.get("transport", "http"),
        "cli_provider": row.get("cli_provider", ""),
        "base_url": row["base_url"],
        "auth_ref": row["auth_ref"],
        "model_key": row["model_key"],
        "purposes": list(row["purposes"]),
        "enabled": bool(row["enabled"]),
        "connection": connection(row, settings),
    }


def presets(settings) -> list[dict]:
    fixed = [
        ("openai", "OpenAI 兼容", "OpenAI", "https://api.openai.com/v1", "OPENAI_API_KEY"),
        ("xai", "xAI", "xAI", "https://api.x.ai/v1", "XAI_API_KEY"),
        ("ark", "火山方舟", "火山方舟", "https://ark.cn-beijing.volces.com/api/v3", "ARK_API_KEY"),
        ("deepseek", "DeepSeek", "DeepSeek", "https://api.deepseek.com", "DEEPSEEK_API_KEY"),
    ]
    cli_presets = [
        ("cli-grok", "Grok CLI 订阅", "xAI Grok 订阅", "grok", "grok-4"),
        ("cli-codex", "Codex CLI 订阅", "ChatGPT Codex 订阅", "codex", "gpt-5"),
        ("cli-agy", "AGY CLI 订阅", "Google AGY 订阅", "agy", "gemini-2.5-pro"),
    ]
    purposes = ["plan", "write", "revise", "judge"]
    rows = [
        {
            "id": "environment",
            "name": "当前进程环境",
            "supplier": "环境变量",
            "transport": "http",
            "cli_provider": "",
            "base_url": _clean(getattr(settings, "model_url", "")).rstrip("/"),
            "auth_ref": "NCC_MODEL_KEY",
            "model_key": _clean(getattr(settings, "writer_model", "")),
            "purposes": purposes + (["judge_secondary"] if _clean(getattr(settings, "second_judge_model", "")) else []),
        }
    ]
    for pid, name, supplier, base, auth in fixed:
        rows.append(
            {
                "id": pid,
                "name": name,
                "supplier": supplier,
                "transport": "http",
                "cli_provider": "",
                "base_url": base,
                "auth_ref": auth,
                "model_key": "",
                "purposes": list(purposes),
            }
        )
    for pid, name, supplier, provider, default_model in cli_presets:
        rows.append(
            {
                "id": pid,
                "name": name,
                "supplier": supplier,
                "transport": "cli_oauth",
                "cli_provider": provider,
                "base_url": "",
                "auth_ref": "NCC_MODEL_KEY",
                "model_key": default_model,
                "purposes": list(purposes),
            }
        )
    return rows


def describe(scope_config, settings) -> dict:
    registry, source = active_registry(scope_config)
    snap = snapshot_from(scope_config, settings)
    effective = {}
    for purpose, label in PURPOSE_LABELS:
        slot = snap["by_purpose"].get(purpose) or {}
        effective[purpose] = {
            "label": label,
            "configuration_id": slot.get("configuration_id", ""),
            "name": slot.get("name", ""),
            "model_key": slot.get("model_key", ""),
            "bound": bool(registry["defaults"].get(purpose)),
        }
    return {
        "configurations": [_public(row, settings) for row in registry["configurations"]],
        "defaults": dict(registry["defaults"]),
        "purposes": [{"id": purpose, "label": label} for purpose, label in PURPOSE_LABELS],
        "presets": presets(settings),
        "source": source,
        "effective": effective,
    }
