"""
Ingestion module (orchestrator-first).

Provides the orchestrator-based ingestion pipeline. See docs/SYSTEM_ARCHITECTURE.md for a summary.
Legacy threaded pipeline components have been archived under archive/backend/ingestion_v1.
"""

from app.core.app_settings import IngestionSettings, get_ingestion_settings
from app.ingestion.application.orchestrator import IngestionOrchestrator
from app.ingestion.application.policies import RetryPolicy, WorkflowDefinition
from app.ingestion.domain.enums import JobPhase, PhaseStatus
from app.ingestion.domain.models import IngestionState, IngestionStateSchema, JobRuntime
from app.ingestion.models import (
    IngestionJob,
    IngestionPhaseStatus,
    IngestionQueueItem,
    PhaseStatusDB,
    QueueStatus,
)
from app.ingestion.models import (
    JobStatus as DBJobStatus,
)

__all__ = [
    'DBJobStatus',
    'IngestionJob',
    'IngestionOrchestrator',
    'IngestionPhaseStatus',
    'IngestionQueueItem',
    'IngestionSettings',
    'IngestionState',
    'IngestionStateSchema',
    'JobPhase',
    'JobRuntime',
    'PhaseStatus',
    'PhaseStatusDB',
    'QueueStatus',
    'RetryPolicy',
    'WorkflowDefinition',
    'get_ingestion_settings',
]

__version__ = '2.0.0'
