"""
Ingestion module (orchestrator-first).

Provides the orchestrator-based ingestion pipeline per docs/ingestion/OrchestratorSpec.md.
Legacy threaded pipeline components have been archived under archive/backend/ingestion_v1.
"""

from app.ingestion.models import (
    IngestionJob,
    IngestionQueueItem,
    IngestionPhaseStatus,
    JobStatus as DBJobStatus,
    QueueStatus,
    PhaseStatusDB,
)

from app.ingestion.application.orchestrator import IngestionOrchestrator
from app.ingestion.application.policies import RetryPolicy, WorkflowDefinition
from app.ingestion.domain.models import IngestionState, IngestionStateSchema, JobRuntime
from app.ingestion.domain.enums import JobPhase, PhaseStatus
from config import get_settings, set_settings, IngestionSettings

__all__ = [
    "IngestionJob",
    "IngestionQueueItem",
    "IngestionPhaseStatus",
    "DBJobStatus",
    "QueueStatus",
    "PhaseStatusDB",
    "IngestionOrchestrator",
    "RetryPolicy",
    "WorkflowDefinition",
    "IngestionState",
    "IngestionStateSchema",
    "JobRuntime",
    "JobPhase",
    "PhaseStatus",
    "get_settings",
    "set_settings",
    "IngestionSettings",
]

__version__ = "2.0.0"
