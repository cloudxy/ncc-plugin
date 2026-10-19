import os
import stat
from pathlib import Path

import pytest

from ncc_data.cli.backup import pg_service
from ncc_data.persistence.database import connection_parameters
from ncc_data.runtime.settings import Settings
from ncc_shared.configuration import configuration, initialize, read_dotenv
from ncc_shared.database import DatabasePair, configured_url


def test_file_is_authoritative_and_does_not_mutate_environment(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    password = "p@:/#中文$()secret"
    values = {
        "NCC_DB_HOST": "localhost",
        "NCC_DB_NAME": "正式小说",
        "NCC_DB_USER": "author",
        "NCC_DB_PASSWORD": password,
        "NCC_DB_PORT": "5544",
        "NCC_MODEL_URL": "https://model.example",
    }
    assert initialize(path, values=values)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    monkeypatch.setenv("NCC_DATABASE_URL", "postgresql://wrong/wrong")
    monkeypatch.setenv("NCC_MODEL_URL", "https://wrong.example")
    monkeypatch.chdir(tmp_path / "..")
    settings = Settings.load(path)
    params = connection_parameters(settings.database_url)
    assert params["dbname"] == "正式小说" and params["password"] == password
    assert params["port"] == 5544
    assert settings.model_url == "https://model.example"
    assert os.environ["NCC_MODEL_URL"] == "https://wrong.example"
    assert password not in repr(settings)
    assert not initialize(path, values={"NCC_DB_NAME": "changed"})
    assert read_dotenv(path) == values
    test = Settings.load(path, "test")
    assert connection_parameters(test.database_url)["dbname"] == "正式小说-test"
    assert test.public_origin == "http://127.0.0.1:8788"


def test_explicit_missing_and_invalid_files_do_not_fallback(tmp_path):
    with pytest.raises(ValueError, match="不存在"):
        configuration(tmp_path / "missing", {"NCC_DATABASE_URL": "postgresql://x/formal"})
    with pytest.raises(ValueError, match="不存在"):
        configuration(environ={"NCC_CONFIG_FILE": str(tmp_path / "missing")})
    for content in ("NCC_A=1\nNCC_A=2", 'NCC_A="unclosed', "not a setting"):
        path = tmp_path / ".env"
        path.write_text(content)
        with pytest.raises(ValueError):
            read_dotenv(path)
    empty = tmp_path / "no-partial"
    with pytest.raises(ValueError):
        initialize(empty, values={"BAD": "x"})
    assert not empty.exists()


@pytest.mark.parametrize("host", ["localhost", "::1", "/tmp/postgres"])
def test_exactly_one_sibling_preserves_all_connection_parameters(host):
    url = configured_url(
        {
            "NCC_DB_HOST": host,
            "NCC_DB_PORT": "5533",
            "NCC_DB_NAME": "创作",
            "NCC_DB_USER": "u",
            "NCC_DB_PASSWORD": "p@#",
        }
    )
    pair = DatabasePair(url)
    prod, test = connection_parameters(url), connection_parameters(pair.test_url)
    assert pair.production_url == url and pair.select() == url
    assert prod.pop("dbname") == "创作"
    assert test.pop("dbname") == "创作-test"
    assert prod == test
    pair.require_test(pair.test_url)
    for rejected in (url, url.replace("5533", "5534"), pair.test_url + "x"):
        with pytest.raises(ValueError):
            pair.require_test(rejected)


@pytest.mark.parametrize("key", ["dbname", "database", "DBNAME", "%64bname"])
def test_query_cannot_redirect_test_back_to_production(key):
    url = "postgresql+psycopg://u:p@localhost/formal?" + key + "=formal"
    with pytest.raises(ValueError):
        DatabasePair(url)


def test_maintenance_keeps_tls_options_and_private_secrets():
    url = "postgresql+psycopg://author:private%40value@db.example/formal?sslmode=verify-full&sslrootcert=%2Fprivate%2Fca.pem&connect_timeout=8&options=-c%20statement_timeout%3D3000"
    pair = DatabasePair(url)
    parameters = connection_parameters(pair.test_url)
    assert parameters["dbname"] == "formal-test"
    assert parameters["sslmode"] == "verify-full"
    assert parameters["sslrootcert"] == "/private/ca.pem"
    with pg_service(parameters) as env:
        file = Path(env["PGSERVICEFILE"])
        assert stat.S_IMODE(file.stat().st_mode) == 0o600
        content = file.read_text()
        assert "verify-full" in content and "statement_timeout=3000" in content
        assert "private@value" not in content and "password" not in content
        assert env["PGPASSWORD"] == "private@value"
    assert not file.exists()


def test_rejects_duplicate_connection_sources_and_unsafe_origin(tmp_path):
    with pytest.raises(ValueError):
        configured_url({"NCC_DATABASE_URL": "postgresql://u/db", "NCC_DB_NAME": "other"})
    initialize(
        tmp_path / ".env",
        values={"NCC_DATABASE_URL": "postgresql://u/db", "NCC_PUBLIC_ORIGIN": "ftp://localhost"},
    )
    with pytest.raises(ValueError):
        Settings.load(tmp_path / ".env")
