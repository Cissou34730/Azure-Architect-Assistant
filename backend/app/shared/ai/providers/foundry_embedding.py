"""AI Foundry embedding provider implementation."""

from __future__ import annotations

import logging

from ..config import AIConfig
from .foundry_client import get_foundry_client
from .foundry_llm import _is_embedding_model, discover_foundry_deployments
from .openai_embedding import EMBEDDING_DIMENSIONS, OpenAIEmbeddingProvider

logger = logging.getLogger(__name__)


class FoundryEmbeddingProvider(OpenAIEmbeddingProvider):
    """AI Foundry implementation of the embedding provider."""

    def __init__(self, config: AIConfig):
        self.config = config
        self.client = get_foundry_client(config)
        self.model = config.foundry_embedding_model
        self._embedding_family = config.openai_embedding_model
        logger.info("AI Foundry Embedding Provider initialized with deployment: %s", self.model)

    async def _list_embedding_deployments(self) -> list[dict[str, str]]:
        return [
            deployment
            for deployment in await discover_foundry_deployments(self.config)
            if _is_embedding_model(deployment["model"])
        ]

    async def _ensure_model_selected(self) -> None:
        if self.model:
            return

        deployments = await self._list_embedding_deployments()
        if not deployments:
            raise ValueError("No AI Foundry embedding deployment available")

        selected = deployments[0]
        self.model = selected["id"]
        self._embedding_family = selected["model"]

    async def embed_text(self, text: str) -> list[float]:
        await self._ensure_model_selected()
        return await super().embed_text(text)

    async def embed_batch(
        self, texts: list[str], batch_size: int = 100
    ) -> list[list[float]]:
        await self._ensure_model_selected()
        return await super().embed_batch(texts, batch_size=batch_size)

    def get_embedding_dimension(self) -> int:
        return EMBEDDING_DIMENSIONS.get(self._embedding_family or self.model, 1536)
