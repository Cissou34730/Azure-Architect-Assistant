"""
Resilient ingestion module with layered architecture.

This module provides a robust ingestion system for knowledge base processing with:
- Layered architecture (domain, infrastructure, application)
- Producer-consumer threading model
- State machine with validated transitions
- Pause/resume from checkpoints
- Structured logging with correlation IDs
- Prometheus-style metrics
- Protocol-based extensibility

Quick Start:
    >>> from app.ingestion.application.ingestion_service import IngestionService
    >>> service = IngestionService.instance()
    >>> state = await service.start(kb_id="my-kb", run_callable=my_function)
    >>> await service.pause(kb_id="my-kb")
    >>> await service.resume(kb_id="my-kb", run_callable=my_function)

Configuration:
    Configure via environment variables (see config/settings.py):
    - INGESTION_BATCH_SIZE: Queue batch size (default: 50)
    - INGESTION_DATA_ROOT: Data directory (default: data/knowledge_bases)
    - INGESTION_LOG_LEVEL: Logging level (default: INFO)

Architecture:
    domain/         - Core business logic, models, interfaces
    infrastructure/ - Database and persistence implementations
    application/    - Service orchestration and utilities
    workers/        - Producer and consumer thread workers
    config/         - Typed configuration
    observability/  - Logging and metrics

See README.md and docs/ingestion/ for detailed documentation.
"""

# Legacy database models (for backward compatibility)
from app.ingestion.models import IngestionJob, IngestionQueueItem, JobStatus as DBJobStatus, QueueStatus

# New layered architecture exports
from app.ingestion.application.ingestion_service import IngestionService
from app.ingestion.domain.models import IngestionState, IngestionStateSchema, JobRuntime
from app.ingestion.domain.enums import JobStatus, JobPhase
from config import get_settings, set_settings, IngestionSettings

__all__ = [
    # Legacy models (backward compatibility)
    "IngestionJob",
    "IngestionQueueItem",
    "DBJobStatus",
    "QueueStatus",
    # New architecture
    "IngestionService",
    "IngestionState",
    "IngestionStateSchema",
    "JobRuntime",
    "JobStatus",
    "JobPhase",
    "get_settings",
    "set_settings",
    "IngestionSettings",
]

__version__ = "2.0.0"
