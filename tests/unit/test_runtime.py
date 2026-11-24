from unittest.mock import MagicMock

import pytest
from support.runtime import TestRuntime


def runtime_with(responses):
    runtime = object.__new__(TestRuntime)
    runtime.connection = MagicMock()
    results = []
    for kind, value in responses:
        result = MagicMock()
        if kind == "one":
            result.fetchone.return_value = value
        else:
            result.__iter__.return_value = iter(value)
        results.append(result)
    runtime.connection.execute.side_effect = results
    return runtime


@pytest.mark.parametrize("schema", ["private", "pgxdata", None])
def test_reset_refuses_non_public_search_path_before_mutation(schema):
    runtime = runtime_with([("one", (schema,))])
    with pytest.raises(ValueError, match="schema"):
        runtime.reset()
    assert runtime.connection.execute.call_count == 1


def test_reset_refuses_other_business_schema_and_unknown_table():
    for responses in (
        [("one", ("public",)), ("one", (1,))],
        [("one", ("public",)), ("one", None), ("rows", [("other_business",)])],
    ):
        runtime = runtime_with(responses)
        with pytest.raises(ValueError):
            runtime.reset()
        assert not any("TRUNCATE" in str(call.args[0]) for call in runtime.connection.execute.call_args_list)


def test_reset_refuses_nonempty_shared_ncc_dev_database():
    runtime = runtime_with([("one", ("public",)), ("one", None), ("rows", [("ncc_scope",)]), ("one", (1,))])
    with pytest.raises(ValueError, match="拒绝执行清库"):
        runtime.reset()
    assert not any("TRUNCATE" in str(call.args[0]) for call in runtime.connection.execute.call_args_list)


def test_reset_is_schema_qualified_and_cannot_cascade_outside_ncc():
    runtime = runtime_with([("one", ("public",)), ("one", None), ("rows", [("ncc_scope",)]), ("one", None), ("one", None)])
    runtime.reset()
    sql = runtime.connection.execute.call_args.args[0].as_string()
    assert sql.startswith('TRUNCATE TABLE "public"."ncc_')
    assert "CASCADE" not in sql
    schema_check = runtime.connection.execute.call_args_list[1].args[0]
    assert "starts_with(schemaname, 'pg_')" in schema_check


def test_runtime_generates_isolated_ephemeral_credentials(monkeypatch):
    import support.runtime as runtime_mod

    monkeypatch.setattr(
        "support.runtime.test_settings",
        lambda path=None, override=None: MagicMock(public_origin="http://127.0.0.1:8788"),
    )
    assert not hasattr(runtime_mod, "USERNAME")
    assert not hasattr(runtime_mod, "PASSWORD")
    r1 = TestRuntime()
    r2 = TestRuntime()
    assert r1.username.startswith("browser-author-")
    assert r2.username.startswith("browser-author-")
    assert r1.username != r2.username
    assert r1.password != r2.password
    assert len(r1.password) >= 24
    sub_user, sub_pw = r1.new_credentials("studio-author")
    assert sub_user.startswith("studio-author-")
    assert sub_user in r1._ephemeral_usernames
    assert len(sub_pw) >= 24
