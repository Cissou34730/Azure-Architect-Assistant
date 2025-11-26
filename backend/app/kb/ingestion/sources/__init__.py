"""Source-specific ingestion implementations."""

from .web_documentation import WebDocumentationCrawler
from .web_generic import GenericWebCrawler
from .web_cleaner import WebContentCleaner
from .web_indexer import GenericIndexBuilder

__all__ = [
    'WebDocumentationCrawler',
    'GenericWebCrawler',
    'WebContentCleaner',
    'GenericIndexBuilder'
]
