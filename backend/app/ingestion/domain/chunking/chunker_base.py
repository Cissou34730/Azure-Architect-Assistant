"""
Base Chunker
Abstract base class for document chunking strategies.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseChunker(ABC):
    """Abstract base class for document chunkers"""

    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 200):
        """
        Initialize chunker.

        Args:
            chunk_size: Target size for chunks
            chunk_overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @abstractmethod
    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk documents into smaller pieces.

        Args:
            documents: List of documents with 'content' and 'metadata' keys

        Returns:
            List of chunks with text and enriched metadata
        """
        pass
