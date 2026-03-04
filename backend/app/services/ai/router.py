"""AI routing helpers for primary provider with optional fallback."""

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, TypeVar, cast

from openai import APIError, APITimeoutError, RateLimitError

from .interfaces import EmbeddingProvider, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

T = TypeVar("T")
HTTP_TOO_MANY_REQUESTS = 429
HTTP_SERVER_ERROR_MIN = 500
HTTP_SERVER_ERROR_MAX_EXCLUSIVE = 600


class AIRouter:
    """Routes AI requests to primary provider and optional fallback provider."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        primary_llm: LLMProvider,
        primary_embedding: EmbeddingProvider,
        fallback_llm: LLMProvider | None = None,
        fallback_embedding: EmbeddingProvider | None = None,
        fallback_enabled: bool = False,
        fallback_on_transient_only: bool = True,
    ) -> None:
        self.primary_llm = primary_llm
        self.primary_embedding = primary_embedding
        self.fallback_llm = fallback_llm
        self.fallback_embedding = fallback_embedding
        self.fallback_enabled = fallback_enabled
        self.fallback_on_transient_only = fallback_on_transient_only

    async def chat(self, **kwargs: Any) -> LLMResponse | AsyncIterator[str]:
        stream = kwargs.get("stream", False)
        if stream:
            return await self._chat_stream_with_fallback(**kwargs)
        fallback_call: Callable[[], Awaitable[LLMResponse | AsyncIterator[str]]] | None = None
        if self.fallback_llm is not None:
            fallback_llm = self.fallback_llm

            def fallback_call() -> Awaitable[LLMResponse | AsyncIterator[str]]:
                return fallback_llm.chat(**kwargs)

        return await self._execute_with_fallback(
            primary_call=lambda: self.primary_llm.chat(**kwargs),
            fallback_call=fallback_call,
            capability="chat",
        )

    async def complete(self, **kwargs: Any) -> str:
        fallback_call: Callable[[], Awaitable[str]] | None = None
        if self.fallback_llm is not None:
            fallback_llm = self.fallback_llm

            def fallback_call() -> Awaitable[str]:
                return fallback_llm.complete(**kwargs)

        return await self._execute_with_fallback(
            primary_call=lambda: self.primary_llm.complete(**kwargs),
            fallback_call=fallback_call,
            capability="complete",
        )

    async def embed_text(self, text: str) -> list[float]:
        fallback_call: Callable[[], Awaitable[list[float]]] | None = None
        if self.fallback_embedding is not None:
            fallback_embedding = self.fallback_embedding

            def fallback_call() -> Awaitable[list[float]]:
                return fallback_embedding.embed_text(text)

        return await self._execute_with_fallback(
            primary_call=lambda: self.primary_embedding.embed_text(text),
            fallback_call=fallback_call,
            capability="embed_text",
        )

    async def embed_batch(self, texts: list[str], batch_size: int) -> list[list[float]]:
        fallback_call: Callable[[], Awaitable[list[list[float]]]] | None = None
        if self.fallback_embedding is not None:
            fallback_embedding = self.fallback_embedding

            def fallback_call() -> Awaitable[list[list[float]]]:
                return fallback_embedding.embed_batch(texts, batch_size)

        return await self._execute_with_fallback(
            primary_call=lambda: self.primary_embedding.embed_batch(texts, batch_size),
            fallback_call=fallback_call,
            capability="embed_batch",
        )

    async def _chat_stream_with_fallback(self, **kwargs: Any) -> AsyncIterator[str]:
        """
        Stream fallback strategy:
        - fallback is attempted only before the first token is emitted
        - once streaming has started, primary stream errors are propagated
        """
        try:
            primary_stream = await self.primary_llm.chat(**kwargs)
            primary_stream = cast(AsyncIterator[str], primary_stream)
        except Exception as primary_error:
            if self._should_fallback(primary_error) and self.fallback_llm is not None:
                logger.warning("Primary chat stream init failed, using fallback provider: %s", primary_error)
                fallback_stream = await self.fallback_llm.chat(**kwargs)
                return cast(AsyncIterator[str], fallback_stream)
            raise

        async def _stream_with_guard() -> AsyncIterator[str]:
            emitted_any = False
            try:
                async for chunk in primary_stream:
                    emitted_any = True
                    yield chunk
            except Exception as primary_error:
                if (
                    not emitted_any
                    and self._should_fallback(primary_error)
                    and self.fallback_llm is not None
                ):
                    logger.warning(
                        "Primary chat stream failed before first token, switching to fallback: %s",
                        primary_error,
                    )
                    fallback_stream = await self.fallback_llm.chat(**kwargs)
                    fallback_stream = cast(AsyncIterator[str], fallback_stream)
                    async for chunk in fallback_stream:
                        yield chunk
                    return
                raise

        return _stream_with_guard()

    async def _execute_with_fallback(
        self,
        *,
        primary_call: Callable[[], Awaitable[T]],
        fallback_call: Callable[[], Awaitable[T]] | None,
        capability: str,
    ) -> T:
        try:
            return await primary_call()
        except Exception as primary_error:
            if not self._should_fallback(primary_error) or fallback_call is None:
                raise

            logger.warning(
                "Primary provider failed for %s, trying fallback provider: %s",
                capability,
                primary_error,
            )
            return await fallback_call()

    def _should_fallback(self, error: Exception) -> bool:
        if not self.fallback_enabled:
            return False
        if not self.fallback_on_transient_only:
            return True

        if isinstance(error, (APITimeoutError, RateLimitError, TimeoutError)):
            return True

        if isinstance(error, APIError):
            status_code = getattr(error, "status_code", None)
            if status_code is None:
                return True
            return status_code == HTTP_TOO_MANY_REQUESTS or (
                HTTP_SERVER_ERROR_MIN <= status_code < HTTP_SERVER_ERROR_MAX_EXCLUSIVE
            )

        return False
