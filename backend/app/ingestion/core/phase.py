from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class PhaseStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class PhaseUpdate:
    job_id: str
    kb_id: str
    phase: str
    status: PhaseStatus
    progress: int = 0
    message: str = ""
    items_processed: Optional[int] = None
    error: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class Phase:
    """Interface for ingestion phases to handle signals and report status."""

    def on_signal(self, signal: str) -> None:
        raise NotImplementedError

    def tick(self) -> None:
        raise NotImplementedError

    def get_status(self) -> PhaseUpdate:
        raise NotImplementedError
