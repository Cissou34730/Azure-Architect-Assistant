"""
Ingestion Phases Enum
Defines phases of the ingestion process.
"""

from enum import Enum


class IngestionPhase(str, Enum):
    """Phases of the ingestion process."""
    CRAWLING = "crawling"
    CLEANING = "cleaning"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"