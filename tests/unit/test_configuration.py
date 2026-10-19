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


def test_dynaconf_manages_defaults_environment_and_private_overlay(tmp_path, monkeypatch):
    from dynaconf import Dynaconf

    from ncc_shared import configuration as module

    defaults = tmp_path / "config/default/settings.toml"
    defaults.parent.mkdir(parents=True)
    defaults.write_text((Path(__file__).resolve().parents[2] / "config/default/settings.toml").read_text())
    environment = tmp_path / "config/local/settings.toml"
    environment.parent.mkdir()
    environment.write_text("SESSION_HOURS=10\nMODEL_TIMEOUT=240\n")
    private = tmp_path / ".env"
    initialize(private, values={"NCC_SESSION_HOURS": "12"})
    monkeypatch.setattr(module, "project_root", lambda: tmp_path)
    manager = module.load_settings(private, environ={"NCC_SESSION_HOURS": "6"})
    assert isinstance(manager, Dynaconf)
    assert manager.SESSION_HOURS == 12 and manager.MODEL_TIMEOUT == 240
    private.write_text('NCC_SESSION_HOURS="999"')
    with pytest.raises(ValueError, match="类型或范围"):
        module.load_settings(private, environ={})


@pytest.mark.parametrize("use_url", [True, False])
def test_environment_file_chooses_a_complete_database_source(tmp_path, monkeypatch, use_url):
    from ncc_shared import configuration as module

    defaults = tmp_path / "config/default/settings.toml"
    defaults.parent.mkdir(parents=True)
    defaults.write_text((Path(__file__).resolve().parents[2] / "config/default/settings.toml").read_text())
    environment = tmp_path / "config/local/settings.toml"
    environment.parent.mkdir()
    path = tmp_path / ".env"
    path.write_text('NCC_ENV="local"')
    monkeypatch.setattr(module, "project_root", lambda: tmp_path)
    if use_url:
        environment.write_text('DATABASE_URL="postgresql://u:synthetic@localhost/from_environment"')
        fallback = {"NCC_DB_HOST": "other", "NCC_DB_NAME": "wrong", "NCC_DB_USER": "wrong"}
    else:
        environment.write_text('DB_HOST="localhost"\nDB_NAME="from_environment"\nDB_USER="u"')
        fallback = {"NCC_DATABASE_URL": "postgresql://wrong/wrong"}
    result = configured_url(module.configuration(path, fallback))
    assert connection_parameters(result)["dbname"] == "from_environment"


@pytest.mark.parametrize(
    "value", ["p\x01word", "中文\x00", r"\u4e2d", "${HOME}", "@format {env[HOME]}", 'x\\y\n\t"']
)
def test_initializer_and_legacy_json_escapes_preserve_exact_values(tmp_path, value):
    path = tmp_path / ".env"
    initialize(path, values={"NCC_DB_PASSWORD": value})
    assert read_dotenv(path)["NCC_DB_PASSWORD"] == value


def test_old_unicode_escaped_json_configuration_still_decodes(tmp_path):
    path = tmp_path / ".env"
    path.write_text(r'NCC_DB_PASSWORD="\u4e2d\u6587"')
    assert read_dotenv(path)["NCC_DB_PASSWORD"] == "中文"


@pytest.mark.parametrize(
    "literal, expected", [(r'"\x73\x79"', "sy"), (r'"\U0001f600"', "😀"), (r"'\u4e2d'", "中")]
)
def test_legacy_python_string_escapes_are_preserved(tmp_path, literal, expected):
    path = tmp_path / ".env"
    path.write_text("NCC_DB_PASSWORD=" + literal)
    assert read_dotenv(path)["NCC_DB_PASSWORD"] == expected


def local_project(tmp_path, monkeypatch):
    from ncc_shared import configuration as module
    from ncc_shared import paths

    defaults = tmp_path / "config/default/settings.toml"
    defaults.parent.mkdir(parents=True)
    defaults.write_bytes((Path(__file__).resolve().parents[2] / "config/default/settings.toml").read_bytes())
    monkeypatch.setattr(paths, "project_root", lambda: tmp_path)
    monkeypatch.setattr(module, "project_root", lambda: tmp_path)
    return module


def test_default_init_migrates_legacy_bytes_once_and_never_falls_back(tmp_path, monkeypatch):
    module = local_project(tmp_path, monkeypatch)
    old = tmp_path / ".env"
    raw = b'\xef\xbb\xbf# retained comment\r\nNCC_DATABASE_URL="postgresql://u:synthetic@localhost/formal"\r\n'
    old.write_bytes(raw)
    with pytest.raises(ValueError, match="ncc-data init"):
        module.load_settings(environ={})
    assert module.initialize(values={"NCC_DATABASE_URL": "postgresql://wrong/ignored"})
    target = tmp_path / "config/.env"
    assert target.read_bytes() == raw and not old.exists()
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert configured_url(module.configuration(environ={})).endswith("/formal")
    assert not module.initialize(values={"NCC_DATABASE_URL": "changed"})
    assert target.read_bytes() == raw


def test_two_private_config_files_are_an_explicit_conflict(tmp_path, monkeypatch):
    module = local_project(tmp_path, monkeypatch)
    old, target = tmp_path / ".env", tmp_path / "config/.env"
    target.parent.mkdir(exist_ok=True)
    old.write_bytes(b'NCC_DB_NAME="legacy"')
    target.write_bytes(b'NCC_DB_NAME="current"')
    before = old.read_bytes(), target.read_bytes()
    for operation in (
        module.initialize,
        lambda: module.initialize(target),
        lambda: module.load_settings(environ={}),
        lambda: module.load_settings(target, environ={}),
    ):
        with pytest.raises(ValueError, match="同时存在"):
            operation()
        assert before == (old.read_bytes(), target.read_bytes())


def test_new_project_template_and_private_file_belong_to_config(tmp_path, monkeypatch):
    module = local_project(tmp_path, monkeypatch)
    template_path = tmp_path / "config/.env.example"
    template_path.parent.mkdir(exist_ok=True)
    template_path.write_text('NCC_ENV="local"\nNCC_DB_NAME=""\n')
    assert module.initialize(values=module.template())
    assert (tmp_path / "config/.env").is_file()
    assert not (tmp_path / ".env").exists()


def test_migration_refuses_a_destination_created_concurrently(tmp_path, monkeypatch):
    module = local_project(tmp_path, monkeypatch)
    old, target = tmp_path / ".env", tmp_path / "config/.env"
    old.write_bytes(b'NCC_DB_NAME="legacy"')

    actual_move = module._move_no_replace

    def concurrent_target(source, destination):
        Path(destination).write_bytes(b'NCC_DB_NAME="concurrent"')
        actual_move(source, destination)

    monkeypatch.setattr(module, "_move_no_replace", concurrent_target)
    with pytest.raises(FileExistsError):
        module.initialize()
    assert old.read_bytes() == b'NCC_DB_NAME="legacy"'
    assert target.read_bytes() == b'NCC_DB_NAME="concurrent"'


def test_legacy_symlink_is_not_moved_or_modified(tmp_path, monkeypatch):
    module = local_project(tmp_path, monkeypatch)
    external = tmp_path / "external"
    external.write_bytes(b'NCC_DB_NAME="external"')
    old = tmp_path / ".env"
    old.symlink_to(external)
    with pytest.raises(ValueError, match="普通文件"):
        module.initialize()
    assert old.is_symlink() and external.read_bytes() == b'NCC_DB_NAME="external"'
    assert not (tmp_path / "config/.env").exists()


@pytest.mark.parametrize("replaced", ["source", "target", "recreated_source"])
def test_concurrent_editor_replacement_is_never_deleted_by_migration(tmp_path, monkeypatch, replaced):
    module = local_project(tmp_path, monkeypatch)
    old, target = tmp_path / ".env", tmp_path / "config/.env"
    old.write_bytes(b'NCC_DB_NAME="original"')
    editor = tmp_path / "editor-save"
    editor.write_bytes(b'NCC_DB_NAME="editor"')
    actual_move = module._move_no_replace

    def edit_during_move(source, destination):
        if replaced == "source":
            editor.replace(source)
        actual_move(source, destination)
        if replaced == "target":
            editor.replace(destination)
        elif replaced == "recreated_source":
            editor.replace(source)

    monkeypatch.setattr(module, "_move_no_replace", edit_during_move)
    with pytest.raises(ValueError, match="发生变化"):
        module.initialize()
    if replaced == "recreated_source":
        assert old.read_bytes() == b'NCC_DB_NAME="editor"'
        assert target.read_bytes() == b'NCC_DB_NAME="original"'
    else:
        assert target.read_bytes() == b'NCC_DB_NAME="editor"'
    # Migration has no cleanup unlink that could remove a concurrently saved file.
