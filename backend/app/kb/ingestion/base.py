"""
Generic Ingestion Base Classes
Provides abstract interfaces for ingestion phases.
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
