from collections.abc import AsyncIterator

import pytest

from app.shared.ai.interfaces import EmbeddingProvider, LLMProvider, LLMResponse
from app.shared.ai.router import AIRouter


class _FakeLLMProvider(LLMProvider):
    def __init__(self, *, chat_error: Exception | None = None, complete_error: Exception | None = None, content: str = "ok") -> None:
        self._chat_error = chat_error
        self._complete_error = complete_error
        self._content = content

    async def chat(self, **kwargs) -> LLMResponse | AsyncIterator[str]:
        if self._chat_error:
            raise self._chat_error
        return LLMResponse(content=self._content, model="fake")

    async def complete(self, **kwargs) -> str:
        if self._complete_error:
            raise self._complete_error
        return self._content

    def get_model_name(self) -> str:
        return "fake"

    async def list_runtime_models(self) -> list[dict[str, str]]:
        return [{"id": "fake", "model": "fake"}]


class _FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self, *, embed_error: Exception | None = None, vector: list[float] | None = None) -> None:
        self._embed_error = embed_error
        self._vector = vector or [0.1, 0.2]

    async def embed_text(self, text: str) -> list[float]:
        if self._embed_error:
            raise self._embed_error
        return self._vector

    async def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        if self._embed_error:
            raise self._embed_error
        return [self._vector for _ in texts]

    def get_embedding_dimension(self) -> int:
        return len(self._vector)

    def get_model_name(self) -> str:
        return "fake-embedding"


@pytest.mark.asyncio
async def test_router_primary_success_no_fallback() -> None:
    router = AIRouter(
        primary_llm=_FakeLLMProvider(content="primary"),
        primary_embedding=_FakeEmbeddingProvider(vector=[1.0, 2.0]),
        fallback_enabled=True,
        fallback_llm=_FakeLLMProvider(content="fallback"),
        fallback_embedding=_FakeEmbeddingProvider(vector=[9.0, 9.0]),
    )

    chat = await router.chat(messages=[])
    embed = await router.embed_text("hello")

    assert chat.content == "primary"
    assert embed == [1.0, 2.0]


@pytest.mark.asyncio
async def test_router_transient_failure_falls_back() -> None:
    router = AIRouter(
        primary_llm=_FakeLLMProvider(chat_error=TimeoutError("timeout")),
        primary_embedding=_FakeEmbeddingProvider(),
        fallback_enabled=True,
        fallback_on_transient_only=True,
        fallback_llm=_FakeLLMProvider(content="fallback-success"),
    )

    result = await router.chat(messages=[])

    assert result.content == "fallback-success"


@pytest.mark.asyncio
async def test_router_non_transient_failure_does_not_fallback() -> None:
    router = AIRouter(
        primary_llm=_FakeLLMProvider(chat_error=ValueError("bad request")),
        primary_embedding=_FakeEmbeddingProvider(),
        fallback_enabled=True,
        fallback_on_transient_only=True,
        fallback_llm=_FakeLLMProvider(content="fallback"),
    )

    with pytest.raises(ValueError, match="bad request"):
        await router.chat(messages=[])


@pytest.mark.asyncio
async def test_router_fallback_failure_propagates() -> None:
    router = AIRouter(
        primary_llm=_FakeLLMProvider(chat_error=TimeoutError("primary timeout")),
        primary_embedding=_FakeEmbeddingProvider(),
        fallback_enabled=True,
        fallback_on_transient_only=True,
        fallback_llm=_FakeLLMProvider(chat_error=RuntimeError("fallback failed")),
    )

    with pytest.raises(RuntimeError, match="fallback failed"):
        await router.chat(messages=[])

