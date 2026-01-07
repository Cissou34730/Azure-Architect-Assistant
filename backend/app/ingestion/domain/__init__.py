"""Domain layer for ingestion - contains models, enums, interfaces, and errors."""

from .enums import JobPhase, PhaseStatus
from .models import (
    IngestionState,
    IngestionStateSchema,
    JobRuntime,
    PhaseState,
    PhaseStateSchema,
)

__all__ = [
    "JobPhase",
    "PhaseStatus",
    "IngestionState",
    "IngestionStateSchema",
    "JobRuntime",
    "PhaseState",
    "PhaseStateSchema",
]
