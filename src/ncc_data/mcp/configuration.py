"""Project-scoped host registration. Generated files contain launch paths only."""

import json
import os
import re
import tempfile
import tomllib
from pathlib import Path

from ncc_shared.paths import config_path, legacy_config_path, project_root

SERVER_NAME = "ncc-postgresql"


def _retarget_generated_arguments(original, arguments):
    expected = tomllib.loads(original)
    expected["mcp_servers"][SERVER_NAME]["args"] = arguments
    lines = original.splitlines(keepends=True)
    active = False
    matches = []
    for index, line in enumerate(lines):
        if line.lstrip().startswith("["):
            active = bool(re.fullmatch(r"\[mcp_servers\.ncc-postgresql\]\s*(?:#.*)?", line.strip()))
        elif active and re.match(r"\s*args\s*=", line):
            matches.append(index)
    if len(matches) != 1:
        raise ValueError("现有Codex MCP入口不能安全迁移，原文件保留，请核查config/.env路径")
    lines[matches[0]] = "args = " + json.dumps(arguments, ensure_ascii=False) + "\n"
    candidate = "".join(lines)
    if tomllib.loads(candidate) != expected:
        raise ValueError("现有Codex MCP布局无法只更新真实入口，所有原文件保留，请核查config/.env路径")
    return candidate


def _write(path, content):
    if path.is_symlink():
        raise ValueError("MCP配置不能通过软链覆盖")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def install(host="both", root=None, profile="production", config=None):
    if host not in {"codex", "claude", "both"}:
        raise ValueError("不支持的MCP宿主")
    root = Path(root or project_root()).resolve()
    python = root / ".venv/bin/python"
    if not python.is_file():
        raise ValueError("请先在项目根执行uv sync安装数据运行环境")
    if profile not in {"production", "test"}:
        raise ValueError("MCP只能选择正式或唯一测试模式")
    arguments = [
        str(root / "scripts/ncc_data.py"),
        "--config",
        str(Path(config).resolve() if config else config_path(root)),
    ]
    if profile == "test":
        arguments.append("--test")
    arguments.append("mcp")
    entry = {"command": str(python), "args": arguments}
    legacy_arguments = [*arguments]
    legacy_arguments[2] = str(legacy_config_path(root))
    legacy_entry = {**entry, "args": legacy_arguments}
    result = []
    if host in {"claude", "both"}:
        path = root / ".mcp.json"
        if path.is_symlink():
            raise ValueError("MCP配置不能是软链")
        data = json.loads(path.read_text()) if path.exists() else {}
        if not isinstance(data, dict) or not isinstance(data.get("mcpServers", {}), dict):
            raise ValueError("现有MCP配置结构无效，原文件保留")
        servers = data.setdefault("mcpServers", {})
        if SERVER_NAME in servers and servers[SERVER_NAME] != entry and not (
            config is None and servers[SERVER_NAME] == legacy_entry
        ):
            raise ValueError("已有同名MCP配置不同，保留原文件；请先核查")
        servers[SERVER_NAME] = entry
        result.append((path, json.dumps(data, ensure_ascii=False, indent=2) + "\n"))
    if host in {"codex", "both"}:
        path = root / ".codex/config.toml"
        if path.is_symlink() or path.parent.is_symlink():
            raise ValueError("MCP配置目录不能是软链")
        original = path.read_text() if path.exists() else ""
        table = "[mcp_servers." + SERVER_NAME + "]"
        servers = tomllib.loads(original).get("mcp_servers", {}) if original else {}
        if not isinstance(servers, dict):
            raise ValueError("现有Codex MCP配置结构无效，原文件保留")
        current = servers.get(SERVER_NAME)
        if current is not None:
            if not isinstance(current, dict) or current.get("command") != entry["command"]:
                raise ValueError("已有同名Codex MCP配置不同，保留原文件；请先核查")
            if current.get("args") != arguments:
                if config is not None or current.get("args") != legacy_arguments:
                    raise ValueError("已有同名Codex MCP配置不同，保留原文件；请先核查")
                original = _retarget_generated_arguments(original, arguments)
            result.append((path, original))
        else:
            block = (
                table
                + "\ncommand = "
                + json.dumps(str(python))
                + "\nargs = "
                + json.dumps(arguments, ensure_ascii=False)
                + "\ncwd = "
                + json.dumps(str(root), ensure_ascii=False)
                + "\nstartup_timeout_sec = 20\ntool_timeout_sec = 30\nenabled = true\n"
            )
            result.append((path, original.rstrip() + "\n\n" + block if original else block))
    # Validate the complete candidate, including existing inline tables, before
    # touching either host file. Unsupported layouts remain entirely unchanged.
    for path, content in result:
        try:
            if path.suffix == ".toml":
                tomllib.loads(content)
            else:
                json.loads(content)
        except (ValueError, TypeError):
            raise ValueError("现有MCP配置布局无法安全合并，所有原文件保留，请先核查") from None
    # Both formats are prepared and checked before either file is changed.
    for path, _ in result:
        path.parent.mkdir(parents=True, exist_ok=True)
    for path, content in result:
        if not path.exists() or path.read_text() != content:
            _write(path, content)
    return {
        "server": SERVER_NAME,
        "profile": profile,
        "files": [str(path) for path, _ in result],
        "entry_contains_credentials": False,
        "database_connected": "not_checked",
    }
