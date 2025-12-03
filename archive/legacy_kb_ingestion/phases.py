"""
Ingestion Phases Enum
Defines phases of the ingestion process.
"""

from enum import Enum


class IngestionPhase(str, Enum):
    """Phases of the ingestion process."""
    LOADING = "loading"      # Source-specific document loading
    CHUNKING = "chunking"    # Splitting documents into chunks
    EMBEDDING = "embedding"  # Generating vector embeddings
    INDEXING = "indexing"    # Building vector index
    COMPLETED = "completed"
    FAILED = "failed"