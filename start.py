#!/usr/bin/env python3
"""Cross-platform launcher for the ncc-workflow console, API server, and background worker."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "apps" / "management-web"
WEB_DIST_INDEX = WEB_DIR / "dist" / "index.html"
IS_WINDOWS = os.name == "nt"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

_PRINT_LOCK = threading.Lock()


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except OSError:
                pass


def log(tag: str, message: str, *, err: bool = False) -> None:
    target = sys.stderr if err else sys.stdout
    with _PRINT_LOCK:
        print(f"[{tag}] {message}", file=target, flush=True)


def find_venv_python(root: Path = ROOT) -> Path | None:
    candidates = (
        [
            root / ".venv" / "Scripts" / "python.exe",
            root / ".venv" / "bin" / "python.exe",
            root / ".venv" / "bin" / "python",
        ]
        if IS_WINDOWS
        else [
            root / ".venv" / "bin" / "python",
            root / ".venv" / "bin" / "python3",
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def find_npm() -> str | None:
    if IS_WINDOWS:
        return shutil.which("npm.cmd") or shutil.which("npm")
    return shutil.which("npm")


def build_child_env(root: Path = ROOT) -> dict[str, str]:
    env = dict(os.environ)
    src_path = str(root / "src")
    existing_pp = env.get("PYTHONPATH", "")
    parts = [p for p in existing_pp.split(os.pathsep) if p]
    if src_path not in parts:
        env["PYTHONPATH"] = os.pathsep.join([src_path, *parts])
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def ensure_python_runtime(*, auto_install: bool) -> Path:
    venv_py = find_venv_python()
    if venv_py is not None:
        return venv_py

    if auto_install:
        uv_bin = shutil.which("uv")
        if uv_bin:
            log("ncc", "未检测到 .venv，正在执行 uv sync 安装 Python 运行依赖...")
            proc = subprocess.run(
                [uv_bin, "sync", "--extra", "dev", "--frozen"],
                cwd=ROOT,
                env=build_child_env(),
            )
            if proc.returncode != 0:
                raise SystemExit(proc.returncode)
            venv_py = find_venv_python()
            if venv_py is not None:
                return venv_py

    probe = subprocess.run(
        [sys.executable, "-c", "import fastapi, psycopg, sqlalchemy, uvicorn"],
        cwd=ROOT,
        env=build_child_env(),
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        return Path(sys.executable)

    hint = (
        "uv sync --extra dev --frozen"
        if shutil.which("uv")
        else "先安装 uv（https://docs.astral.sh/uv/），再在仓库根目录执行: uv sync --extra dev --frozen"
    )
    log("ncc", f"缺少数据库与后台运行环境（.venv 未就绪）。请执行：{hint}", err=True)
    log("ncc", "提示：若仅使用纯文件创作流，无需启动本后台服务，直接在宿主调用 /ncc 或运行 scripts/cli/ncc_state.py 即可。", err=True)
    raise SystemExit(1)


def ensure_frontend_dist(*, force_build: bool, auto_build: bool) -> None:
    if WEB_DIST_INDEX.is_file() and not force_build:
        return
    if not auto_build and not force_build:
        log(
            "ncc",
            "前端静态产物尚未构建（缺少 apps/management-web/dist/index.html），请移除 --no-build-web 或手动构建。",
            err=True,
        )
        raise SystemExit(1)

    npm_bin = find_npm()
    if not npm_bin:
        log(
            "ncc",
            "未检测到 npm（需要 Node.js >= 22.12），无法构建 apps/management-web。",
            err=True,
        )
        raise SystemExit(1)

    env = build_child_env()
    if not (WEB_DIR / "node_modules").is_dir():
        log("ncc", "未检测到前端依赖 node_modules，正在执行 npm ci...")
        ci_proc = subprocess.run([npm_bin, "--prefix", str(WEB_DIR), "ci"], cwd=ROOT, env=env)
        if ci_proc.returncode != 0:
            raise SystemExit(ci_proc.returncode)

    log("ncc", "正在构建前端工作台 apps/management-web...")
    build_proc = subprocess.run([npm_bin, "--prefix", str(WEB_DIR), "run", "build"], cwd=ROOT, env=env)
    if build_proc.returncode != 0:
        raise SystemExit(build_proc.returncode)


def cli_common_flags(args: argparse.Namespace) -> list[str]:
    flags: list[str] = []
    if args.config:
        flags.extend(["--config", str(args.config)])
    if args.database:
        flags.extend(["--profile", "production" if args.database == "ncc-pro" else "local"])
    elif args.test:
        flags.append("--test")
    elif args.production:
        flags.append("--production")
    elif args.profile:
        flags.extend(["--profile", args.profile])
    else:
        flags.extend(["--profile", "production"])
    return flags


def effective_profile(args: argparse.Namespace) -> str:
    if args.database:
        return "production" if args.database == "ncc-pro" else "local"
    if args.test:
        return "test"
    if args.production:
        return "production"
    if args.profile:
        return str(args.profile)
    return "production"


def target_summary(args: argparse.Namespace) -> str:
    profile = effective_profile(args)
    database = "ncc-pro" if profile == "production" else "ncc-dev"
    return f"{profile} / {database}"


def mode_hint_flags(args: argparse.Namespace) -> list[str]:
    flags: list[str] = []
    if args.config:
        flags.extend(["--config", str(args.config)])
    if args.database:
        flags.extend(["--database", args.database])
    elif args.test:
        flags.append("--test")
    elif args.production:
        flags.append("--production")
    elif args.profile:
        flags.extend(["--profile", args.profile])
    else:
        flags.extend(["--database", "ncc-pro"])
    return flags


def _quote_cli_arg(token: str) -> str:
    if not token or any(ch.isspace() or ch in {'"', "'"} for ch in token):
        if IS_WINDOWS:
            escaped = token.replace('"', '\\"')
            return f'"{escaped}"'
        return shlex.quote(token)
    return token


def migrate_command_hint(args: argparse.Namespace) -> str:
    prefix = ["python", "start.py"] if IS_WINDOWS else ["./start.py"]
    parts = [*prefix, *mode_hint_flags(args), "--migrate"]
    return " ".join(_quote_cli_arg(part) for part in parts)


def is_loopback_bind_host(host: str) -> bool:
    cleaned = (host or "").strip().lower()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1].strip()
    return cleaned in LOOPBACK_HOSTS


def emit_default_admin_notice(info: dict, host: str) -> None:
    if not info.get("default_admin_active"):
        return
    if is_loopback_bind_host(host):
        log(
            "ncc",
            "安全提醒：当前正在使用默认管理员账号（admin / 123456），"
            "第一次使用时请进入后台修改账号与密码（当前监听回环地址，仅作提醒）。",
        )
    else:
        log(
            "ncc",
            f"安全强制策略：当前监听非回环地址（{host}）且仍在使用默认管理员账号，"
            "首次登录后台将强制要求修改账号与密码！",
        )


def run_cli_step(venv_py: Path, sub_args: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    cmd = [str(venv_py), "-m", "ncc_data.cli", *sub_args]
    return subprocess.run(
        cmd,
        cwd=ROOT,
        env=build_child_env(),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=capture,
    )


def ensure_config_initialized(venv_py: Path, args: argparse.Namespace) -> Path:
    target_cfg = args.config.resolve() if args.config else (ROOT / "config" / ".env")
    if not target_cfg.is_file():
        init_args = ["init"]
        if args.config:
            init_args = ["--config", str(args.config), "init"]
        res = run_cli_step(venv_py, init_args, capture=True)
        if res.returncode != 0:
            log("ncc", (res.stderr or res.stdout or "初始化配置失败").strip(), err=True)
            raise SystemExit(res.returncode)
        if res.stdout.strip():
            log("ncc", res.stdout.strip())
    return target_cfg


def _summarize_error(raw: str) -> str:
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return "未知错误"
    for ln in reversed(lines):
        if not ln.startswith("(Background on this error"):
            return ln
    return lines[-1]


def run_doctor(
    venv_py: Path,
    common_flags: list[str],
    cfg_path: Path,
    *,
    args: argparse.Namespace | None = None,
    verbose: bool = False,
) -> dict:
    res = run_cli_step(venv_py, [*common_flags, "doctor"], capture=True)
    if res.returncode == 0:
        try:
            return json.loads(res.stdout)
        except json.JSONDecodeError:
            log("ncc", res.stdout.strip())
            return {}

    resolved_args = args if args is not None else build_parser().parse_args(common_flags)
    target = target_summary(resolved_args)
    detail = (res.stderr or res.stdout or "").strip()
    shown = detail if verbose else _summarize_error(detail)
    log("ncc", f"运行前自检未通过（目标：{target}）：{shown}", err=True)
    lowered = detail.lower()
    if "alembic_version" in lowered or "undefinedtable" in lowered or "does not exist" in lowered:
        cmd_hint = migrate_command_hint(resolved_args)
        log("ncc", f"提示：目标数据库（{target}）尚未初始化表结构，可显式执行：{cmd_hint}", err=True)
    elif (
        "数据库" in detail
        or "db_" in lowered
        or "database" in lowered
        or "password" in lowered
        or "operationalerror" in lowered
        or "connection" in lowered
    ):
        log("ncc", f"提示：请确认 PostgreSQL 已启动，并检查 {cfg_path} 中的连接配置。", err=True)
    raise SystemExit(res.returncode or 1)


def is_port_in_use(host: str, port: int) -> bool:
    check_host = "127.0.0.1" if host in {"0.0.0.0", ""} else host
    family = socket.AF_INET6 if ":" in check_host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((check_host, port)) == 0


def wait_http_ready(url: str, stop_event: threading.Event, *, open_browser: bool) -> None:
    deadline = time.monotonic() + 25.0
    while time.monotonic() < deadline and not stop_event.is_set():
        try:
            with urllib.request.urlopen(url + "/health/live", timeout=1.5) as resp:
                if resp.status == 200:
                    log("ncc", f"工作台已就绪：{url} （按 Ctrl+C 停止服务）")
                    if open_browser:
                        webbrowser.open(url)
                    return
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        stop_event.wait(0.3)


def spawn_managed(cmd: list[str], label: str) -> subprocess.Popen[str]:
    kwargs: dict = {
        "cwd": ROOT,
        "env": build_child_env(),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "bufsize": 1,
    }
    if IS_WINDOWS:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, **kwargs)

    def _pump() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            text = line.rstrip("\r\n")
            if text:
                log(label, text)

    threading.Thread(target=_pump, name=f"pump-{label}", daemon=True).start()
    return proc


def stop_processes(procs: list[tuple[str, subprocess.Popen[str]]]) -> None:
    for _, proc in procs:
        if proc.poll() is not None:
            continue
        try:
            if IS_WINDOWS:
                proc.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                os.killpg(proc.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError, ValueError, OSError):
            try:
                proc.terminate()
            except OSError:
                pass

    deadline = time.monotonic() + 5.0
    for _, proc in procs:
        remaining = max(0.1, deadline - time.monotonic())
        try:
            proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            try:
                if not IS_WINDOWS:
                    os.killpg(proc.pid, signal.SIGKILL)
                else:
                    proc.kill()
            except OSError:
                try:
                    proc.kill()
                except OSError:
                    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="start.py",
        description="ncc-workflow 跨平台启动器（支持 macOS 与 Windows：统一启动管理后台 API 与后台任务 Worker）",
    )
    parser.add_argument("--config", type=Path, help="可选的配置文件路径（默认读取 config/.env）")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--database",
        choices=["ncc-dev", "ncc-pro"],
        help="选择目标数据库（默认 ncc-pro；与 --test/--production/--profile 互斥）",
    )
    mode_group.add_argument("--test", action="store_true", help="使用测试模式（连接 ncc-dev 与测试端口 8788）")
    mode_group.add_argument("--production", action="store_true", help="显式指定线上正式模式（连接 ncc-pro；无模式参数时默认即此）")
    mode_group.add_argument(
        "--profile",
        choices=["local", "production", "test"],
        help="显式指定运行 profile（未指定任何模式参数时默认 production -> ncc-pro）",
    )
    role_group = parser.add_mutually_exclusive_group()
    role_group.add_argument("--web-only", action="store_true", help="仅启动 Web 与 API 服务（不启动后台 Worker）")
    role_group.add_argument("--worker-only", action="store_true", help="仅启动后台任务 Worker")
    parser.add_argument("--host", default="127.0.0.1", help="Web 服务监听地址（默认 127.0.0.1）")
    parser.add_argument("--port", type=int, help="Web 服务监听端口（默认读取 PUBLIC_ORIGIN 或 8761）")
    parser.add_argument("--migrate", action="store_true", help="启动前显式执行数据库迁移与系统定义种子安装")
    parser.add_argument("--create-user", metavar="USERNAME", help="交互式创建后台账号并退出（首个账号为系统管理员）")
    parser.add_argument("--build-web", action="store_true", help="启动前强制重新构建前端工作台")
    parser.add_argument("--no-build-web", action="store_true", help="缺少前端构建产物时不自动执行 npm build")
    parser.add_argument("--no-install", action="store_true", help="缺少 .venv 时不自动调用 uv sync")
    parser.add_argument("--check", "--doctor", dest="check_only", action="store_true", help="仅执行环境、前端产物与数据库 doctor 自检后退出")
    parser.add_argument("--open", dest="open_browser", action="store_true", help="Web 服务就绪后自动打开默认浏览器")
    parser.add_argument("-v", "--verbose", action="store_true", help="自检失败时打印完整堆栈信息")
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    args = build_parser().parse_args(argv)

    venv_py = ensure_python_runtime(auto_install=not args.no_install)
    cfg_path = ensure_config_initialized(venv_py, args)
    common_flags = cli_common_flags(args)

    if args.migrate:
        log("ncc", "正在执行数据库迁移与系统定义种子安装...")
        mig = run_cli_step(venv_py, [*common_flags, "migrate"])
        if mig.returncode != 0:
            return mig.returncode

    if args.create_user:
        res = run_cli_step(venv_py, [*common_flags, "create-user", args.create_user])
        return res.returncode

    if not args.worker_only:
        ensure_frontend_dist(force_build=args.build_web, auto_build=not args.no_build_web)

    info = run_doctor(venv_py, common_flags, cfg_path, args=args, verbose=args.verbose)
    profile = info.get("profile", effective_profile(args))
    dbname = info.get("database", "unknown")
    origin = str(info.get("origin") or "http://127.0.0.1:8761")
    parsed_origin = urlsplit(origin)
    effective_port = args.port or parsed_origin.port or (8788 if profile == "test" else 8761)
    display_host = "127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host
    display_url = f"{parsed_origin.scheme or 'http'}://{display_host}:{effective_port}"

    log(
        "ncc",
        f"自检通过：profile={profile}, database={dbname}, "
        f"frontend_built={info.get('frontend_built')}, model_configured={info.get('model_configured')}",
    )
    emit_default_admin_notice(info, args.host)

    if args.check_only:
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return 0

    if not args.worker_only and is_port_in_use(args.host, effective_port):
        log(
            "ncc",
            f"端口 {args.host}:{effective_port} 已被占用。请先停止已有服务，或使用 --port 指定其他端口。",
            err=True,
        )
        return 1

    procs: list[tuple[str, subprocess.Popen[str]]] = []
    stop_event = threading.Event()

    def _request_stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, _request_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _request_stop)

    try:
        if not args.worker_only:
            serve_cmd = [
                str(venv_py),
                "-m",
                "ncc_data.cli",
                *common_flags,
                "serve",
                "--host",
                args.host,
                "--port",
                str(effective_port),
            ]
            log("ncc", f"启动 Web 与 API 服务（监听 {args.host}:{effective_port}）...")
            procs.append(("web", spawn_managed(serve_cmd, "web")))
            threading.Thread(
                target=wait_http_ready,
                args=(display_url, stop_event),
                kwargs={"open_browser": args.open_browser},
                name="health-probe",
                daemon=True,
            ).start()

        if not args.web_only:
            worker_cmd = [str(venv_py), "-m", "ncc_data.cli", *common_flags, "worker"]
            log("ncc", "启动后台创作与索引 Worker...")
            procs.append(("worker", spawn_managed(worker_cmd, "worker")))

        exit_code = 0
        while not stop_event.is_set():
            for label, proc in procs:
                code = proc.poll()
                if code is not None:
                    log("ncc", f"{label} 进程已退出（退出码 {code}），正在关闭其余服务...", err=code != 0)
                    exit_code = code if code != 0 else exit_code
                    stop_event.set()
                    break
            stop_event.wait(0.4)
        return exit_code
    except KeyboardInterrupt:
        stop_event.set()
        return 0
    finally:
        stop_event.set()
        if procs:
            log("ncc", "正在安全停止服务...")
            stop_processes(procs)
            log("ncc", "已停止。")


if __name__ == "__main__":
    raise SystemExit(main())
