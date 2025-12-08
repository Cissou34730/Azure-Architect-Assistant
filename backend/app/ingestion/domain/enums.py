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


# State transition map: current_status -> allowed_next_statuses
_TRANSITION_MAP: Dict[JobStatus, Set[JobStatus]] = {
    JobStatus.NOT_STARTED: {JobStatus.RUNNING},
    JobStatus.PENDING: {JobStatus.RUNNING},
    JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED},
    JobStatus.COMPLETED: set(),  # Terminal state
    JobStatus.FAILED: set(),  # Terminal state
}


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, current: JobStatus, target: JobStatus):
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid transition from {current.value} to {target.value}. "
            f"Allowed: {[s.value for s in _TRANSITION_MAP.get(current, set())]}"
        )


def validate_transition(current: JobStatus, target: JobStatus) -> bool:
    """Check if transition from current to target status is valid."""
    allowed = _TRANSITION_MAP.get(current, set())
    return target in allowed


def transition_or_raise(current: JobStatus, target: JobStatus) -> None:
    """Validate transition and raise StateTransitionError if invalid."""
    if not validate_transition(current, target):
        raise StateTransitionError(current, target)


def get_allowed_transitions(status: JobStatus) -> Set[JobStatus]:
    """Return set of allowed next statuses from current status."""
    return _TRANSITION_MAP.get(status, set()).copy()


def is_terminal_status(status: JobStatus) -> bool:
    """Check if status is a terminal state (no further transitions)."""
    return len(_TRANSITION_MAP.get(status, set())) == 0
