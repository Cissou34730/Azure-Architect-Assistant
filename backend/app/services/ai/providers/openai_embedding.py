"""
OpenAI Embedding Provider Implementation
"""

import logging

from ..config import AIConfig
from ..interfaces import EmbeddingProvider
from .openai_client import get_openai_client

logger = logging.getLogger(__name__)

# Embedding dimensions by model
EMBEDDING_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI implementation of embedding provider."""

    def __init__(self, config: AIConfig):
        """
        Initialize OpenAI embedding provider.

        Args:
            config: AI configuration
        """
        self.config = config
        self.client = get_openai_client(config)
        self.model = config.openai_embedding_model
        logger.info("OpenAI Embedding Provider initialized with model: %s", self.model)

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        try:
            response = await self.client.embeddings.create(model=self.model, input=text)
            return response.data[0].embedding
        except Exception as e:
            logger.error("OpenAI embedding error: %s", e)
            raise

    async def embed_batch(
        self, texts: list[str], batch_size: int = 100
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts with batching."""
        if batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {batch_size}")
        all_embeddings = []

        try:
            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]

                response = await self.client.embeddings.create(
                    model=self.model, input=batch
                )

                if len(response.data) != len(batch):
                    raise ValueError(
                        f"Embedding response length mismatch: expected {len(batch)},"
                        f" got {len(response.data)}"
                    )

                # Extract embeddings in order
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

                if (i + batch_size) < len(texts):
                    logger.debug(
                        "Embedded batch %d: %d texts",
                        i // batch_size + 1,
                        len(batch_embeddings),
                    )

            logger.info("Generated %d embeddings", len(all_embeddings))
            return all_embeddings

        except Exception as e:
            logger.error("OpenAI batch embedding error: %s", e)
            raise

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings."""
        return EMBEDDING_DIMENSIONS.get(self.model, 1536)

    def get_model_name(self) -> str:
        """Get current model name."""
        return self.model

