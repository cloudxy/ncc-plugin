import ast
import io
from pathlib import Path
from unittest.mock import MagicMock, Mock

import httpx
import pytest

from ncc_data.api import create_app
from ncc_data.cli.main import main
from ncc_data.runtime.settings import Settings
from ncc_shared.http import APIClient


def client(profile="test"):
    return APIClient(
        {"NCC_API_URL": "http://127.0.0.1:8788", "NCC_API_TOKEN": "never-leak", "NCC_API_PROFILE": profile}
    )


def test_wrong_service_gets_no_credentials_and_no_mutation():
    api = client()
    api.opener = MagicMock()
    api.opener.open.return_value.__enter__.return_value = io.BytesIO(b'{"profile":"production"}')
    with pytest.raises(ValueError, match="不一致"):
        api.request("POST", "/scopes", {"name": "must-not-write"})
    assert api.opener.open.call_count == 1
    request = api.opener.open.call_args.args[0]
    assert request.full_url.endswith("/health/live") and not request.has_header("Authorization")


def test_correct_service_checks_once_and_each_request_has_profile():
    api = client()
    responses = [io.BytesIO(b'{"profile":"test"}'), io.BytesIO(b"{}"), io.BytesIO(b"{}")]
    api.opener = MagicMock()
    api.opener.open.return_value.__enter__.side_effect = responses
    api.request("POST", "/scopes", {})
    api.request("GET", "/scopes")
    assert api.opener.open.call_count == 3
    for call in api.opener.open.call_args_list[1:]:
        assert call.args[0].get_header("X-ncc-profile") == "test"


async def test_server_fences_wrong_profile_before_auth_or_database():
    factory = Mock(side_effect=AssertionError("database must never be touched"))
    app = create_app(Settings(database_url="postgresql://unused/unused", profile="production"), factory)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://local") as api:
        response = await api.post("/api/v1/scopes", json={}, headers={"x-ncc-profile": "test"})
        assert response.status_code == 409
        response = await api.get("/health/live")
        assert response.json()["profile"] == "production"
    factory.assert_not_called()


def test_cli_request_uses_selected_file_and_test_origin(tmp_path, monkeypatch, capsys):
    path = tmp_path / ".env"
    path.write_text('NCC_API_TOKEN="selected-token"\nNCC_TEST_PUBLIC_ORIGIN="http://127.0.0.1:8999"')
    constructor = Mock()
    constructor.return_value.request.return_value = {"ok": True}
    import importlib

    monkeypatch.setattr(importlib.import_module("ncc_data.cli.main"), "APIClient", constructor)
    main(["--config", str(path), "--test", "request", "GET", "/scopes"])
    values = constructor.call_args.args[0]
    assert values["NCC_API_TOKEN"] == "selected-token" and values["NCC_API_URL"].endswith(":8999")
    assert values["NCC_API_PROFILE"] == "test"


def test_shared_and_domain_dependencies_stay_owned():
    root = Path(__file__).resolve().parents[2]
    for path in (root / "src/ncc_shared").rglob("*.py"):
        tree = ast.parse(path.read_text())
        names = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module]
        names += [alias.name for n in ast.walk(tree) if isinstance(n, ast.Import) for alias in n.names]
        assert not any(
            n.startswith(("ncc_data", "sqlalchemy", "fastapi", "pydantic", "httpx")) for n in names
        ), path
    for path in (root / "src/ncc_data/domain").glob("*.py"):
        assert not any(
            n.module
            and n.module.startswith(
                ("ncc_data.api", "ncc_data.creation", "ncc_data.persistence", "ncc_data.application")
            )
            for n in ast.walk(ast.parse(path.read_text()))
            if isinstance(n, ast.ImportFrom)
        ), path


@pytest.mark.parametrize(
    "token", ["secret\npart", "secret\rpart", "secret\x00part", "secret 中文", "secret part"]
)
def test_invalid_header_credential_never_reaches_transport_or_errors(token):
    with pytest.raises(ValueError) as error:
        APIClient({"NCC_API_TOKEN": token})
    assert token not in str(error.value)
