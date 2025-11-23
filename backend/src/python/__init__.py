"""
WAF (Well-Architected Framework) Documentation Query System

This package provides tools for ingesting, indexing, and querying
Azure Well-Architected Framework documentation.

Components:
- crawler: BFS web crawler for documentation discovery
- ingestion: HTML extraction, cleaning, and text normalization
- chunker: Document chunking and validation
- indexer: Vector index building with OpenAI embeddings
- query_service: Semantic search and answer generation
- query_wrapper: JSON interface for TypeScript integration
"""

__version__ = "1.0.0"
__author__ = "Azure Architect Assistant Team"

# Import main classes for convenience
from .crawler import WAFCrawler
from .ingestion import WAFIngestionPipeline
from .chunker import ChunkValidator
from .indexer import WAFIndexer
from .query_service import WAFQueryService

__all__ = [
    'WAFCrawler',
    'WAFIngestionPipeline',
    'ChunkValidator',
    'WAFIndexer',
    'WAFQueryService',
]
