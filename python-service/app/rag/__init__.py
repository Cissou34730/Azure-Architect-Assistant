"""
WAF (Well-Architected Framework) Documentation Query System

This package provides tools for ingesting, indexing, and querying
Azure Well-Architected Framework documentation.

Components:
- crawler: BFS web crawler for documentation discovery
- cleaner: HTML extraction, cleaning, and text normalization
- indexer: Vector index building with OpenAI embeddings
- query_service: Semantic search and answer generation
- query_wrapper: JSON interface for TypeScript integration
"""

__version__ = "1.0.0"
__author__ = "Azure Architect Assistant Team"

# Import main classes for convenience
from .crawler import WAFCrawler
from .cleaner import WAFIngestionPipeline
from .indexer import WAFIndexBuilder
from .query_service import WAFQueryService

__all__ = [
    'WAFCrawler',
    'WAFIngestionPipeline',
    'WAFIndexBuilder',
    'WAFQueryService',
]
