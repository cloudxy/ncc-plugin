"""Local CLI subscription status. Tokens stay on disk and never enter these results."""

import datetime
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from ncc_data.creation.model_route import SECRET_HINT
from ncc_shared.errors import require

PROVIDERS = ("grok", "codex", "agy")
MODEL_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_CHANNELS = (
    {
        "id": "grok",
        "title": "xAI Grok 订阅授权",
        "path_label": "~/.grok/auth.json",
        "bin": "grok",
        "login_command": "grok login --oauth",
        "login_argv": ("login", "--oauth"),
        "verify_argv": ("models",),
        "login_label": "调起浏览器授权登录",
        "verify_label": "在线验证授权",
        "note": "复用本机 grok CLI 登录态。服务不回传令牌，也不改用 XAI_API_KEY。与「模型与连接」里的按量接口分开。",
        "models": (
            ("image_edit", "image_edit（终端 grok CLI 内置）"),
            ("grok-imagine-image-2.0", "grok-imagine-image-2.0"),
            ("grok-imagine-image", "grok-imagine-image"),
        ),
        "default_model": "image_edit",
    },
    {
        "id": "codex",
        "title": "OpenAI Codex 订阅授权",
        "path_label": "本机 codex login 的 ChatGPT 订阅",
        "bin": "codex",
        "login_command": "codex login",
        "login_argv": ("login",),
        "verify_argv": ("login", "status"),
        "login_label": "打开终端完成 Codex 授权",
        "verify_label": "检查本机授权",
        "note": "只承认 ChatGPT 订阅登录。Codex 若用 API Key 登录，这里视为未完成订阅授权，也不会拿 OpenAI API Key 顶上。",
        "models": (("image-generation", "Codex 内置生图（GPT Image）"),),
        "default_model": "image-generation",
    },
    {
        "id": "agy",
        "title": "Google AGY 授权登录",
        "path_label": "~/.gemini/antigravity-cli/jetski_state.pbtxt",
        "bin": "agy",
        "login_command": "agy",
        "login_argv": (),
        "verify_argv": ("models",),
        "login_label": "打开终端完成 AGY 授权",
        "verify_label": "在线验证授权",
        "note": "复用本机 Antigravity CLI 登录态。服务不读取令牌正文，也不把它当作 API Key。",
        "models": (("image-generator", "image-generator（AGY 内置生图）"),),
        "default_model": "image-generator",
    },
)


def channels():
    return _CHANNELS


def channel(provider: str) -> dict:
    found = next((item for item in _CHANNELS if item["id"] == provider), None)
    require(found is not None, "subscription", "未知的订阅授权通道", 404)
    return found


def normalize_model(provider: str, model: str) -> str:
    spec = channel(provider)
    text = model.strip()
    allowed = {item[0] for item in spec["models"]}
    require(text in allowed or MODEL_ID.fullmatch(text) is not None, "model", "模型标识只填写公开的模型名")
    require(SECRET_HINT.search(text) is None, "model", "不要填写密钥，只填写公开的模型标识")
    require("token" not in text.lower() and "secret" not in text.lower(), "model", "不要填写密钥，只填写公开的模型标识")
    return text


def _mask(value: str) -> str | None:
    text = value.strip()
    if not text or len(text) > 80 or "sk-" in text.lower() or "token" in text.lower():
        return None
    if "@" in text:
        local, _, domain = text.partition("@")
        head = local[:2] if len(local) > 2 else local[:1]
        return f"{head}***@{domain}"
    if len(text) <= 8:
        return text[:2] + "***"
    return f"{text[:4]}…{text[-4:]}"


def _expiry(entry: dict):
    value = entry.get("expires_at")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _grok_file(path: Path) -> tuple[str, str | None]:
    """Classify ~/.grok/auth.json. The access key is never returned."""
    if not path.is_file():
        return "missing", None
    try:
        data = json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        return "unreadable", None
    entries = []
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, dict) and isinstance(value.get("key"), str) and value["key"].strip():
                entries.append(value)
    if not entries:
        return "empty", None
    now = datetime.datetime.now(datetime.timezone.utc)
    fresh = [entry for entry in entries if (expiry := _expiry(entry)) is None or expiry > now]
    chosen = (fresh or entries)[0]
    raw = str(chosen.get("user_id") or chosen.get("email") or "")
    account = _mask(raw)
    return ("ready" if fresh else "expired"), account


def _status(provider: str, **fields) -> dict:
    return {
        "ready": False,
        "status": "unauthorized",
        "cli_installed": False,
        "account": None,
        "message": "",
        "verified": False,
        **fields,
    }


def grok_status(home: Path, which) -> dict:
    spec = channel("grok")
    cli = bool(which(spec["bin"]))
    kind, account = _grok_file(home / ".grok" / "auth.json")
    if kind == "ready":
        message = "本机 Grok 订阅登录态可用。未向模型发起请求，也未回传令牌。"
        if account:
            message = f"本机 Grok 订阅登录态可用（账号 {account}）。未向模型发起请求，也未回传令牌。"
        return _status("grok", ready=True, status="authorized", cli_installed=cli, account=account, message=message)
    if kind == "expired":
        return _status(
            "grok",
            status="expired",
            cli_installed=cli,
            account=account,
            message="Grok 登录态已过期。请重新授权；不会改用按量 API Key。",
        )
    if kind == "unreadable":
        return _status("grok", status="check_failed", cli_installed=cli, message="Grok 登录态文件无法读取。请在终端重新登录。")
    if kind == "empty":
        return _status(
            "grok",
            status="file_detected",
            cli_installed=cli,
            message="已检测到 Grok 状态文件，但缺少有效订阅令牌。请运行 grok login --oauth 完成登录。",
        )
    if not cli:
        return _status("grok", status="cli_missing", message="未检测到本机 grok CLI。安装后运行 grok login --oauth。")
    return _status("grok", cli_installed=True, message="尚未登录 Grok。可打开终端完成授权，或复制命令 grok login --oauth。")


def agy_status(home: Path, which) -> dict:
    cli = bool(which("agy"))
    state = home / ".gemini" / "antigravity-cli" / "jetski_state.pbtxt"
    try:
        has_state = state.is_file() and state.stat().st_size > 0
    except OSError:
        has_state = False
    if not cli and has_state:
        return _status(
            "agy",
            status="file_detected",
            cli_installed=False,
            message="已检测到本机 AGY 状态文件，但未找到 agy CLI。安装后请运行在线验证确认登录。",
        )
    if cli and has_state:
        return _status(
            "agy",
            ready=False,
            status="file_detected",
            cli_installed=True,
            message="已检测到本机 AGY 状态文件，尚未证实登录授权。请点击「在线验证授权」确认，未证实前不计入就绪。",
        )
    if not cli:
        return _status("agy", status="cli_missing", message="未检测到本机 agy CLI。安装 Antigravity CLI 后在终端运行 agy。")
    return _status("agy", cli_installed=True, message="已安装 agy CLI，尚未检测到授权文件。请在终端运行 agy 完成登录。")


def _run(binary: str, args: tuple[str, ...], run, env: dict | None, timeout: int):
    child = dict(env if env is not None else os.environ)
    for name in ("XAI_API_KEY", "OPENAI_API_KEY", "NCC_MODEL_KEY", "ARK_API_KEY", "DEEPSEEK_API_KEY"):
        child.pop(name, None)
    try:
        completed = run(
            [binary, *args],
            env=child,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = _ANSI.sub("", f"{completed.stdout or ''}\n{completed.stderr or ''}").lower()
    return completed.returncode, text


def codex_status(which, run, env=None) -> dict:
    binary = which("codex")
    if not binary:
        return _status("codex", status="cli_missing", message="未检测到本机 Codex CLI。安装后运行 codex login，并选择 ChatGPT 登录。")
    outcome = _run(binary, ("login", "status"), run, env, 8)
    if outcome is None:
        return _status("codex", cli_installed=True, status="check_failed", message="Codex 授权检查未完成。请稍后刷新，或在终端运行 codex login status。")
    code, output = outcome
    if code != 0 and any(value in output for value in ("operation not permitted", "permission denied")):
        return _status("codex", cli_installed=True, status="check_failed", message="Codex 授权检查被系统权限阻止。请检查服务进程权限后刷新。")
    if code == 0 and re.search(r"(?m)^logged in (?:using|with) chatgpt\b", output.strip()):
        return _status(
            "codex",
            ready=True,
            status="authorized",
            cli_installed=True,
            message="本机 Codex 已通过 ChatGPT 订阅登录。授权由 Codex CLI 保管，页面不接收密钥。",
        )
    if code == 0 and "api key" in output:
        return _status(
            "codex",
            cli_installed=True,
            status="api_key_only",
            message="Codex 当前是 API Key 登录。订阅授权需要运行 codex login，并选择 ChatGPT 登录。",
        )
    return _status("codex", cli_installed=True, message="未确认 Codex 的 ChatGPT 订阅登录。请在终端运行 codex login。")


def _has_supported_verify_signal(provider: str, spec: dict, output: str) -> bool:
    stripped = (output or "").strip()
    if not stripped:
        return False
    known_models = [model_id.lower() for model_id, _ in spec.get("models", ())]
    if any(m in stripped for m in known_models):
        return True
    if provider == "grok":
        return any(token in stripped for token in ("grok-", "image_edit", "models"))
    if provider == "agy":
        return any(token in stripped for token in ("gemini", "claude", "image-generator", "models"))
    return False


def verify_channel(provider: str, home: Path, which, run, env=None) -> dict:
    spec = channel(provider)
    if provider == "codex":
        info = codex_status(which, run, env)
        info["verified"] = bool(info["ready"])
        return info
    binary = which(spec["bin"])
    base = grok_status(home, which) if provider == "grok" else agy_status(home, which)
    if not binary:
        return {**base, "ready": False, "status": "cli_missing", "cli_installed": False, "verified": False}
    outcome = _run(binary, spec["verify_argv"], run, env, 20)
    if outcome is None:
        return {
            **base,
            "ready": False,
            "status": "check_failed",
            "cli_installed": True,
            "verified": False,
            "message": f"{spec['title']}在线验证未完成。请确认网络，或稍后在终端重试。",
        }
    code, output = outcome
    signed_out = any(
        phrase in output
        for phrase in ("not logged in", "not signed in", "login required", "unauthenticated", "unauthorized")
    )
    if code == 0 and not signed_out and _has_supported_verify_signal(provider, spec, output):
        return {
            **base,
            "ready": True,
            "status": "authorized",
            "cli_installed": True,
            "verified": True,
            "message": f"{spec['title']}在线验证通过。未发起付费生成，也未回传令牌。",
        }
    if code == 0 and not signed_out:
        return {
            **base,
            "ready": False,
            "status": "check_failed",
            "cli_installed": True,
            "verified": False,
            "message": f"{spec['title']}验证命令未返回可识别的授权模型信息，未计入就绪。",
        }
    if not signed_out and any(word in output for word in ("fetch failed", "network", "timed out", "dns", "connection")):
        return {
            **base,
            "ready": False,
            "status": "check_failed",
            "cli_installed": True,
            "verified": False,
            "message": f"{spec['title']}在线连接失败。请检查本机网络后重试。",
        }
    return {
        **base,
        "ready": False,
        "status": "expired" if base["status"] == "expired" else "unauthorized",
        "cli_installed": True,
        "verified": False,
        "message": f"{spec['title']}尚未完成在线授权或登录已过期。请按终端命令重新登录。",
    }


def saved_model(saved, provider: str) -> str:
    spec = channel(provider)
    raw = saved.get(provider) if isinstance(saved, dict) else None
    model = raw.get("model") if isinstance(raw, dict) else ""
    text = model.strip() if isinstance(model, str) else ""
    if text and (text in {item[0] for item in spec["models"]} or MODEL_ID.fullmatch(text)):
        if SECRET_HINT.search(text) is None:
            return text
    return spec["default_model"]


def collect_subscriptions(saved, home: Path | None = None, which=shutil.which, run=subprocess.run, env=None) -> dict:
    root = home or Path.home()
    probes = {
        "grok": lambda: grok_status(root, which),
        "codex": lambda: codex_status(which, run, env),
        "agy": lambda: agy_status(root, which),
    }
    rows = []
    for spec in _CHANNELS:
        status = probes[spec["id"]]()
        rows.append(
            {
                "id": spec["id"],
                "title": spec["title"],
                "path_label": spec["path_label"],
                "login_command": spec["login_command"],
                "login_label": spec["login_label"],
                "verify_label": spec["verify_label"],
                "note": spec["note"],
                "models": [{"id": model_id, "label": label} for model_id, label in spec["models"]],
                "model": saved_model(saved, spec["id"]),
                "status": status,
            }
        )
    return {"channels": rows, "ready_count": sum(1 for row in rows if row["status"]["ready"])}


def open_login(provider: str, which=shutil.which, run=subprocess.run) -> dict:
    spec = channel(provider)
    binary = which(spec["bin"])
    command = spec["login_command"]
    if not binary:
        return {"started": False, "command": command, "message": f"本机未找到 {spec['bin']}。请先安装，再运行 {command}。"}
    if sys.platform != "darwin" or not which("osascript"):
        return {"started": False, "command": command, "message": f"请在终端运行 {command}。完成后回到本页刷新授权状态。"}
    argv = " ".join(shlex.quote(part) for part in (binary, *spec["login_argv"]))
    escaped = argv.replace("\\", "\\\\").replace('"', '\\"')
    script = f'tell application "Terminal"\nactivate\ndo script "{escaped}"\nend tell'
    try:
        completed = run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=8,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        started = completed.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        started = False
    if started:
        return {"started": True, "command": command, "message": f"已打开终端。请按提示完成授权，然后回到本页刷新。命令是 {command}。"}
    return {"started": False, "command": command, "message": f"未能打开终端。请复制命令 {command} 并在终端运行。"}
