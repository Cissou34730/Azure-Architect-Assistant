"""Integration tests: OpenAILLMProvider.chat retries transient faults."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from openai import RateLimitError

from app.shared.ai.config import AIConfig
from app.shared.ai.interfaces import ChatMessage
from app.shared.ai.providers.openai_llm import OpenAILLMProvider


def _rate_limit_error() -> RateLimitError:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(429, request=request)
    return RateLimitError("rate limited", response=response, body=None)


def _chat_completion(content: str = "hello") -> SimpleNamespace:
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    usage = SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2)
    return SimpleNamespace(choices=[choice], model="gpt-4o-mini", usage=usage)


class _FlakyCompletions:
    def __init__(self, failures: int) -> None:
        self._failures = failures
        self.calls = 0

    async def create(self, **kwargs: Any) -> Any:
        self.calls += 1
        if self.calls <= self._failures:
            raise _rate_limit_error()
        return _chat_completion()


class _FlakyClient:
    def __init__(self, failures: int) -> None:
        self.chat = SimpleNamespace(completions=_FlakyCompletions(failures))

    def with_options(self, **kwargs: Any) -> "_FlakyClient":
        return self


def _provider(monkeypatch: pytest.MonkeyPatch, client: Any) -> OpenAILLMProvider:
    config = AIConfig(llm_provider="openai", openai_api_key="sk-test", transient_max_attempts=3)
    monkeypatch.setattr(
        "app.shared.ai.providers.openai_llm.get_openai_client", lambda _cfg: client
    )
    return OpenAILLMProvider(config)


@pytest.mark.asyncio
async def test_chat_retries_transient_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    # Speed up backoff for the test
    monkeypatch.setattr(
        "app.shared.ai.transient_retry.asyncio.sleep", lambda _s: _noop()
    )

    async def _noop() -> None:  # pragma: no cover - helper
        return None

    client = _FlakyClient(failures=2)
    provider = _provider(monkeypatch, client)

    result = await provider.chat([ChatMessage(role="user", content="hi")])
    assert result.content == "hello"
    assert client.chat.completions.calls == 3


@pytest.mark.asyncio
async def test_chat_raises_after_exhausting_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.shared.ai.transient_retry.asyncio.sleep", lambda _s: _noop()
    )

    async def _noop() -> None:  # pragma: no cover - helper
        return None

    client = _FlakyClient(failures=99)
    provider = _provider(monkeypatch, client)

    with pytest.raises(RateLimitError):
        await provider.chat([ChatMessage(role="user", content="hi")])
    assert client.chat.completions.calls == 3
