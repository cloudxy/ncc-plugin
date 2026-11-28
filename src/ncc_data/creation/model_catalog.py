"""Shared model capability catalog, validation constants, and unified 6-capability default logic.

Pure leaf module under creation/ with zero imports from model_route or subscription_auth,
preventing circular dependencies while providing a single source of truth for API platforms,
grounded subscription channel catalogs, and global 6-capability defaults.
"""

from __future__ import annotations

import re

from ncc_data.domain.contracts import CapabilityDefaultInput
from ncc_shared.errors import require

ENV_REF = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
CLI_MODEL_ID = re.compile(r"^[A-Za-z0-9_.:/-]{1,128}$")
CLI_PROVIDERS = ("grok", "codex", "agy")
SECRET_HINT = re.compile(r"(bearer\s+|api[_-]?key\s*=|sk-[A-Za-z0-9]{8,})", re.I)

CAPABILITIES = (
    "text",
    "text_to_image",
    "video",
    "image_to_image",
    "image_to_video",
    "text_to_video",
)

CAPABILITY_META = (
    {
        "id": "text",
        "label": "文本",
        "description": "小说正文、细纲、修订与审评通用文本模型（主能力）",
        "runtime_adapter": "implemented",
        "runtime_note": "已接入创作台与后台文本路由（支持 HTTP API 与本机 CLI OAuth 订阅）",
    },
    {
        "id": "text_to_image",
        "label": "生图",
        "description": "文字生成图片（小说封页、人物立绘与场景插图）",
        "runtime_adapter": "metadata_only",
        "runtime_note": "已完成模型登记、能力校验与全局默认持久化；媒体执行适配器待后续接入",
    },
    {
        "id": "video",
        "label": "生视频",
        "description": "通用视频默认槽位（仅在默认模型实际匹配对应输入模式时可回退）",
        "runtime_adapter": "metadata_only",
        "runtime_note": "已完成模型登记、能力校验与全局默认持久化；媒体执行适配器待后续接入",
    },
    {
        "id": "image_to_image",
        "label": "图生图",
        "description": "以参考图片进行人物变体、风格迁移或局部重绘",
        "runtime_adapter": "metadata_only",
        "runtime_note": "已完成模型登记、能力校验与全局默认持久化；媒体执行适配器待后续接入",
    },
    {
        "id": "image_to_video",
        "label": "图生视频",
        "description": "以静帧封面/人物图生成视频片段（独立于文生视频输入能力）",
        "runtime_adapter": "metadata_only",
        "runtime_note": "已完成模型登记、能力校验与全局默认持久化；媒体执行适配器待后续接入",
    },
    {
        "id": "text_to_video",
        "label": "文生视频",
        "description": "以文字分镜脚本直接生成视频片段（独立于图生视频输入能力）",
        "runtime_adapter": "metadata_only",
        "runtime_note": "已完成模型登记、能力校验与全局默认持久化；媒体执行适配器待后续接入",
    },
)

CAPABILITY_LABELS = {item["id"]: item["label"] for item in CAPABILITY_META}

DEPRECATED_API_MODELS: dict[str, str] = {
    "gpt-image-1": "OpenAI 官方图像 API 已停用 gpt-image-1；已保存历史标识仍可展示，建议改选 gpt-image-1.5 或 gpt-image-1-mini。",
}

# Grounded HTTP API platform catalog (official provider API endpoints & capabilities).
API_PLATFORMS = (
    {
        "id": "openai",
        "name": "OpenAI 兼容",
        "supplier": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "auth_ref": "OPENAI_API_KEY",
        "models": (
            ("gpt-5", "gpt-5（主力文本与创作）", "text", ("text",), "model"),
            ("gpt-5.4", "gpt-5.4（长篇连载与深度推演）", "text", ("text",), "model"),
            ("gpt-4.1", "gpt-4.1（稳健长上下文文本）", "text", ("text",), "model"),
            ("o3", "o3（逻辑推理与独立审评）", "text", ("text",), "model"),
            (
                "gpt-image-1.5",
                "gpt-image-1.5（图像 API · 生图与图生图）",
                "image",
                ("text_to_image", "image_to_image"),
                "model",
            ),
            (
                "gpt-image-1-mini",
                "gpt-image-1-mini（轻量图像 API · 生图与图生图）",
                "image",
                ("text_to_image", "image_to_image"),
                "model",
            ),
            ("sora-2", "sora-2（视频 API · 通用/文生/图生视频）", "video", ("video", "text_to_video", "image_to_video"), "model"),
        ),
    },
    {
        "id": "xai",
        "name": "xAI",
        "supplier": "xAI",
        "base_url": "https://api.x.ai/v1",
        "auth_ref": "XAI_API_KEY",
        "models": (
            ("grok-4", "grok-4（主力文本与推演）", "text", ("text",), "model"),
            ("grok-3", "grok-3（长文对话与审评）", "text", ("text",), "model"),
            (
                "grok-imagine-image",
                "grok-imagine-image（xAI 图像 API · 生图与图片编辑）",
                "image",
                ("text_to_image", "image_to_image"),
                "model",
            ),
            (
                "grok-imagine-image-2.0",
                "grok-imagine-image-2.0（xAI 图像 API · 精绘与图生图）",
                "image",
                ("text_to_image", "image_to_image"),
                "model",
            ),
            (
                "grok-imagine-video",
                "grok-imagine-video（xAI 视频 API · 文生/图生视频）",
                "video",
                ("video", "text_to_video", "image_to_video"),
                "model",
            ),
        ),
    },
    {
        "id": "ark",
        "name": "火山方舟",
        "supplier": "火山方舟",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "auth_ref": "ARK_API_KEY",
        "models": (
            ("doubao-1-5-pro-32k-250115", "Doubao 1.5 Pro（中文主力文本）", "text", ("text",), "model"),
            ("doubao-seedream-3-0-t2i-250415", "Seedream 3.0（仅文字生图）", "image", ("text_to_image",), "model"),
            ("doubao-seededit-3-0-i2i-250628", "SeedEdit 3.0（仅图生图）", "image", ("image_to_image",), "model"),
            (
                "doubao-seedance-1-0-pro-250528",
                "Seedance 1.0 Pro（通用/文生/图生视频）",
                "video",
                ("video", "text_to_video", "image_to_video"),
                "model",
            ),
            (
                "doubao-seedance-1-0-lite-t2v-250428",
                "Seedance 1.0 Lite T2V（仅文生视频）",
                "video",
                ("video", "text_to_video"),
                "model",
            ),
            (
                "doubao-seedance-1-0-lite-i2v-250428",
                "Seedance 1.0 Lite I2V（仅图生视频）",
                "video",
                ("video", "image_to_video"),
                "model",
            ),
        ),
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "supplier": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "auth_ref": "DEEPSEEK_API_KEY",
        "models": (
            ("deepseek-chat", "deepseek-chat（中文小说主力文本）", "text", ("text",), "model"),
            ("deepseek-reasoner", "deepseek-reasoner（深度推理与审评）", "text", ("text",), "model"),
        ),
    },
    {
        "id": "custom",
        "name": "自定义兼容接口",
        "supplier": "兼容接口",
        "base_url": "",
        "auth_ref": "NCC_MODEL_KEY",
        "models": (),
    },
)

# Grounded local CLI subscription channel catalog.
# Strictly distinguishes callable CLI chat models (entry_kind="model") from built-in CLI media tools/subagents
# (entry_kind="builtin_tool"), and excludes API-only models lacking CLI subscription channel evidence.
SUBSCRIPTION_CHANNELS = (
    {
        "id": "grok",
        "title": "xAI Grok 订阅授权",
        "path_label": "~/.grok/auth.json",
        "bin": "grok",
        "login_command": "grok login --oauth",
        "device_auth_argv": ("login", "--device-auth"),
        "login_argv": ("login", "--oauth"),
        "verify_argv": ("models",),
        "login_label": "网页发起 OAuth 授权",
        "verify_label": "在线验证授权",
        "note": "复用本机 grok CLI 登录态，不回传令牌也不改用 XAI_API_KEY。xAI 视频模型属 API 能力，需在「API 配置 → xAI」登记。",
        "text_models": (
            ("grok-4", "grok-4（主力文本与推演）", ("text",), "model"),
            ("grok-4-fast", "grok-4-fast（快速草稿与大纲）", ("text",), "model"),
            ("grok-3", "grok-3（长文对话与审评）", ("text",), "model"),
            ("grok-3-mini", "grok-3-mini（轻量规划与校对）", ("text",), "model"),
        ),
        "default_text_model": "grok-4",
        "image_models": (
            (
                "image_edit",
                "image_edit（grok CLI 内置图片工具 · 生图与编辑）",
                ("text_to_image", "image_to_image"),
                "builtin_tool",
            ),
        ),
        "default_image_model": "image_edit",
        "legacy_image_ids": ("image_edit", "grok-imagine-image-2.0", "grok-imagine-image"),
        "video_models": (),
    },
    {
        "id": "codex",
        "title": "OpenAI Codex 订阅授权",
        "path_label": "本机 codex login 的 ChatGPT 订阅",
        "bin": "codex",
        "login_command": "codex login",
        "device_auth_argv": ("login", "--device-auth"),
        "login_argv": ("login",),
        "verify_argv": ("login", "status"),
        "login_label": "网页发起 Codex 授权",
        "verify_label": "检查本机授权",
        "note": "只承认 ChatGPT 订阅登录，不改用 OpenAI API Key。图像 API 模型（如 gpt-image-1.5）请在「API 配置 → OpenAI 兼容」登记。",
        "text_models": (
            ("gpt-5", "gpt-5（ChatGPT 订阅主力文本）", ("text",), "model"),
            ("gpt-5.4", "gpt-5.4（长篇连载与深度推演）", ("text",), "model"),
            ("o3", "o3（逻辑推理与独立审评）", ("text",), "model"),
            ("o4-mini", "o4-mini（轻量规划与校对）", ("text",), "model"),
        ),
        "default_text_model": "gpt-5",
        "image_models": (
            (
                "image-generation",
                "image-generation（Codex 内置生图工具 · 非独立 API 模型）",
                ("text_to_image", "image_to_image"),
                "builtin_tool",
            ),
        ),
        "default_image_model": "image-generation",
        "legacy_image_ids": ("image-generation", "gpt-image-1"),
        "video_models": (),
    },
    {
        "id": "agy",
        "title": "Google AGY 授权登录",
        "path_label": "~/.gemini/antigravity-cli/jetski_state.pbtxt",
        "bin": "agy",
        "login_command": "agy",
        "device_auth_argv": (),
        "login_argv": (),
        "verify_argv": ("models",),
        "login_label": "查看终端授权说明",
        "verify_label": "在线验证授权",
        "note": "复用本机 Antigravity CLI 登录态，不读取令牌正文。image-generator 为内置图片子代理能力线索，非文本会话模型 ID。",
        "text_models": (
            ("gemini-4-neon-high", "gemini-4-neon-high（Gemini 4 Neon High · 主力文本与长上下文）", ("text",), "model"),
            ("gemini-4-neon-xhigh", "gemini-4-neon-xhigh（Gemini 4 Neon XHigh · 深度推演与审评）", ("text",), "model"),
            ("gemini-4-neon-medium", "gemini-4-neon-medium（Gemini 4 Neon Medium · 均衡创作）", ("text",), "model"),
            ("gemini-4-neon-low", "gemini-4-neon-low（Gemini 4 Neon Low · 快速草稿）", ("text",), "model"),
            ("gemini-4-carbon-high", "gemini-4-carbon-high（Gemini 4 Carbon High · 长程规划）", ("text",), "model"),
            ("gemini-4-hydrogen-high", "gemini-4-hydrogen-high（Gemini 4 Hydrogen High · 轻量快速）", ("text",), "model"),
            ("gemini-3.8-flash-high", "gemini-3.8-flash-high（Gemini 3.8 Flash High · 快速大纲）", ("text",), "model"),
            ("claude-sonnet-5-5-high", "claude-sonnet-5-5-high（Claude Sonnet 5.5 High · 文风精修与审评）", ("text",), "model"),
            ("claude-opus-5-5-high", "claude-opus-5-5-high（Claude Opus 5.5 High · 复杂审校）", ("text",), "model"),
        ),
        "default_text_model": "gemini-4-neon-high",
        "legacy_text_ids": ("gemini-2.5-pro", "gemini-2.5-flash", "claude-sonnet-4-5"),
        "image_models": (
            (
                "image-generator",
                "image-generator（AGY 内置图片子代理 · 非会话模型 ID）",
                ("text_to_image", "image_to_image"),
                "builtin_tool",
            ),
        ),
        "default_image_model": "image-generator",
        "legacy_image_ids": ("image-generator",),
        "video_models": (),
    },
)


def _clean(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def subscription_channel(provider: str) -> dict:
    found = next((item for item in SUBSCRIPTION_CHANNELS if item["id"] == provider), None)
    require(found is not None, "subscription", "未知的订阅授权通道", 404)
    return found


def subscription_spec_models(spec: dict) -> tuple[tuple[str, str, tuple[str, ...], str], ...]:
    return (
        *spec.get("text_models", ()),
        *spec.get("image_models", ()),
        *spec.get("video_models", ()),
    )


def subscription_model_entry(provider: str, model: str) -> dict | None:
    spec = subscription_channel(provider)
    key = model.strip()
    for category, group_key in (("text", "text_models"), ("image", "image_models"), ("video", "video_models")):
        for model_id, label, caps, entry_kind in spec.get(group_key, ()):
            if model_id == key:
                return {
                    "id": model_id,
                    "label": label,
                    "category": category,
                    "capabilities": tuple(caps),
                    "entry_kind": entry_kind,
                    "capability_source": "catalog",
                }
    return None


def subscription_model_capabilities(provider: str, model: str) -> tuple[tuple[str, ...], str]:
    """Return grounded catalog capabilities for a subscription entry. Never guesses from model names."""
    entry = subscription_model_entry(provider, model)
    if entry is not None:
        return entry["capabilities"], "catalog"
    return (), "unknown"


def is_known_image_model(provider: str, model: str) -> bool:
    spec = subscription_channel(provider)
    key = model.strip()
    known = {item[0] for item in spec["image_models"]} | set(spec.get("legacy_image_ids", ()))
    return key in known


def normalize_subscription_model(provider: str, model: str) -> str:
    spec = subscription_channel(provider)
    text = model.strip()
    allowed = {item[0] for item in subscription_spec_models(spec)}
    require(text in allowed or CLI_MODEL_ID.fullmatch(text) is not None, "model", "模型标识只填写公开的模型名")
    require(SECRET_HINT.search(text) is None, "model", "不要填写密钥，只填写公开的模型标识")
    require("token" not in text.lower() and "secret" not in text.lower(), "model", "不要填写密钥，只填写公开的模型标识")
    return text


def deprecated_model_notice(model_key: str) -> str:
    return DEPRECATED_API_MODELS.get(_clean(model_key), "")


def infer_platform_id(
    supplier: str = "",
    base_url: str = "",
    platform_id: str = "",
    transport: str = "http",
    cli_provider: str = "",
) -> str:
    explicit = _clean(platform_id).lower()
    known_ids = {item["id"] for item in API_PLATFORMS}
    if explicit in known_ids:
        return explicit
    if transport == "cli_oauth" and cli_provider in CLI_PROVIDERS:
        return f"cli-{cli_provider}"
    sup = _clean(supplier).lower()
    url = _clean(base_url).lower()
    if "openai" in sup or "api.openai.com" in url:
        return "openai"
    if sup == "xai" or "xai" in sup or "api.x.ai" in url:
        return "xai"
    if "火山" in sup or "ark" in sup or "volces.com" in url:
        return "ark"
    if "deepseek" in sup or "api.deepseek.com" in url:
        return "deepseek"
    if explicit and re.fullmatch(r"[a-z0-9_-]{1,64}", explicit):
        return explicit
    return "custom"


def catalog_model_caps(platform_id: str, model_key: str) -> tuple[str, ...] | None:
    key = _clean(model_key)
    for platform in API_PLATFORMS:
        if platform["id"] == platform_id:
            for mid, _, _, caps, _ in platform["models"]:
                if mid == key:
                    return tuple(caps)
    return None


def platforms_catalog() -> list[dict]:
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "supplier": item["supplier"],
            "base_url": item["base_url"],
            "auth_ref": item["auth_ref"],
            "models": [
                {
                    "id": mid,
                    "label": label,
                    "category": category,
                    "capabilities": list(caps),
                    "entry_kind": entry_kind,
                    "capability_source": "catalog",
                }
                for mid, label, category, caps, entry_kind in item["models"]
            ],
        }
        for item in API_PLATFORMS
    ]


def platform_label(platform_id: str, fallback: str = "") -> str:
    for item in API_PLATFORMS:
        if item["id"] == platform_id:
            return item["name"]
    return fallback or platform_id or "自定义兼容接口"


def empty_capability_defaults() -> dict[str, dict | None]:
    return {cap: None for cap in CAPABILITIES}


def clean_capability_defaults(scope_config, registry) -> dict[str, dict | None]:
    """Validate stored 6-capability global defaults against enabled HTTP API configs & grounded subscription catalog."""
    raw = (scope_config or {}).get("capability_defaults") if isinstance(scope_config, dict) else None
    incoming = raw if isinstance(raw, dict) else {}
    by_id = {row["id"]: row for row in registry.get("configurations") or []}
    cleaned = empty_capability_defaults()
    for cap in CAPABILITIES:
        entry = incoming.get(cap)
        if not isinstance(entry, dict):
            continue
        source = _clean(entry.get("source"))
        if source == "api":
            cid = _clean(entry.get("configuration_id"))
            model_key = _clean(entry.get("model_key"))
            row = by_id.get(cid)
            if (
                row
                and row.get("transport", "http") == "http"
                and row.get("enabled")
                and cap in (row.get("capabilities") or [])
                and model_key == _clean(row.get("model_key"))
            ):
                cleaned[cap] = {
                    "source": "api",
                    "configuration_id": cid,
                    "model_key": model_key,
                }
        elif source == "subscription":
            provider = _clean(entry.get("provider"))
            model_key = _clean(entry.get("model_key"))
            if provider in CLI_PROVIDERS and model_key:
                caps, cap_source = subscription_model_capabilities(provider, model_key)
                if cap_source == "catalog" and cap in caps:
                    cleaned[cap] = {
                        "source": "subscription",
                        "provider": provider,
                        "model_key": model_key,
                    }
    return cleaned


def apply_capability_default(registry, current_cap_defaults: dict, value: CapabilityDefaultInput) -> dict:
    cap = value.capability
    require(cap in CAPABILITIES, "capability", "未知的模型能力类别")
    result = {k: (dict(v) if isinstance(v, dict) else None) for k, v in empty_capability_defaults().items()}
    if isinstance(current_cap_defaults, dict):
        for k in CAPABILITIES:
            if isinstance(current_cap_defaults.get(k), dict):
                result[k] = dict(current_cap_defaults[k])
    source = _clean(value.source)
    if not source:
        result[cap] = None
        return result
    if source == "api":
        cid = _clean(value.configuration_id)
        row = next((item for item in registry.get("configurations") or [] if item["id"] == cid), None)
        require(row is not None, "not_found", "模型配置不存在", 404)
        require(
            row.get("transport", "http") == "http",
            "capability_default",
            "API 默认配置只能绑定 HTTP API 配置，订阅通道请在「订阅配置」中设置",
        )
        require(bool(row.get("enabled")), "capability_default", "只能把默认配置绑到已启用的 API 配置")
        req_model = _clean(value.model_key)
        require(
            bool(req_model) and req_model == _clean(row.get("model_key")),
            "capability_default",
            "提交的模型标识与服务端已保存配置不一致，请先保存或刷新后再设为默认",
        )
        require(
            cap in (row.get("capabilities") or []),
            "capability_default",
            f"配置「{row['name']}」未声明支持「{CAPABILITY_LABELS[cap]}」能力",
        )
        result[cap] = {
            "source": "api",
            "configuration_id": row["id"],
            "model_key": row["model_key"],
        }
        return result
    if source == "subscription":
        provider = _clean(value.provider)
        require(provider in CLI_PROVIDERS, "provider", "未知的订阅平台")
        model_key = normalize_subscription_model(provider, value.model_key)
        caps, cap_source = subscription_model_capabilities(provider, model_key)
        require(
            cap_source == "catalog" and bool(caps),
            "capability_default",
            f"模型 {model_key} 未在订阅目录中登记能力，无法设为「{CAPABILITY_LABELS[cap]}」默认",
        )
        require(
            cap in caps,
            "capability_default",
            f"模型 {model_key} 不支持「{CAPABILITY_LABELS[cap]}」能力",
        )
        result[cap] = {
            "source": "subscription",
            "provider": provider,
            "model_key": model_key,
        }
        return result
    require(False, "source", "未知的默认配置来源")
    return result


def api_status_summary(row: dict) -> tuple[str, str, str, bool]:
    conn = row.get("connection") or {}
    if conn.get("status") == "loaded":
        return "unverified", "已保存 · 未在线探测", conn.get("message") or "配置已保存，可按需运行在线连通探测。", False
    return "invalid", "连接未就绪", conn.get("message") or "请补全网关地址或模型标识。", False


def sub_status_summary(info: dict | None) -> tuple[str, str, str, bool]:
    if not isinstance(info, dict):
        return "unverified", "待检查本机状态", "打开订阅配置可刷新本机授权状态。", False
    st = info.get("status") or {}
    ready = bool(st.get("ready"))
    verified = bool(st.get("verified"))
    code = st.get("status") or "unauthorized"
    msg = st.get("message") or ""
    if ready and verified:
        return "ready", "已授权并验证", msg, True
    if ready:
        return "unverified", "本机已登录", msg, False
    if code == "cli_missing":
        return "cli_missing", "未安装 CLI", msg, False
    if code == "expired":
        return "needs_auth", "授权已过期", msg, False
    if code == "api_key_only":
        return "needs_auth", "仅 API Key", msg, False
    if code == "file_detected":
        return "needs_auth", "检测到文件 · 待验证", msg, False
    return "needs_auth", "未完成授权", msg, False


def _entry_capabilities(entry: dict, by_id: dict[str, dict]) -> tuple[str, ...]:
    if entry.get("source") == "api":
        row = by_id.get(_clean(entry.get("configuration_id")))
        return tuple(row.get("capabilities") or ()) if row else ()
    if entry.get("source") == "subscription":
        caps, _ = subscription_model_capabilities(_clean(entry.get("provider")), _clean(entry.get("model_key")))
        return caps
    return ()


def _sub_info_from_view(provider: str, subscription_view) -> dict | None:
    if isinstance(subscription_view, dict):
        for item in subscription_view.get("channels") or []:
            if item.get("id") == provider:
                return item
    return None


def effective_capabilities_view(
    cap_defaults: dict,
    by_id: dict[str, dict],
    snap: dict,
    subscription_view=None,
) -> dict[str, dict]:
    def resolve_one(meta: dict) -> dict:
        cap = meta["id"]
        base = {
            **meta,
            "bound": False,
            "fallback": False,
            "fallback_from": "",
            "fallback_blocked_reason": "",
            "source": "",
            "source_label": "未设置",
            "platform_id": "",
            "platform_label": "",
            "configuration_id": "",
            "provider": "",
            "name": "",
            "model_key": "",
            "entry_kind": "model",
            "status": "unset",
            "status_label": "未设置",
            "status_message": "尚未指定默认模型。",
            "verified": False,
        }
        entry = cap_defaults.get(cap)
        if isinstance(entry, dict):
            if entry.get("source") == "api":
                row = by_id.get(_clean(entry.get("configuration_id")))
                if row and row.get("transport", "http") == "http":
                    status, status_label, status_message, verified = api_status_summary(row)
                    return {
                        **base,
                        "bound": True,
                        "source": "api",
                        "source_label": "API 配置",
                        "platform_id": row["platform_id"],
                        "platform_label": platform_label(row["platform_id"], row["supplier"]),
                        "configuration_id": row["id"],
                        "name": row["name"],
                        "model_key": row["model_key"],
                        "status": status,
                        "status_label": status_label,
                        "status_message": status_message,
                        "verified": verified,
                    }
            elif entry.get("source") == "subscription":
                provider = _clean(entry.get("provider"))
                spec = subscription_channel(provider)
                info = _sub_info_from_view(provider, subscription_view)
                status, status_label, status_message, verified = sub_status_summary(info)
                model_key = _clean(entry.get("model_key"))
                cat_entry = subscription_model_entry(provider, model_key)
                return {
                    **base,
                    "bound": True,
                    "source": "subscription",
                    "source_label": "订阅配置",
                    "platform_id": provider,
                    "platform_label": spec["title"],
                    "provider": provider,
                    "name": spec["title"],
                    "model_key": model_key,
                    "entry_kind": cat_entry["entry_kind"] if cat_entry else "model",
                    "status": status,
                    "status_label": status_label,
                    "status_message": status_message,
                    "verified": verified,
                }

        if cap == "text":
            write_slot = (snap.get("by_purpose") or {}).get("write") or {}
            if write_slot.get("model_key"):
                cid = _clean(write_slot.get("configuration_id"))
                if cid and cid in by_id:
                    row = by_id[cid]
                    if row.get("transport") == "cli_oauth":
                        provider = _clean(row.get("cli_provider"))
                        spec = subscription_channel(provider)
                        info = _sub_info_from_view(provider, subscription_view)
                        status, status_label, status_message, verified = sub_status_summary(info)
                        return {
                            **base,
                            "fallback": True,
                            "fallback_from": "legacy_cli_route",
                            "source": "subscription",
                            "source_label": "订阅配置（旧 CLI 登记沿用）",
                            "platform_id": provider,
                            "platform_label": spec["title"],
                            "configuration_id": row["id"],
                            "provider": provider,
                            "name": row["name"],
                            "model_key": row["model_key"],
                            "status": status,
                            "status_label": status_label,
                            "status_message": status_message,
                            "verified": verified,
                        }
                    status, status_label, status_message, verified = api_status_summary(row)
                    return {
                        **base,
                        "fallback": True,
                        "fallback_from": "legacy_write",
                        "source": "api",
                        "source_label": "API 配置（沿用写作配置）",
                        "platform_id": row["platform_id"],
                        "platform_label": platform_label(row["platform_id"], row["supplier"]),
                        "configuration_id": row["id"],
                        "name": row["name"],
                        "model_key": row["model_key"],
                        "status": status,
                        "status_label": status_label,
                        "status_message": status_message,
                        "verified": verified,
                    }
                return {
                    **base,
                    "fallback": True,
                    "fallback_from": "environment",
                    "source": "environment",
                    "source_label": "进程环境（兜底）",
                    "platform_id": "environment",
                    "platform_label": "进程环境变量",
                    "name": write_slot.get("name") or "进程环境",
                    "model_key": write_slot.get("model_key") or "",
                    "status": "unverified",
                    "status_label": "环境变量兜底",
                    "status_message": "当前由服务端环境变量提供默认文本路由。",
                    "verified": False,
                }

        if cap in ("text_to_video", "image_to_video"):
            video_entry = cap_defaults.get("video")
            if isinstance(video_entry, dict):
                video_caps = _entry_capabilities(video_entry, by_id)
                if cap in video_caps:
                    video_meta = next(item for item in CAPABILITY_META if item["id"] == "video")
                    resolved_video = resolve_one(video_meta)
                    return {
                        **resolved_video,
                        **meta,
                        "bound": False,
                        "fallback": True,
                        "fallback_from": "video",
                        "fallback_blocked_reason": "",
                        "status_message": f"按输入能力匹配沿用「生视频」默认（{resolved_video['model_key']}）。",
                    }
                video_model = _clean(video_entry.get("model_key"))
                return {
                    **base,
                    "fallback_blocked_reason": (
                        f"「生视频」默认模型 {video_model} 未声明支持「{CAPABILITY_LABELS[cap]}」，不自动回退。"
                    ),
                    "status_message": f"未设置；「生视频」默认（{video_model}）不支持「{CAPABILITY_LABELS[cap]}」，未回退。",
                }
        return base

    return {meta["id"]: resolve_one(meta) for meta in CAPABILITY_META}


def capability_candidates_view(public_configs: list[dict], subscription_view=None) -> dict[str, list[dict]]:
    sub_by_id = {}
    if isinstance(subscription_view, dict):
        for item in subscription_view.get("channels") or []:
            sub_by_id[item["id"]] = item

    out: dict[str, list[dict]] = {cap: [] for cap in CAPABILITIES}
    for row in public_configs:
        if not row.get("enabled") or row.get("transport", "http") != "http":
            continue
        _, status_label, _, verified = api_status_summary(row)
        for cap in row.get("capabilities") or []:
            if cap in out:
                out[cap].append(
                    {
                        "value": f"api:{row['id']}",
                        "source": "api",
                        "configuration_id": row["id"],
                        "provider": "",
                        "platform_id": row["platform_id"],
                        "platform_label": platform_label(row["platform_id"], row["supplier"]),
                        "name": row["name"],
                        "model_key": row["model_key"],
                        "entry_kind": "model",
                        "verified": verified,
                        "status_label": status_label,
                    }
                )
    for spec in SUBSCRIPTION_CHANNELS:
        info = sub_by_id.get(spec["id"])
        _, sub_label, _, sub_verified = sub_status_summary(info)
        for group_key in ("text_models", "image_models", "video_models"):
            for model_id, label, caps, entry_kind in spec.get(group_key, ()):
                for cap in caps:
                    if cap in out:
                        out[cap].append(
                            {
                                "value": f"subscription:{spec['id']}:{model_id}",
                                "source": "subscription",
                                "configuration_id": "",
                                "provider": spec["id"],
                                "platform_id": spec["id"],
                                "platform_label": spec["title"],
                                "name": label,
                                "model_key": model_id,
                                "entry_kind": entry_kind,
                                "verified": sub_verified,
                                "status_label": sub_label,
                            }
                        )
    return out
