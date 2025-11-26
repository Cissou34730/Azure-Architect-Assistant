"""Generic ingestion module for knowledge base document processing."""

from .base import (
    DocumentCrawler,
    DocumentCleaner,
    IndexBuilder,
    IngestionPipeline,
    IngestionPhase
)
from .job_manager import (
    JobManager,
    IngestionJob,
    JobStatus,
    get_job_manager
)

__all__ = [
    'DocumentCrawler',
    'DocumentCleaner',
    'IndexBuilder',
    'IngestionPipeline',
    'IngestionPhase',
    'JobManager',
    'IngestionJob',
    'JobStatus',
    'get_job_manager'
]
