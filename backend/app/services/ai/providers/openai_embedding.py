"""
OpenAI Embedding Provider Implementation
"""

import logging
from typing import List
from openai import AsyncOpenAI

from ..interfaces import EmbeddingProvider
from ..config import AIConfig

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
        self.client = AsyncOpenAI(
            api_key=config.openai_api_key,
            timeout=config.openai_timeout,
            max_retries=config.openai_max_retries,
        )
        self.model = config.openai_embedding_model
        logger.info(f"OpenAI Embedding Provider initialized with model: {self.model}")

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        try:
            response = await self.client.embeddings.create(model=self.model, input=text)
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise

    async def embed_batch(
        self, texts: List[str], batch_size: int = 100
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts with batching."""
        all_embeddings = []

        try:
            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]

                response = await self.client.embeddings.create(
                    model=self.model, input=batch
                )

                # Extract embeddings in order
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

                if (i + batch_size) < len(texts):
                    logger.debug(
                        f"Embedded batch {i // batch_size + 1}: {len(batch_embeddings)} texts"
                    )

            logger.info(f"Generated {len(all_embeddings)} embeddings")
            return all_embeddings

        except Exception as e:
            logger.error(f"OpenAI batch embedding error: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings."""
        return EMBEDDING_DIMENSIONS.get(self.model, 1536)

    def get_model_name(self) -> str:
        """Get current model name."""
        return self.model
