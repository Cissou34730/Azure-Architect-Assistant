"""Domain enums and state machine for ingestion lifecycle."""

from __future__ import annotations

import enum
from typing import Dict, Set, Optional


class JobStatus(str, enum.Enum):
    """Lifecycle states for an ingestion job."""
    NOT_STARTED = "not_started"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobPhase(str, enum.Enum):
    """Execution phases within a running job."""

    LOADING = "loading"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class PhaseStatus(str, enum.Enum):
    """Status for individual ingestion phases."""

    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


# State transition map: current_status -> allowed_next_statuses
_TRANSITION_MAP: Dict[JobStatus, Set[JobStatus]] = {
    JobStatus.NOT_STARTED: {JobStatus.RUNNING},
    JobStatus.PENDING: {JobStatus.RUNNING},
    JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED},
    JobStatus.COMPLETED: set(),  # Terminal state
    JobStatus.FAILED: set(),  # Terminal state
}



