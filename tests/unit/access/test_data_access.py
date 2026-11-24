from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from ncc_data.application import access as module
from ncc_data.runtime.settings import Settings
from ncc_shared.errors import DomainError
from ncc_shared.serialization import digest


def fixture(monkeypatch, token="synthetic-token"):
    db = MagicMock()
    db.__aenter__.return_value = db
    db.execute = AsyncMock()
    db.scalar = AsyncMock()
    actor = SimpleNamespace(id="author")
    service = MagicMock(actor=actor)
    for name in (
        "scopes",
        "scope_info",
        "entities",
        "entity",
        "facts",
        "history",
        "revision",
        "create_change",
        "adopt",
        "change",
    ):
        setattr(service, name, AsyncMock())
    auth = AsyncMock(return_value=(actor, SimpleNamespace(kind="cli")))
    monkeypatch.setattr(module, "authenticate", auth)
    monkeypatch.setattr(module, "authorize", AsyncMock())
    monkeypatch.setattr(module, "Service", Mock(return_value=service))
    client = module.DataAccess(
        Settings(database_url="postgresql://unused/unused"), token, Mock(return_value=db)
    )
    return client, db, service, auth


async def test_reads_start_readonly_and_recheck_authentication(monkeypatch):
    client, db, service, auth = fixture(monkeypatch)
    service.scopes.return_value = [{"id": "allowed"}]
    assert await client.read("scopes") == [{"id": "allowed"}]
    assert str(db.execute.call_args_list[0].args[0]) == "SET TRANSACTION READ ONLY"
    await client.read("scopes")
    assert auth.await_count == 2
    auth.side_effect = DomainError("session_expired", "revoked", 401)
    with pytest.raises(DomainError, match="revoked"):
        await client.read("scopes")
    assert service.scopes.await_count == 2


@pytest.mark.parametrize("operation, query", [("apply", {}), ("sql", {}), ("search", {"limit": 201})])
async def test_invalid_read_cannot_open_a_write_or_unbounded_query(monkeypatch, operation, query):
    client, db, _, auth = fixture(monkeypatch)
    with pytest.raises((DomainError, ValueError)):
        await client.read(operation, scope_id="scope", query=query)
    db.execute.assert_not_called()
    auth.assert_not_called()


async def test_browser_credential_and_absent_token_cannot_use_direct_data(monkeypatch):
    client, db, _, auth = fixture(monkeypatch)
    auth.return_value = (SimpleNamespace(id="author"), SimpleNamespace(kind="browser"))
    with pytest.raises(DomainError) as error:
        await client.read("scopes")
    assert error.value.code == "credential_kind"
    client.token = ""
    previous = db.execute.call_count
    with pytest.raises(DomainError) as error:
        await client.read("scopes")
    assert error.value.code == "credential_required" and db.execute.call_count == previous


def change():
    return {
        "request_id": "fixture-request-1",
        "title": "合成更新",
        "base_version": 3,
        "operations": [{"op": "update", "entity_id": "e", "expected": "previous-revision", "name": "new"}],
    }


async def test_writes_use_existing_adoption_and_preserve_expected_version(monkeypatch):
    client, db, service, _ = fixture(monkeypatch)
    receipt = SimpleNamespace(result={})
    db.scalar.side_effect = [None, receipt]
    service.create_change.return_value = {"id": "change", "operations": [{"entity_id": "e"}]}
    service.adopt.return_value = {"change_id": "change", "version": 4}
    result = await client.apply("scope", change())
    assert not any("READ ONLY" in str(call.args[0]) for call in db.execute.call_args_list)
    assert service.create_change.call_args.args[1].operations[0].expected == "previous-revision"
    service.adopt.assert_awaited_once_with("scope", "change", "fixture-request-1")
    assert receipt.result == result and result["version"] == 4


async def test_idempotent_retry_rechecks_permission_and_does_not_recreate_change(monkeypatch):
    client, db, service, auth = fixture(monkeypatch)
    value = change()
    original = {k: v for k, v in value.items() if k != "request_id"}
    from ncc_data.domain.access import DirectChange

    expected = DirectChange.model_validate(value).model_dump(mode="json", exclude={"request_id"})
    assert original["base_version"] == expected["base_version"]
    previous = {"change_id": "old", "version": 4, "direct_input_hash": digest(expected)}
    db.scalar.return_value = SimpleNamespace(result=previous)
    assert await client.apply("scope", value) == previous
    service.create_change.assert_not_called()
    service.change.assert_awaited_once_with("scope", "old", "adopt")
    assert auth.await_count == 1 and module.authorize.await_count == 2
    value["operations"][0]["name"] = "different"
    with pytest.raises(DomainError) as error:
        await client.apply("scope", value)
    assert error.value.code == "idempotency_reuse"


@pytest.mark.parametrize(
    "action, expected_operation",
    [("create", "create"), ("edit", "update"), ("update", "update"), ("retire", "retire")],
)
def test_real_cli_parser_routes_full_data_mutations_without_http(
    tmp_path, monkeypatch, capsys, action, expected_operation
):
    from ncc_data.cli import data as cli
    from ncc_data.cli.main import main

    content = tmp_path / "fields.json"
    content.write_text('{"name":"synthetic","text":"new"}')
    access = SimpleNamespace(apply=AsyncMock(return_value={"version": 4}), close=AsyncMock())
    constructor = Mock(return_value=access)
    load = Mock(
        return_value=Settings(
            database_url="postgresql://unused/unused", api_token="synthetic-token", profile="test"
        )
    )
    monkeypatch.setattr(cli, "DataAccess", constructor)
    monkeypatch.setattr(cli.Settings, "load", load)
    argv = ["--test", "data", action, "--scope", "scope", "--base-version", "3", "--request-id", "request-1"]
    if action == "create":
        argv += ["--kind", "character", "--file", str(content)]
    else:
        argv += ["--entity", "entity", "--expected", "old-revision"]
        if action != "retire":
            argv += ["--file", str(content)]
    main(argv)
    payload = access.apply.call_args.args[1]
    assert payload["operations"][0]["op"] == expected_operation
    if action != "create":
        assert payload["operations"][0]["expected"] == "old-revision"
    assert payload["base_version"] == 3 and payload["request_id"] == "request-1"
    assert load.call_args.args == (None, "test")
    access.close.assert_awaited_once()
    assert '"version": 4' in capsys.readouterr().out
