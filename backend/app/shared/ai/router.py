"""AI routing helpers for primary provider delegation."""

from collections.abc import AsyncIterator
from typing import Any

from .interfaces import EmbeddingProvider, LLMProvider, LLMResponse


class AIRouter:
    """Routes AI requests to the active primary provider."""

    def __init__(
        self,
        *,
        primary_llm: LLMProvider,
        primary_embedding: EmbeddingProvider,
    ) -> None:
        self.primary_llm = primary_llm
        self.primary_embedding = primary_embedding

    async def chat(self, **kwargs: Any) -> LLMResponse | AsyncIterator[str]:
        return await self.primary_llm.chat(**kwargs)

    async def complete(self, **kwargs: Any) -> str:
        return await self.primary_llm.complete(**kwargs)

    async def embed_text(self, text: str) -> list[float]:
        return await self.primary_embedding.embed_text(text)

    async def embed_batch(self, texts: list[str], batch_size: int) -> list[list[float]]:
        return await self.primary_embedding.embed_batch(texts, batch_size)
