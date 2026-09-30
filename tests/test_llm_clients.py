from __future__ import annotations

from collections.abc import Callable
import json
from typing import Any

import httpx
import pytest

from app.llm.base import LLMClient, LLMInvalidJSON, LLMUnavailable, parse_json_object
from app.llm.fallback import FallbackLLMClient, build_llm_from_env
from app.llm.groq_client import GROQ_CHAT_COMPLETIONS_URL, GroqClient
from app.llm.ollama_client import OllamaClient


NO_SLEEP: Callable[[float], None] = lambda _: None


def _groq_client(
    handler: Callable[[httpx.Request], httpx.Response], monkeypatch: pytest.MonkeyPatch
) -> tuple[GroqClient, httpx.Client]:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "test-model")
    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    return GroqClient(http_client=http_client, sleep=NO_SLEEP), http_client


def _groq_success(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": content}}]},
    )


def test_groq_success(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _groq_success('{"intent":"hello"}')

    client, http_client = _groq_client(handler, monkeypatch)
    try:
        assert client.generate_json("system", "user") == {"intent": "hello"}
        assert len(requests) == 1
        assert requests[0].url == GROQ_CHAT_COMPLETIONS_URL
        assert requests[0].headers["Authorization"] == "Bearer test-key"
        payload = json.loads(requests[0].content)
        assert payload["temperature"] == 0
        assert payload["response_format"] == {"type": "json_object"}
    finally:
        http_client.close()


def test_groq_retries_429_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    statuses = iter([429, 200])
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        status = next(statuses)
        return httpx.Response(status, json={"error": "rate limited"}) if status == 429 else _groq_success('{"ok":true}')

    client, http_client = _groq_client(handler, monkeypatch)
    try:
        assert client.generate_json("system", "user") == {"ok": True}
        assert len(requests) == 2
    finally:
        http_client.close()


def test_groq_500_three_times_raises_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(500, text="server error")

    client, http_client = _groq_client(handler, monkeypatch)
    try:
        with pytest.raises(LLMUnavailable, match="after 3 attempts"):
            client.generate_json("system", "user")
        assert len(requests) == 3
    finally:
        http_client.close()


def test_groq_401_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(401, text="invalid key")

    client, http_client = _groq_client(handler, monkeypatch)
    try:
        with pytest.raises(LLMUnavailable, match="HTTP 401") as error:
            client.generate_json("system", "user")
        assert error.value.status_code == 401
        assert len(requests) == 1
    finally:
        http_client.close()


def test_parse_fenced_json_with_surrounding_prose() -> None:
    assert parse_json_object('Here is the result:\n```json\n{"hello": "world"}\n```\nDone.') == {
        "hello": "world"
    }


def test_garbage_groq_content_raises_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    client, http_client = _groq_client(
        lambda _: _groq_success("not JSON at all"), monkeypatch
    )
    try:
        with pytest.raises(LLMInvalidJSON) as error:
            client.generate_json("system", "user")
        assert error.value.raw_text == "not JSON at all"
    finally:
        http_client.close()


def test_groq_json_validation_400_becomes_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    client, http_client = _groq_client(
        lambda _: httpx.Response(400, text="JSON validation failed"), monkeypatch
    )
    try:
        with pytest.raises(LLMInvalidJSON) as error:
            client.generate_json("system", "user")
        assert error.value.raw_text == "JSON validation failed"
    finally:
        http_client.close()


@pytest.mark.parametrize(
    ("api_key", "model", "missing_setting"),
    [(None, "test-model", "GROQ_API_KEY"), ("test-key", None, "GROQ_MODEL")],
)
def test_groq_requires_key_and_model(
    monkeypatch: pytest.MonkeyPatch,
    api_key: str | None,
    model: str | None,
    missing_setting: str,
) -> None:
    if api_key is None:
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
    else:
        monkeypatch.setenv("GROQ_API_KEY", api_key)
    if model is None:
        monkeypatch.delenv("GROQ_MODEL", raising=False)
    else:
        monkeypatch.setenv("GROQ_MODEL", model)
    with pytest.raises(LLMUnavailable, match=missing_setting):
        GroqClient()


def test_ollama_sends_json_chat_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_MODEL", "local-model")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"message": {"content": '{"intent":"hello"}'}})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = OllamaClient(http_client=http_client, sleep=NO_SLEEP)
    try:
        assert client.generate_json("system", "user") == {"intent": "hello"}
        assert len(requests) == 1
        payload = json.loads(requests[0].content)
        assert requests[0].url.path == "/api/chat"
        assert payload["model"] == "local-model"
        assert payload["stream"] is False
        assert payload["format"] == "json"
        assert payload["options"] == {"temperature": 0}
    finally:
        http_client.close()


class StubLLMClient(LLMClient):
    def __init__(self, name: str, result: dict[str, Any] | LLMUnavailable | LLMInvalidJSON) -> None:
        self.name = name
        self.result = result

    def generate_json(self, system: str, user: str) -> dict[str, Any]:
        if isinstance(self.result, (LLMUnavailable, LLMInvalidJSON)):
            raise self.result
        return self.result


def test_fallback_moves_to_second_provider() -> None:
    fallback = FallbackLLMClient(
        [
            StubLLMClient("first", LLMUnavailable("offline")),
            StubLLMClient("second", {"answer": 42}),
        ]
    )
    assert fallback.generate_json("system", "user") == {"answer": 42}
    assert fallback.last_provider == "second"


def test_fallback_with_all_providers_unavailable_lists_reasons() -> None:
    fallback = FallbackLLMClient(
        [
            StubLLMClient("groq", LLMUnavailable("rate limited")),
            StubLLMClient("ollama", LLMUnavailable("connection refused")),
        ]
    )
    with pytest.raises(LLMUnavailable) as error:
        fallback.generate_json("system", "user")
    assert "groq: rate limited" in str(error.value)
    assert "ollama: connection refused" in str(error.value)


def test_fallback_does_not_swallow_invalid_json() -> None:
    invalid = LLMInvalidJSON("malformed", "raw provider text")
    second = StubLLMClient("second", {"should_not": "run"})
    fallback = FallbackLLMClient([StubLLMClient("first", invalid), second])
    with pytest.raises(LLMInvalidJSON) as error:
        fallback.generate_json("system", "user")
    assert error.value is invalid
    assert fallback.last_provider is None


def test_auto_factory_orders_groq_before_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "test-model")
    monkeypatch.setenv("OLLAMA_MODEL", "local-model")
    client = build_llm_from_env()
    assert isinstance(client, FallbackLLMClient)
    assert [provider.name for provider in client.clients] == ["groq", "ollama"]
    client.close()
