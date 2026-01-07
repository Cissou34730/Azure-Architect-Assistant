"""
Semantic Chunker
Sentence-aware chunking using LlamaIndex SentenceSplitter.
"""

import logging
from typing import List, Dict, Any

from llama_index.core.node_parser import SentenceSplitter

from .chunker_base import BaseChunker

logger = logging.getLogger(__name__)


class SemanticChunker(BaseChunker):
    """
    Semantic chunker that respects sentence boundaries.
    Uses LlamaIndex SentenceSplitter for intelligent text splitting.
    """

    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 200):
        """
        Initialize semantic chunker.

        Args:
            chunk_size: Target size for chunks (in tokens/characters)
            chunk_overlap: Overlap between chunks for context preservation
        """
        super().__init__(chunk_size, chunk_overlap)
        self.splitter = SentenceSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        logger.info(
            f"SemanticChunker initialized: size={chunk_size}, overlap={chunk_overlap}"
        )

    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk documents with semantic boundaries.

        Args:
            documents: List of LlamaIndex Document objects or dicts with 'content' and 'metadata' keys
            state: Optional IngestionState for cooperative pause/cancel checking

        Returns:
            List of chunks with text and enriched metadata
        """
        chunks = []

        for doc_idx, doc in enumerate(documents):
            # Pause/cancel handled at pipeline level (batch boundaries)

            # Handle both LlamaIndex Document objects and dicts
            if hasattr(doc, "text"):
                # LlamaIndex Document object
                content = doc.text
                metadata = doc.metadata or {}
            else:
                # Dictionary format
                content = doc.get("content", "")
                metadata = doc.get("metadata", {})

            if not content:
                logger.warning(f"Skipping document {doc_idx}: empty content")
                continue

            # Split into sentence-aware chunks
            text_chunks = self.splitter.split_text(content)

            for chunk_idx, chunk_text in enumerate(text_chunks):
                chunks.append(
                    {
                        "content": chunk_text,  # Fixed: use 'content' not 'text'
                        "metadata": {
                            **metadata,
                            "chunk_index": chunk_idx,
                            "total_chunks": len(text_chunks),
                            "chunk_size": len(chunk_text),
                            "chunking_strategy": "semantic",
                        },
                    }
                )

        logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")
        return chunks
