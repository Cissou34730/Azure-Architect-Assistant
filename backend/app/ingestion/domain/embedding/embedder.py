"""
Embedder
Pure async embedding generation for chunks.
Delegates embedding generation to the unified AIService.
"""

import logging
from dataclasses import dataclass
from typing import Any

from app.ingestion.domain.chunking.adapter import Chunk
from app.shared.ai import get_ai_service

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """
    Result of embedding a chunk.

    Attributes:
        vector: Embedding vector (list of floats)
        content_hash: Content hash for idempotency
        text: Original chunk text
        metadata: Chunk metadata
    """

    vector: list[float]
    content_hash: str
    text: str
    metadata: dict[str, Any]


class Embedder:
    """
    Pure async embedder for chunk text.
    Generates vector embeddings without orchestration coupling.
    """

    def __init__(self, model_name: str | None = None):
        """
        Initialize embedder.

        Args:
            model_name: Runtime embedding model/deployment identity
        """
        self.ai_service = get_ai_service()
        self.model_name = model_name or self.ai_service.get_embedding_model()
        logger.info(f'Embedder initialized: model={self.model_name}')

    async def embed(self, chunk: Chunk) -> EmbeddingResult:
        """
        Generate embedding for a chunk.

        Args:
            chunk: Chunk dataclass with text, content_hash, metadata

        Returns:
            EmbeddingResult with vector, content_hash, metadata

        Raises:
            ValueError: If chunk text is empty
            RuntimeError: If embedding generation fails
        """
        if not chunk.text or not chunk.text.strip():
            raise ValueError('Cannot embed empty chunk text')

        try:
            logger.info(
                f'→ Calling embedding provider: model={self.model_name}, chunk={chunk.content_hash[:8]}, size={len(chunk.text)} chars'
            )

            vector = await self.ai_service.embed_text(chunk.text)

            logger.info(
                f'✓ Embedding response: {len(vector)} dimensions, chunk={chunk.content_hash[:8]}'
            )

            if not vector:
                raise RuntimeError('Embedding generation returned empty vector')

            return EmbeddingResult(
                vector=vector,
                content_hash=chunk.content_hash,
                text=chunk.text,
                metadata=chunk.metadata,
            )

        except Exception as e:
            logger.error(f'✗ Embedding provider error for chunk {chunk.content_hash[:8]}: {e}')
            raise RuntimeError(f'Embedding generation failed: {e}') from e
