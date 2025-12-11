"""
Embedder
Pure async embedding generation for chunks.
Extracts embedding logic without orchestration dependencies.
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Any

from llama_index.embeddings.openai import OpenAIEmbedding

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
    vector: List[float]
    content_hash: str
    text: str
    metadata: Dict[str, Any]


class Embedder:
    """
    Pure async embedder for chunk text.
    Generates vector embeddings without orchestration coupling.
    """
    
    def __init__(self, model_name: str = "text-embedding-3-small"):
        """
        Initialize embedder.
        
        Args:
            model_name: OpenAI embedding model name
        """
        self.model_name = model_name
        self.embedding_client = OpenAIEmbedding(model=model_name)
        logger.info(f"Embedder initialized: model={model_name}")
    
    async def embed(self, chunk) -> EmbeddingResult:
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
            raise ValueError("Cannot embed empty chunk text")
        
        try:
            # Generate embedding (sync call, but fast enough)
            # LlamaIndex OpenAIEmbedding handles retries internally
            logger.debug(f"Generating embedding for chunk {chunk.content_hash[:8]} ({len(chunk.text)} chars)")
            vector = self.embedding_client.get_text_embedding(chunk.text)
            logger.debug(f"Embedding generated: {len(vector)} dimensions")
            
            if not vector:
                raise RuntimeError("Embedding generation returned empty vector")
            
            return EmbeddingResult(
                vector=vector,
                content_hash=chunk.content_hash,
                text=chunk.text,
                metadata=chunk.metadata
            )
            
        except Exception as e:
            logger.error(f"Embedding failed for chunk {chunk.content_hash[:8]}: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}") from e
