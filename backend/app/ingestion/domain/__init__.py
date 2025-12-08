"""Domain layer for ingestion - contains models, enums, interfaces, and errors."""

from .enums import JobStatus, JobPhase, PhaseStatus
from .models import IngestionState, IngestionStateSchema, JobRuntime, PhaseState, PhaseStateSchema

__all__ = [
    "JobStatus",
    "JobPhase",
    "PhaseStatus",
    "IngestionState",
    "IngestionStateSchema",
    "JobRuntime",
    "PhaseState",
    "PhaseStateSchema",
]
