from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest

from ncc_data.application.model_settings import check_configuration
from ncc_data.creation.gateway import ChatProvider, estimate_tokens
from ncc_data.domain.definitions import SYSTEM_SCOPE
from ncc_shared.errors import DomainError


class _FakeDB:
    def __init__(self, scope):
        self._scope = scope

    async def get(self, model, key):
        if key == SYSTEM_SCOPE:
            return self._scope
        return None


def _settings_stub(*, secret: str = "sk-unit-secret-value-1234567890"):
    return SimpleNamespace(
        model_url="https://gateway.example.com/v1",
        model_key=secret,
        writer_model="deepseek-chat",
        judge_model="deepseek-reasoner",
        second_judge_model="",
        model_timeout=8.0,
        credentials={"DEEPSEEK_API_KEY": secret},
    )


def test_estimate_tokens_handles_chinese_and_ascii_within_realistic_bounds():
    assert estimate_tokens("") == 0
    # 3 chapters * 4,000 Chinese chars = 12,000 CJK chars (previously 36,000 UTF-8 bytes > 24,000 budget)
    cjk_text = ("风雪夜归人执剑问苍生" * 1200)
    assert len(cjk_text) == 12_000
    cjk_tokens = estimate_tokens(cjk_text)
    assert 12_000 <= cjk_tokens <= 14_000

    ascii_text = "chapter outline beat " * 500
    ascii_tokens = estimate_tokens(ascii_text)
    assert ascii_tokens < len(ascii_text)


@pytest.mark.asyncio
async def test_chat_provider_allows_three_4000_char_chinese_chapters_under_default_24k_budget():
    chapter_prose = "长街夜雪落无声，少年按剑立于灯下，回想师门旧事与今夜抉择。" * 150
    chapter_prose = chapter_prose[:4000]
    assert len(chapter_prose) == 4000
    packet = {
        "objective": "续写第四章：破庙对峙与抉择",
        "previous_chapters": [
            {"id": f"ch-{idx}", "name": f"第{idx}章", "text": chapter_prose}
            for idx in (1, 2, 3)
        ],
    }
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {"text": "第四章正文：寒风吹开庙门。", "data": {}, "claims": []},
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
                # Omit usage to exercise conservative_estimate path too
            },
        )

    provider = ChatProvider(_settings_stub(), transport=httpx.MockTransport(handler))
    result, meta = await provider.call("write", packet, 24000)
    assert result["text"].startswith("第四章正文")
    assert captured["body"]["max_tokens"] >= 256
    assert captured["body"]["max_tokens"] <= 8192
    assert meta["kind"] == "conservative_estimate"
    # Conservative estimate uses estimate_tokens rather than raw UTF-8 byte length (~36KB+)
    assert meta["tokens"] < 20000

    # Excessively small budget still triggers token_budget guard deterministically
    with pytest.raises(DomainError) as exc_info:
        await provider.call("write", packet, 1000)
    assert exc_info.value.code == "token_budget"


@pytest.mark.asyncio
async def test_check_configuration_static_and_live_probe_never_leak_api_key():
    secret = "sk-live-probe-top-secret-99887766"
    settings = _settings_stub(secret=secret)
    scope = SimpleNamespace(
        id=SYSTEM_SCOPE,
        config={
            "model_registry": {
                "configurations": [
                    {
                        "id": "cfg-deepseek",
                        "name": "DeepSeek 主力",
                        "supplier": "DeepSeek",
                        "base_url": "https://api.deepseek.com",
                        "auth_ref": "DEEPSEEK_API_KEY",
                        "model_key": "deepseek-chat",
                        "purposes": ["plan", "write", "revise", "judge"],
                        "enabled": True,
                    },
                    {
                        "id": "cfg-incomplete",
                        "name": "未填地址",
                        "supplier": "兼容接口",
                        "base_url": "",
                        "auth_ref": "DEEPSEEK_API_KEY",
                        "model_key": "",
                        "purposes": ["write"],
                        "enabled": False,
                    },
                ],
                "defaults": {"write": "cfg-deepseek"},
            }
        },
    )
    svc = SimpleNamespace(actor=SimpleNamespace(admin=True), db=_FakeDB(scope))

    # 1) live=False static check makes zero network calls
    def forbid_network(request: httpx.Request) -> httpx.Response:
        raise AssertionError("live=False must not issue HTTP requests")

    static_res = await check_configuration(
        svc, settings, "cfg-deepseek", live=False, transport=httpx.MockTransport(forbid_network)
    )
    assert static_res["mode"] == "config"
    assert static_res["ok"] is True
    assert static_res["connection"]["status"] == "loaded"
    assert secret not in json.dumps(static_res, ensure_ascii=False)

    # 2) live=True on incomplete config fails fast without network
    incomplete_res = await check_configuration(
        svc, settings, "cfg-incomplete", live=True, transport=httpx.MockTransport(forbid_network)
    )
    assert incomplete_res["mode"] == "live"
    assert incomplete_res["ok"] is False
    assert incomplete_res["status_code"] is None
    assert incomplete_res["model_found"] is None

    # 3) live=True HTTP 200 GET /models finds configured model
    seen_requests: list[httpx.Request] = []

    def ok_models(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return httpx.Response(200, json={"data": [{"id": "deepseek-chat"}, {"id": "deepseek-reasoner"}]})

    live_ok = await check_configuration(
        svc, settings, "cfg-deepseek", live=True, transport=httpx.MockTransport(ok_models)
    )
    assert len(seen_requests) == 1
    assert seen_requests[0].method == "GET"
    assert str(seen_requests[0].url) == "https://api.deepseek.com/models"
    assert seen_requests[0].headers["authorization"] == f"Bearer {secret}"
    assert live_ok["ok"] is True
    assert live_ok["mode"] == "live"
    assert live_ok["status_code"] == 200
    assert live_ok["model_found"] is True
    assert secret not in json.dumps(live_ok, ensure_ascii=False)

    # 4) live=True HTTP 401 whose upstream body echoes the secret must NEVER leak the secret
    def unauthorized_echo(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": f"Invalid key: {secret}"}})

    live_401 = await check_configuration(
        svc, settings, "cfg-deepseek", live=True, transport=httpx.MockTransport(unauthorized_echo)
    )
    assert live_401["ok"] is False
    assert live_401["mode"] == "live"
    assert live_401["status_code"] == 401
    assert live_401["model_found"] is None
    assert secret not in json.dumps(live_401, ensure_ascii=False)

    # 5) live=True network failure returns clean diagnostic without secret
    def connect_fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"connect failed with {secret}", request=request)

    live_err = await check_configuration(
        svc, settings, "cfg-deepseek", live=True, transport=httpx.MockTransport(connect_fail)
    )
    assert live_err["ok"] is False
    assert live_err["mode"] == "live"
    assert live_err["status_code"] is None
    assert live_err["model_found"] is None
    assert secret not in json.dumps(live_err, ensure_ascii=False)
