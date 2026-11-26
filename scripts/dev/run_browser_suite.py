#!/usr/bin/env python3
"""Unified browser regression suite runner using only the Python standard library."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_SUITES: tuple[tuple[str, str], ...] = (
    ("console", "tests/browser/console/run_browser.py"),
    ("access", "tests/browser/console/run_access_browser.py"),
    ("studio", "tests/browser/studio/run_studio_browser.py"),
    ("auto_adoption", "tests/browser/studio/run_auto_adoption_browser.py"),
    ("upgrade", "tests/browser/console/run_upgrade_browser.py"),
)
CLI_BRIDGE_SUITE: tuple[str, str] = ("cli_bridge", "tests/browser/bridge/run_cli_bridge.py")


def _python_executable() -> str:
    venv_py = ROOT / ".venv" / "bin" / "python"
    if venv_py.is_file() and Path(sys.executable).resolve() != venv_py.resolve():
        return str(venv_py)
    return sys.executable


def _matches_only(suite_name: str, rel_script: str, requested: set[str]) -> bool:
    script_path = Path(rel_script)
    aliases = {
        suite_name.lower(),
        script_path.stem.lower(),
        script_path.name.lower(),
        rel_script.lower(),
    }
    return bool(aliases & requested)


def _supports_output_flag(script_path: Path) -> bool:
    try:
        content = script_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return '"--output"' in content or "'--output'" in content


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="串行执行 NCC 管理后台全部 Playwright 浏览器验收套件并输出结构化 JSON 摘要。"
    )
    parser.add_argument(
        "--output",
        default="/tmp/ncc-browser-suite",
        help="输出与截图根目录（默认：/tmp/ncc-browser-suite）",
    )
    parser.add_argument(
        "--only",
        default="",
        help="仅运行指定套件，逗号分隔（支持套件短名如 upgrade,studio 或脚本名如 run_upgrade_browser）",
    )
    parser.add_argument(
        "--include-cli-bridge",
        action="store_true",
        help="追加运行 tests/browser/bridge/run_cli_bridge.py CLI 工作副本往返验收",
    )
    parser.add_argument(
        "--config",
        default="",
        help="可选透传给各套件的隔离配置文件路径",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_root = Path(args.output).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    candidates = list(DEFAULT_SUITES)
    requested = {item.strip().lower() for item in args.only.split(",") if item.strip()}
    if args.include_cli_bridge or (
        requested and _matches_only(CLI_BRIDGE_SUITE[0], CLI_BRIDGE_SUITE[1], requested)
    ):
        candidates.append(CLI_BRIDGE_SUITE)

    if requested:
        selected = [item for item in candidates if _matches_only(item[0], item[1], requested)]
        if not selected:
            available = [name for name, _ in [*DEFAULT_SUITES, CLI_BRIDGE_SUITE]]
            summary = {
                "ok": False,
                "error": f"未匹配到任何浏览器套件：{sorted(requested)}，可选：{available}",
                "output_dir": str(output_root),
                "suites": [],
            }
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 2
    else:
        selected = candidates

    py_bin = _python_executable()
    suite_results: list[dict] = []
    started_all = time.monotonic()

    for name, rel_script in selected:
        script_path = ROOT / rel_script
        suite_out = output_root / name
        suite_out.mkdir(parents=True, exist_ok=True)

        cmd = [py_bin, str(script_path)]
        if args.config:
            cmd.extend(["--config", str(Path(args.config).expanduser().resolve())])
        if _supports_output_flag(script_path):
            cmd.extend(["--output", str(suite_out)])

        t0 = time.monotonic()
        completed = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        elapsed = round(time.monotonic() - t0, 2)
        ok = completed.returncode == 0
        status = "passed" if ok else "failed"

        (suite_out / "stdout.log").write_text(completed.stdout or "", encoding="utf-8")
        (suite_out / "stderr.log").write_text(completed.stderr or "", encoding="utf-8")

        parsed_stdout = None
        stdout_lines = [ln.strip() for ln in (completed.stdout or "").splitlines() if ln.strip()]
        if stdout_lines:
            try:
                parsed_stdout = json.loads("\n".join(stdout_lines))
            except ValueError:
                try:
                    parsed_stdout = json.loads(stdout_lines[-1])
                except ValueError:
                    parsed_stdout = None

        record = {
            "name": name,
            "script": rel_script,
            "status": status,
            "exit_code": completed.returncode,
            "duration_seconds": elapsed,
            "output_dir": str(suite_out),
        }
        if parsed_stdout is not None:
            record["report"] = parsed_stdout
        if not ok:
            tail = "\n".join((completed.stderr or completed.stdout or "").splitlines()[-20:])
            record["failure_tail"] = tail
            print(
                f"[FAIL] {name} ({rel_script}) exited {completed.returncode} in {elapsed}s:\n{tail}",
                file=sys.stderr,
            )
        suite_results.append(record)

    total_elapsed = round(time.monotonic() - started_all, 2)
    passed_count = sum(1 for r in suite_results if r["status"] == "passed")
    failed_count = len(suite_results) - passed_count
    all_ok = failed_count == 0

    summary = {
        "ok": all_ok,
        "output_dir": str(output_root),
        "total": len(suite_results),
        "passed": passed_count,
        "failed": failed_count,
        "duration_seconds": total_elapsed,
        "suites": suite_results,
    }
    (output_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
