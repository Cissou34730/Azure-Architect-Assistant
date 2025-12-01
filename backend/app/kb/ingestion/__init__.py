"""Generic ingestion module for knowledge base document processing."""

from .base import (
    DocumentCrawler,
    DocumentCleaner,
    IndexBuilder,
    IngestionPipeline,
    IngestionPhase
)

__all__ = [
    'DocumentCrawler',
    'DocumentCleaner',
    'IndexBuilder',
    'IngestionPipeline',
    'IngestionPhase',
]
