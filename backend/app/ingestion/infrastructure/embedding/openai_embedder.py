"""
OpenAI Embedder
Generates embeddings using OpenAI embedding models.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from llama_index.core import Document as LlamaDocument

from app.ingestion.domain.phase_tracker import IngestionPhase
from app.services.ai import get_ai_service

from .embedder_base import BaseEmbedder

logger = logging.getLogger(__name__)

# Constants
MAX_DOC_ID_LENGTH = 200
PROGRESS_CB_INTERVAL = 10
EMBEDDING_P_START = 25
EMBEDDING_P_SPAN = 50
EMBEDDING_P_END = 75


class OpenAIEmbedder(BaseEmbedder):
    """
    Generate embeddings using OpenAI embedding models.
    Uses unified AIService for consistent configuration and monitoring.
    """

    def __init__(self, model_name: str = 'text-embedding-3-small'):
        """
        Initialize OpenAI embedder.

        Args:
            model_name: OpenAI embedding model name
        """
        super().__init__(model_name)
        self.ai_service = get_ai_service()
        self.logger.info(f'OpenAIEmbedder initialized with model: {model_name}')

    def _to_llama_document(self, index: int, doc: dict[str, Any]) -> LlamaDocument | None:
        """Convert raw document dictionary to LlamaIndex Document with metadata."""
        content = doc.get("content", "")
        metadata = doc.get("metadata", {})

        if not content:
            self.logger.warning(f"Skipping document {index}: empty content")
            return None

        # Create document ID
        doc_id = (
            metadata.get("url")
            or metadata.get("file_path")
            or f'doc_{metadata.get("doc_id", index)}'
        )
        if len(doc_id) > MAX_DOC_ID_LENGTH:
            doc_id = doc_id[:MAX_DOC_ID_LENGTH]

        return LlamaDocument(text=content, metadata=metadata, id_=doc_id)

    def _execute_batch_embedding(self, texts: list[str]) -> list[list[float]]:
        """Run async batch embedding within synchronous context."""
        try:
            return asyncio.run(self.ai_service.embed_batch(texts))
        except RuntimeError as exc:
            raise RuntimeError(
                'OpenAIEmbedder.embed_documents() cannot be called from a running event loop. '
                'Call ai_service.embed_batch(...) from async code instead.'
            ) from exc

    def embed_documents(
        self,
        documents: list[dict[str, Any]],
        progress_callback: Callable[..., Any] | None = None,
    ) -> list[Any]:
        """Generate embeddings for documents yields LlamaIndex objects."""
        if not self.validate_documents(documents):
            raise ValueError("Document validation failed")

        self.logger.info(f"Generating embeddings for {len(documents)} documents")

        llama_docs: list[LlamaDocument] = []
        for i, doc in enumerate(documents):
            ld = self._to_llama_document(i, doc)
            if ld:
                llama_docs.append(ld)

        if progress_callback:
            progress_callback(
                IngestionPhase.EMBEDDING,
                EMBEDDING_P_START,
                f"Generating embeddings for {len(llama_docs)} documents...",
                {"documents": len(llama_docs)},
            )

        embeddings = self._execute_batch_embedding([d.text for d in llama_docs])

        # Assign results back to Llama docs
        for i, (l_doc, b_embedding) in enumerate(zip(llama_docs, embeddings, strict=True)):
            l_doc.embedding = b_embedding
            if progress_callback and i % PROGRESS_CB_INTERVAL == 0:
                p = EMBEDDING_P_START + int((i / len(llama_docs)) * EMBEDDING_P_SPAN)
                progress_callback(
                    IngestionPhase.EMBEDDING,
                    p,
                    f"Embedded {i}/{len(llama_docs)} documents",
                    {"embedded": i, "total": len(llama_docs)},
                )

        if progress_callback:
            progress_callback(
                IngestionPhase.EMBEDDING,
                EMBEDDING_P_END,
                f"Embedding complete: {len(llama_docs)} documents",
                {"documents": len(llama_docs)},
            )

        return llama_docs
