"""AI routing helpers with cross-provider fallback on transient faults."""

import logging
from collections.abc import AsyncIterator, Callable
from typing import Any

from .interfaces import EmbeddingProvider, LLMProvider, LLMResponse
from .transient_retry import is_transient_llm_error

logger = logging.getLogger(__name__)


class AIRouter:
    """Routes AI requests to the primary provider, falling back on transient faults.

    Fallback providers are supplied as *factories* so they are only
    instantiated (and only consume credentials/connections) when actually
    needed.  Fallback is triggered exclusively by transient infrastructure
    faults (rate limits, 5xx, timeouts, connection errors); deterministic
    errors such as 400/401/403 propagate immediately without fallback.
    """

    def __init__(
        self,
        *,
        primary_llm: LLMProvider,
        primary_embedding: EmbeddingProvider,
        fallback_llm_factories: dict[str, Callable[[], LLMProvider]] | None = None,
    ) -> None:
        self.primary_llm = primary_llm
        self.primary_embedding = primary_embedding
        self._fallback_llm_factories = fallback_llm_factories or {}
        self._fallback_llm_cache: dict[str, LLMProvider] = {}

    def _iter_fallback_llms(self) -> list[LLMProvider]:
        """Instantiate (lazily, cached) and return fallback LLM providers in order."""
        providers: list[LLMProvider] = []
        for name, factory in self._fallback_llm_factories.items():
            if name in self._fallback_llm_cache:
                providers.append(self._fallback_llm_cache[name])
                continue
            try:
                provider = factory()
            except Exception as exc:  # noqa: BLE001 - skip unbuildable fallbacks
                logger.warning("Skipping LLM fallback '%s': factory failed: %s", name, exc)
                continue
            self._fallback_llm_cache[name] = provider
            providers.append(provider)
        return providers

    async def chat(self, **kwargs: Any) -> LLMResponse | AsyncIterator[str]:
        # Streaming responses are consumed incrementally; falling back
        # mid-stream is not meaningful, so only non-streaming calls fall back.
        if kwargs.get("stream"):
            return await self.primary_llm.chat(**kwargs)

        primary_error: Exception | None = None
        try:
            return await self.primary_llm.chat(**kwargs)
        except Exception as error:  # noqa: BLE001 - classified below
            if not is_transient_llm_error(error):
                raise
            primary_error = error

        fallbacks = self._iter_fallback_llms()
        if not fallbacks:
            raise primary_error
        logger.warning(
            "Primary LLM failed with transient error: %s — trying %d fallback(s)",
            primary_error,
            len(fallbacks),
        )

        last_error: Exception = primary_error
        for name, provider in zip(
            list(self._fallback_llm_factories.keys()), fallbacks, strict=False
        ):
            try:
                result = await provider.chat(**kwargs)
                logger.info("LLM fallback '%s' succeeded", name)
                return result
            except Exception as error:  # noqa: BLE001 - try next fallback
                last_error = error
                if not is_transient_llm_error(error):
                    raise
                logger.warning("LLM fallback '%s' failed transiently: %s", name, error)
        raise last_error

    async def complete(self, **kwargs: Any) -> str:
        primary_error: Exception | None = None
        try:
            return await self.primary_llm.complete(**kwargs)
        except Exception as error:  # noqa: BLE001 - classified below
            if not is_transient_llm_error(error):
                raise
            primary_error = error

        fallbacks = self._iter_fallback_llms()
        if not fallbacks:
            raise primary_error
        logger.warning(
            "Primary LLM complete failed transiently: %s — trying %d fallback(s)",
            primary_error,
            len(fallbacks),
        )

        last_error: Exception = primary_error
        for name, provider in zip(
            list(self._fallback_llm_factories.keys()), fallbacks, strict=False
        ):
            try:
                return await provider.complete(**kwargs)
            except Exception as error:  # noqa: BLE001 - try next fallback
                last_error = error
                if not is_transient_llm_error(error):
                    raise
                logger.warning("LLM fallback '%s' failed transiently: %s", name, error)
        raise last_error

    async def embed_text(self, text: str) -> list[float]:
        return await self.primary_embedding.embed_text(text)

    async def embed_batch(self, texts: list[str], batch_size: int) -> list[list[float]]:
        return await self.primary_embedding.embed_batch(texts, batch_size)
