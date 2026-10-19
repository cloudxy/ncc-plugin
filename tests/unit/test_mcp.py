import json
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ncc_data.mcp.configuration import install
from ncc_data.mcp.server import create_server
from ncc_shared.configuration import initialize


def root_fixture(tmp_path):
    (tmp_path / ".venv/bin").mkdir(parents=True)
    (tmp_path / ".venv/bin/python").touch()
    return tmp_path


def test_host_registration_is_repeat_safe_and_never_embeds_credentials(tmp_path):
    root_fixture(tmp_path)
    result = install(root=tmp_path)
    assert result["entry_contains_credentials"] is False
    codex = tmp_path / ".codex/config.toml"
    parsed = tomllib.loads(codex.read_text())["mcp_servers"]["ncc-postgresql"]
    assert parsed["args"][-1] == "mcp" and "env" not in parsed
    before = codex.read_bytes(), (tmp_path / ".mcp.json").read_bytes()
    install(root=tmp_path)
    assert before == (codex.read_bytes(), (tmp_path / ".mcp.json").read_bytes())


def test_inline_table_config_is_never_corrupted_or_partially_installed(tmp_path):
    root_fixture(tmp_path)
    codex = tmp_path / ".codex/config.toml"
    codex.parent.mkdir()
    original = 'mcp_servers = { other = { command = "python", args = ["other.py"] } }'
    codex.write_text(original)
    with pytest.raises(ValueError, match="所有原文件保留"):
        install(root=tmp_path)
    assert codex.read_text() == original and not (tmp_path / ".mcp.json").exists()
    assert tomllib.loads(codex.read_text())["mcp_servers"]["other"]


@pytest.mark.parametrize("original", ['mcp_servers = "invalid"', '[mcp_servers]\nncc-postgresql = "invalid"'])
def test_invalid_server_shape_preserves_all_existing_host_files(tmp_path, original):
    root_fixture(tmp_path)
    codex = tmp_path / ".codex/config.toml"
    codex.parent.mkdir()
    codex.write_text(original)
    claude = tmp_path / ".mcp.json"
    claude.write_text('{"mcpServers":{"other":{"command":"other"}}}')
    before = claude.read_bytes()
    with pytest.raises(ValueError):
        install(root=tmp_path)
    assert codex.read_text() == original and claude.read_bytes() == before


@pytest.mark.parametrize("test_profile", [False, True])
def test_generated_legacy_config_path_is_retargeted_without_touching_other_settings(tmp_path, test_profile):
    root_fixture(tmp_path)
    old_args = [str(tmp_path / "scripts/ncc_data.py"), "--config", str(tmp_path / ".env")]
    if test_profile:
        old_args.append("--test")
    old_args.append("mcp")
    entry = {"command": str(tmp_path / ".venv/bin/python"), "args": old_args}
    claude = tmp_path / ".mcp.json"
    claude.write_text(json.dumps({"mcpServers": {"other": {"command": "other"}, "ncc-postgresql": entry}}))
    codex = tmp_path / ".codex/config.toml"
    codex.parent.mkdir()
    prefix = '[mcp_servers.other]\ncommand = "other"\n\n'
    codex.write_text(
        prefix + '[mcp_servers.ncc-postgresql]\ncommand = ' + json.dumps(entry["command"])
        + '\nargs = ' + json.dumps(old_args) + '\nenabled = false\ntool_timeout_sec = 42\n'
    )
    install(root=tmp_path, profile="test" if test_profile else "production")
    parsed = tomllib.loads(codex.read_text())["mcp_servers"]
    new_args = parsed["ncc-postgresql"]["args"]
    assert new_args[2] == str(tmp_path / "config/.env")
    assert parsed["other"] == {"command": "other"}
    assert parsed["ncc-postgresql"]["enabled"] is False
    assert parsed["ncc-postgresql"]["tool_timeout_sec"] == 42
    assert codex.read_text().startswith(prefix)
    assert json.loads(claude.read_text())["mcpServers"]["ncc-postgresql"]["args"] == new_args
    before = codex.read_bytes(), claude.read_bytes()
    install(root=tmp_path, profile="test" if test_profile else "production")
    assert before == (codex.read_bytes(), claude.read_bytes())


async def test_only_readonly_tools_are_registered_and_use_shared_read_adapter():
    access = SimpleNamespace(read=AsyncMock(return_value={"id": "entity"}), close=AsyncMock())
    server = create_server(access=access)
    tools = await server.list_tools()
    assert len(tools) == 9 and all(tool.annotations.readOnlyHint for tool in tools)
    assert not any(
        word in tool.name for tool in tools for word in ("update", "apply", "create", "delete", "execute_sql")
    )
    await server.call_tool("get_entity", {"scope_id": "scope", "entity_id": "entity"})
    access.read.assert_awaited_once_with("entity", scope_id="scope", entity_id="entity", query=None)


def test_toml_multiline_string_cannot_masquerade_as_server_table(tmp_path):
    root_fixture(tmp_path)
    args = [str(tmp_path / "scripts/ncc_data.py"), "--config", str(tmp_path / ".env"), "mcp"]
    original = (
        "notes = '''\n[mcp_servers.ncc-postgresql]\nargs = [\"synthetic note\"]\n'''\n"
        + '[mcp_servers."ncc-postgresql"]\ncommand = '
        + json.dumps(str(tmp_path / ".venv/bin/python"))
        + "\nargs = " + json.dumps(args) + "\n"
    )
    codex = tmp_path / ".codex/config.toml"
    codex.parent.mkdir()
    codex.write_text(original)
    claude = tmp_path / ".mcp.json"
    claude.write_text('{"mcpServers":{"other":{"command":"other"}}}')
    before = codex.read_bytes(), claude.read_bytes()
    assert "synthetic note" in tomllib.loads(original)["notes"]
    with pytest.raises(ValueError, match="所有原文件保留"):
        install(root=tmp_path)
    assert before == (codex.read_bytes(), claude.read_bytes())


async def test_real_stdio_initialize_discover_and_unconfigured_status(tmp_path):
    root = Path(__file__).resolve().parents[2]
    config = tmp_path / ".env"
    initialize(config, values={"NCC_DB_NAME": "", "NCC_API_TOKEN": ""})
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(root / "scripts/ncc_data.py"), "--config", str(config), "mcp"],
        cwd=str(root),
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        assert len(tools.tools) == 9
        response = await session.call_tool("postgresql_status", {})
        assert response.structuredContent["configured"] is False
        assert response.structuredContent["connected"] is False
        assert not response.isError
        failure = await session.call_tool("get_scope", {"scope_id": "synthetic"})
        assert failure.isError
        assert "password" not in json.dumps(failure.model_dump(), ensure_ascii=False).lower()
