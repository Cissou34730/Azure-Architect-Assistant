"""Generic ingestion module for knowledge base document processing."""

from .base import (
    DocumentCrawler,
    DocumentCleaner,
    IndexBuilder,
    IngestionPhase
)

__all__ = [
    'DocumentCrawler',
    'DocumentCleaner',
    'IndexBuilder',
    'IngestionPhase',
]
