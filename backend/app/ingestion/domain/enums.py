"""Domain enums for ingestion phases and status."""

from __future__ import annotations

import enum


class JobPhase(str, enum.Enum):
    """Execution phases within a running job."""

    LOADING = 'loading'
    CHUNKING = 'chunking'
    EMBEDDING = 'embedding'
    INDEXING = 'indexing'


class PhaseStatus(str, enum.Enum):
    """Status for individual ingestion phases."""

    NOT_STARTED = 'not_started'
    RUNNING = 'running'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAILED = 'failed'
