"""Local CLI subscription status and managed headless Device-Auth login.

Tokens stay on disk in each CLI's own store and never enter API responses or audit logs.
"""

import asyncio
import contextlib
import datetime
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from ncc_data.creation.model_route import SECRET_HINT
from ncc_shared.errors import require

PROVIDERS = ("grok", "codex", "agy")
OAUTH_TTL_SECONDS = 180
STRIPPED_API_KEYS = (
    "XAI_API_KEY",
    "OPENAI_API_KEY",
    "NCC_MODEL_KEY",
    "ARK_API_KEY",
    "DEEPSEEK_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
)
MODEL_ID = re.compile(r"^[A-Za-z0-9_.:/-]{1,128}$")
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_URL_RE = re.compile(r"https://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+")
_HYPHEN_CODE_RE = re.compile(r"\b([A-Z0-9]{3,8}-[A-Z0-9]{3,8})\b")
_LABELED_CODE_RE = re.compile(r"(?:code|验证码|设备码)\s*[:：=]?\s*([A-Z0-9-]{4,16})\b", re.I)
_CHANNELS = (
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
        "note": "复用本机 grok CLI 登录态。服务不回传令牌，也不改用 XAI_API_KEY。可直接绑定到写作与审评模型。",
        "models": (
            ("grok-4", "grok-4（对话与创作）"),
            ("grok-3", "grok-3（对话与审评）"),
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
        "device_auth_argv": ("login", "--device-auth"),
        "login_argv": ("login",),
        "verify_argv": ("login", "status"),
        "login_label": "网页发起 Codex 授权",
        "verify_label": "检查本机授权",
        "note": "只承认 ChatGPT 订阅登录。Codex 若用 API Key 登录，这里视为未完成订阅授权，也不会拿 OpenAI API Key 顶上。",
        "models": (
            ("gpt-5", "gpt-5（ChatGPT 订阅对话与创作）"),
            ("o3", "o3（深度推理与审评）"),
            ("image-generation", "Codex 内置生图（GPT Image）"),
        ),
        "default_model": "image-generation",
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
        "note": "复用本机 Antigravity CLI 登录态。服务不读取令牌正文，也不把它当作 API Key。",
        "models": (
            ("gemini-2.5-pro", "gemini-2.5-pro（对话与创作）"),
            ("claude-sonnet-4-5", "claude-sonnet-4-5（对话与审评）"),
            ("image-generator", "image-generator（AGY 内置生图）"),
        ),
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


def _has_refresh_token(entry: dict) -> bool:
    rt = entry.get("refresh_token")
    return isinstance(rt, str) and bool(rt.strip())


def _grok_file(path: Path) -> tuple[str, str | None]:
    """Classify ~/.grok/auth.json. The access key and refresh token are never returned."""
    if not path.is_file():
        return "missing", None
    try:
        data = json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        return "unreadable", None
    entries = []
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, dict) and (
                (isinstance(value.get("key"), str) and value["key"].strip())
                or _has_refresh_token(value)
            ):
                entries.append(value)
    if not entries:
        return "empty", None
    now = datetime.datetime.now(datetime.UTC)
    fresh = [
        entry
        for entry in entries
        if (expiry := _expiry(entry)) is None or expiry > now or _has_refresh_token(entry)
    ]
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


def clean_oauth_env(env: dict | None = None) -> dict[str, str]:
    child = dict(env if env is not None else os.environ)
    for name in STRIPPED_API_KEYS:
        child.pop(name, None)
    child.setdefault("NO_COLOR", "1")
    child.setdefault("TERM", "dumb")
    return child


def _run(binary: str, args: tuple[str, ...], run, env: dict | None, timeout: int):
    child = clean_oauth_env(env)
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
    _ = (which, run)
    command = spec["login_command"]
    return {
        "started": False,
        "command": command,
        "message": f"请在本地终端执行 {command} 完成授权，然后回到本页点击「刷新授权状态」。",
    }


def extract_device_auth_info(raw_text: str) -> tuple[str | None, str | None]:
    """Extract only safe https:// verification URL and short device code; never return raw logs or tokens."""
    cleaned = _ANSI.sub("", raw_text or "")
    auth_url: str | None = None
    for match in _URL_RE.finditer(cleaned):
        candidate = match.group(0).rstrip(".,;:)<>\"']")
        parts = urlsplit(candidate)
        lowered = candidate.lower()
        if (
            parts.scheme == "https"
            and parts.hostname
            and len(candidate) <= 512
            and SECRET_HINT.search(candidate) is None
            and "access_token=" not in lowered
            and "refresh_token=" not in lowered
            and "api_key=" not in lowered
        ):
            auth_url = candidate
            break

    text_without_urls = _URL_RE.sub(" ", cleaned)
    device_code: str | None = None
    for pattern in (_HYPHEN_CODE_RE, _LABELED_CODE_RE):
        for match in pattern.finditer(text_without_urls):
            code = match.group(1).strip().upper()
            if (
                4 <= len(code) <= 20
                and SECRET_HINT.search(code) is None
                and not code.startswith("SK-")
                and any(ch.isdigit() or ch == "-" for ch in code)
            ):
                device_code = code
                break
        if device_code is None and pattern is _LABELED_CODE_RE:
            for match in pattern.finditer(text_without_urls):
                code = match.group(1).strip().upper()
                if (
                    4 <= len(code) <= 16
                    and code not in {"HTTP", "HTTPS", "CODE", "AUTH", "OAUTH", "TRUE", "FALSE", "NULL"}
                    and SECRET_HINT.search(code) is None
                    and not code.startswith("SK-")
                ):
                    device_code = code
                    break
        if device_code:
            break
    return auth_url, device_code


@dataclass
class _ManagedLoginSession:
    session_id: str
    provider: str
    command: str
    created_monotonic: float
    ttl_seconds: int
    proc: Any
    initial_ready: bool = False
    auth_url: str | None = None
    device_code: str | None = None
    closed_state: str | None = None
    chunks: list[str] = field(default_factory=list)
    total_chars: int = 0
    reader_task: asyncio.Task | None = None
    expiry_task: asyncio.Task | None = None


_ACTIVE_BY_PROVIDER: dict[str, _ManagedLoginSession] = {}
_SESSIONS_BY_ID: dict[str, _ManagedLoginSession] = {}


async def _terminate_proc(proc: Any) -> None:
    if proc is None or getattr(proc, "returncode", None) is not None:
        return
    with contextlib.suppress(ProcessLookupError, OSError):
        proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=1.5)
    except Exception:
        with contextlib.suppress(ProcessLookupError, OSError):
            proc.kill()
        with contextlib.suppress(Exception):
            await asyncio.wait_for(proc.wait(), timeout=1.0)


async def _close_session(session: _ManagedLoginSession, state: str) -> None:
    if session.closed_state is None:
        session.closed_state = state
    await _terminate_proc(session.proc)
    if session.reader_task is not None and not session.reader_task.done():
        session.reader_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await session.reader_task
    if (
        session.expiry_task is not None
        and session.expiry_task is not asyncio.current_task()
        and not session.expiry_task.done()
    ):
        session.expiry_task.cancel()
    if _ACTIVE_BY_PROVIDER.get(session.provider) is session:
        _ACTIVE_BY_PROVIDER.pop(session.provider, None)


async def _sweep_expired_sessions() -> None:
    now = time.monotonic()
    stale_ids = [
        sid
        for sid, sess in list(_SESSIONS_BY_ID.items())
        if now - sess.created_monotonic > sess.ttl_seconds + 60
    ]
    for sid in stale_ids:
        sess = _SESSIONS_BY_ID.pop(sid, None)
        if sess is not None:
            await _close_session(sess, "expired")


async def _drain_login_output(session: _ManagedLoginSession) -> None:
    stream = getattr(session.proc, "stdout", None)
    if stream is None:
        return
    try:
        while session.total_chars < 16_384:
            chunk = await stream.read(512)
            if not chunk:
                break
            text = chunk.decode("utf-8", errors="replace") if isinstance(chunk, (bytes, bytearray)) else str(chunk)
            session.chunks.append(text)
            session.total_chars += len(text)
            url, code = extract_device_auth_info("".join(session.chunks))
            if url and not session.auth_url:
                session.auth_url = url
            if code and not session.device_code:
                session.device_code = code
    except asyncio.CancelledError:
        raise
    except Exception:
        return


async def _auto_expire(session: _ManagedLoginSession) -> None:
    try:
        await asyncio.sleep(session.ttl_seconds)
        if getattr(session.proc, "returncode", None) is None and session.closed_state is None:
            await _close_session(session, "expired")
    except asyncio.CancelledError:
        return


async def _default_spawner(argv: list[str], env: dict[str, str]):
    child_env = dict(env)
    child_env["BROWSER"] = "/usr/bin/true"
    return await asyncio.create_subprocess_exec(
        *argv,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=child_env,
    )


def _probe_single_channel(
    provider: str,
    saved: dict,
    home: Path,
    which,
    run,
    env: dict | None,
) -> dict:
    spec = channel(provider)
    if provider == "grok":
        status = grok_status(home, which)
    elif provider == "codex":
        status = codex_status(which, run, env)
    else:
        status = agy_status(home, which)
    return {
        "id": spec["id"],
        "title": spec["title"],
        "path_label": spec["path_label"],
        "login_command": spec["login_command"],
        "login_label": spec["login_label"],
        "verify_label": spec["verify_label"],
        "note": spec["note"],
        "models": [{"id": mid, "label": label} for mid, label in spec["models"]],
        "model": saved_model(saved, spec["id"]),
        "status": status,
    }


async def start_oauth_login(
    provider: str,
    *,
    saved: dict | None = None,
    home: Path | None = None,
    which=shutil.which,
    run=subprocess.run,
    spawner=None,
    env: dict | None = None,
    ttl_seconds: int = OAUTH_TTL_SECONDS,
    startup_wait: float = 2.5,
) -> dict:
    spec = channel(provider)
    await _sweep_expired_sessions()
    root = home or Path.home()
    device_argv = spec.get("device_auth_argv") or ()
    if not device_argv:
        return {
            "provider": provider,
            "started": False,
            "mode": "manual",
            "session_id": None,
            "state": "manual",
            "auth_url": None,
            "device_code": None,
            "command": spec["login_command"],
            "expires_in": None,
            "message": f"{spec['title']}暂不支持网页设备码流。请在终端执行 {spec['login_command']} 完成登录，随后点击「在线验证授权」。",
        }

    previous = _ACTIVE_BY_PROVIDER.pop(provider, None)
    if previous is not None:
        await _close_session(previous, "failed")

    command_text = f"{spec['bin']} {' '.join(device_argv)}"
    binary = which(spec["bin"])
    if not binary:
        return {
            "provider": provider,
            "started": False,
            "mode": "manual",
            "session_id": None,
            "state": "failed",
            "auth_url": None,
            "device_code": None,
            "command": command_text,
            "expires_in": None,
            "message": f"未检测到本机 {spec['bin']} CLI。请先安装后再发起网页授权。",
        }

    initial_channel = await asyncio.to_thread(
        _probe_single_channel, provider, saved or {}, root, which, run, env
    )
    spawn = spawner or _default_spawner
    clean_env = clean_oauth_env(env)
    try:
        proc = await spawn([binary, *device_argv], clean_env)
    except OSError:
        return {
            "provider": provider,
            "started": False,
            "mode": "manual",
            "session_id": None,
            "state": "failed",
            "auth_url": None,
            "device_code": None,
            "command": command_text,
            "expires_in": None,
            "message": f"无法启动 {spec['bin']} 设备码授权进程，请改用终端执行 {command_text}。",
        }

    session = _ManagedLoginSession(
        session_id=str(uuid4()),
        provider=provider,
        command=command_text,
        created_monotonic=time.monotonic(),
        ttl_seconds=ttl_seconds,
        proc=proc,
        initial_ready=bool(initial_channel["status"]["ready"]),
    )
    session.reader_task = asyncio.create_task(_drain_login_output(session))
    session.expiry_task = asyncio.create_task(_auto_expire(session))
    _ACTIVE_BY_PROVIDER[provider] = session
    _SESSIONS_BY_ID[session.session_id] = session

    deadline = time.monotonic() + startup_wait
    while time.monotonic() < deadline:
        if (session.auth_url and session.device_code) or getattr(proc, "returncode", None) is not None:
            break
        await asyncio.sleep(0.05)
    if getattr(proc, "returncode", None) is not None and session.reader_task is not None:
        with contextlib.suppress(Exception):
            await asyncio.wait_for(session.reader_task, timeout=0.5)

    expires_in = max(0, int(session.ttl_seconds - (time.monotonic() - session.created_monotonic)))
    rc = getattr(proc, "returncode", None)
    if rc is None:
        state = "pending"
        started = True
        if session.auth_url and session.device_code:
            msg = "已生成设备授权码。请在新窗口打开授权链接并输入设备码，完成后本页将自动更新。"
        elif session.auth_url:
            msg = "已获取授权链接，请在新窗口完成登录授权。"
        else:
            msg = "授权进程已启动，正在等待设备码与授权链接…"
    elif rc == 0:
        await _close_session(session, "authorized")
        state = "authorized"
        started = True
        msg = f"{spec['title']}已完成授权。"
    else:
        await _close_session(session, "failed")
        state = "failed"
        started = False
        msg = f"{spec['title']}设备码授权未成功完成，请重试或在终端执行 {command_text}。"

    return {
        "provider": provider,
        "started": started,
        "mode": "device_auth",
        "session_id": session.session_id,
        "state": state,
        "auth_url": session.auth_url,
        "device_code": session.device_code,
        "command": command_text,
        "expires_in": expires_in,
        "message": msg,
    }


async def poll_oauth_login(
    provider: str,
    session_id: str,
    *,
    saved: dict | None = None,
    home: Path | None = None,
    which=shutil.which,
    run=subprocess.run,
    env: dict | None = None,
) -> dict:
    spec = channel(provider)
    await _sweep_expired_sessions()
    session = _SESSIONS_BY_ID.get(session_id)
    require(
        session is not None and session.provider == provider,
        "not_found",
        "授权会话不存在或已过期",
        404,
    )
    root = home or Path.home()
    elapsed = time.monotonic() - session.created_monotonic
    if elapsed >= session.ttl_seconds and session.closed_state is None:
        await _close_session(session, "expired")

    rc = getattr(session.proc, "returncode", None)
    channel_row = await asyncio.to_thread(
        _probe_single_channel, provider, saved or {}, root, which, run, env
    )
    ready_now = bool(channel_row["status"]["ready"])

    if session.closed_state == "expired":
        state = "expired"
        msg = f"{spec['title']}网页授权会话已超时（{session.ttl_seconds} 秒），请重新发起授权。"
    elif session.closed_state == "cancelled":
        state = "failed"
        msg = f"{spec['title']}授权会话已取消。"
    elif rc == 0 or (not session.initial_ready and ready_now):
        await _close_session(session, "authorized")
        if not ready_now:
            channel_row = await asyncio.to_thread(
                _probe_single_channel, provider, saved or {}, root, which, run, env
            )
        state = "authorized" if channel_row["status"]["ready"] or rc == 0 else "failed"
        msg = (
            f"{spec['title']}已完成授权。"
            if state == "authorized"
            else f"{spec['title']}授权进程已结束，但尚未检测到有效订阅登录态。"
        )
    elif rc is not None and rc != 0:
        await _close_session(session, "failed")
        state = "failed"
        msg = f"{spec['title']}授权未通过或已中断，请重新发起授权。"
    else:
        state = "pending"
        msg = (
            "等待浏览器完成设备码授权…"
            if session.auth_url
            else "正在读取 CLI 授权链接与设备码…"
        )

    expires_in = max(0, int(session.ttl_seconds - (time.monotonic() - session.created_monotonic)))
    return {
        "provider": provider,
        "started": state in {"pending", "authorized"},
        "mode": "device_auth",
        "session_id": session.session_id,
        "state": state,
        "auth_url": session.auth_url,
        "device_code": session.device_code,
        "command": session.command,
        "expires_in": expires_in,
        "message": msg,
        "channel": channel_row,
    }


async def cancel_oauth_login(provider: str, session_id: str) -> dict:
    channel(provider)
    session = _SESSIONS_BY_ID.pop(session_id, None)
    if session is not None and session.provider == provider:
        await _close_session(session, "cancelled")
    return {"cancelled": True}
