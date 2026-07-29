"""Tests for AIRouter cross-provider fallback on transient faults."""

from __future__ import annotations

from typing import Any

import pytest

from app.shared.ai.interfaces import ChatMessage, LLMResponse
from app.shared.ai.router import AIRouter


class _StubEmbedding:
    async def embed_text(self, text: str) -> list[float]:
        return [0.1]

    async def embed_batch(self, texts: list[str], batch_size: int) -> list[list[float]]:
        return [[0.1] for _ in texts]

    def get_embedding_dimension(self) -> int:
        return 1

    def get_model_name(self) -> str:
        return "stub-embedding"


class _FlakyLLM:
    """LLM provider stub that fails a configurable number of times."""

    def __init__(self, name: str, failures: int, *, transient: bool = True) -> None:
        self.name = name
        self._failures = failures
        self.calls = 0
        self._transient = transient

    async def chat(self, **kwargs: Any) -> LLMResponse:
        self.calls += 1
        if self.calls <= self._failures:
            if self._transient:
                from openai import APIConnectionError
                import httpx

                request = httpx.Request("POST", "https://example.test/v1/chat")
                raise APIConnectionError(request=request)
            raise ValueError(f"{self.name}: deterministic failure")
        return LLMResponse(content=f"from-{self.name}", model=self.name, usage=None, finish_reason="stop")

    async def complete(self, **kwargs: Any) -> str:
        response = await self.chat(**kwargs)
        return response.content

    def get_model_name(self) -> str:
        return self.name

    async def list_runtime_models(self) -> list[dict[str, str]]:
        return []


def _router(primary: Any, fallbacks: dict[str, Any] | None = None) -> AIRouter:
    return AIRouter(
        primary_llm=primary,
        primary_embedding=_StubEmbedding(),
        fallback_llm_factories=fallbacks or {},
    )


@pytest.mark.asyncio
async def test_primary_success_no_fallback() -> None:
    primary = _FlakyLLM("primary", failures=0)
    fallback = _FlakyLLM("fallback", failures=0)
    router = _router(primary, {"fallback": lambda: fallback})

    result = await router.chat(messages=[ChatMessage(role="user", content="hi")])
    assert result.content == "from-primary"
    assert fallback.calls == 0


@pytest.mark.asyncio
async def test_fallback_on_transient_failure() -> None:
    primary = _FlakyLLM("primary", failures=99, transient=True)
    fallback = _FlakyLLM("fallback", failures=0)
    router = _router(primary, {"fallback": lambda: fallback})

    result = await router.chat(messages=[ChatMessage(role="user", content="hi")])
    assert result.content == "from-fallback"
    assert fallback.calls == 1


@pytest.mark.asyncio
async def test_no_fallback_on_deterministic_failure() -> None:
    primary = _FlakyLLM("primary", failures=99, transient=False)
    fallback = _FlakyLLM("fallback", failures=0)
    router = _router(primary, {"fallback": lambda: fallback})

    with pytest.raises(ValueError):
        await router.chat(messages=[ChatMessage(role="user", content="hi")])
    assert fallback.calls == 0


@pytest.mark.asyncio
async def test_fallbacks_tried_in_order() -> None:
    primary = _FlakyLLM("primary", failures=99)
    first = _FlakyLLM("first", failures=99)
    second = _FlakyLLM("second", failures=0)
    router = _router(primary, {"first": lambda: first, "second": lambda: second})

    result = await router.chat(messages=[ChatMessage(role="user", content="hi")])
    assert result.content == "from-second"
    assert first.calls == 1
    assert second.calls == 1


@pytest.mark.asyncio
async def test_raises_when_all_providers_fail() -> None:
    primary = _FlakyLLM("primary", failures=99)
    fallback = _FlakyLLM("fallback", failures=99)
    router = _router(primary, {"fallback": lambda: fallback})

    with pytest.raises(Exception):
        await router.chat(messages=[ChatMessage(role="user", content="hi")])


@pytest.mark.asyncio
async def test_fallback_factory_failure_is_skipped() -> None:
    primary = _FlakyLLM("primary", failures=99)

    def _broken_factory() -> Any:
        raise RuntimeError("cannot build fallback")

    fallback = _FlakyLLM("fallback", failures=0)
    router = _router(primary, {"broken": _broken_factory, "fallback": lambda: fallback})

    result = await router.chat(messages=[ChatMessage(role="user", content="hi")])
    assert result.content == "from-fallback"
