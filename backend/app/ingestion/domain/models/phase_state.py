"""Phase state domain model for tracking individual ingestion phases."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

from app.ingestion.domain.enums import PhaseStatus, JobPhase


@dataclass
class PhaseState:
    """State tracking for an individual ingestion phase."""

    phase_name: str  # loading, chunking, embedding, indexing
    status: PhaseStatus = PhaseStatus.NOT_STARTED
    progress: int = 0  # 0-100
    items_processed: int = 0
    items_total: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    def start(self) -> None:
        """Mark phase as running."""
        self.status = PhaseStatus.RUNNING
        self.started_at = datetime.utcnow()

    def pause(self) -> None:
        """Mark phase as paused."""
        self.status = PhaseStatus.PAUSED

    def resume(self) -> None:
        """Resume phase from paused state."""
        self.status = PhaseStatus.RUNNING

    def complete(self) -> None:
        """Mark phase as completed."""
        self.status = PhaseStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.progress = 100

    def fail(self, error: str) -> None:
        """Mark phase as failed with error message."""
        self.status = PhaseStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error = error

    def update_progress(self, items_processed: int, items_total: Optional[int] = None) -> None:
        """Update progress metrics."""
        self.items_processed = items_processed
        if items_total is not None:
            self.items_total = items_total
        
        # Calculate percentage
        if self.items_total and self.items_total > 0:
            self.progress = min(100, int((self.items_processed / self.items_total) * 100))
        else:
            # If total unknown, show progress but cap at 99 until completed
            self.progress = min(99, self.items_processed)

    def is_terminal(self) -> bool:
        """Check if phase is in a terminal state (completed or failed)."""
        return self.status in (PhaseStatus.COMPLETED, PhaseStatus.FAILED)

    def is_active(self) -> bool:
        """Check if phase is actively running."""
        return self.status == PhaseStatus.RUNNING


if PYDANTIC_AVAILABLE:
    class PhaseStateSchema(BaseModel):
        """Pydantic-compatible schema for API serialization."""

        phase_name: str
        status: str = Field(default=PhaseStatus.NOT_STARTED.value)
        progress: int = Field(default=0, ge=0, le=100)
        items_processed: int = Field(default=0)
        items_total: Optional[int] = None
        started_at: Optional[datetime] = None
        completed_at: Optional[datetime] = None
        error: Optional[str] = None

        class Config:
            from_attributes = True

        @classmethod
        def from_phase_state(cls, phase: PhaseState) -> "PhaseStateSchema":
            """Convert dataclass to pydantic model."""
            return cls(
                phase_name=phase.phase_name,
                status=phase.status.value,
                progress=phase.progress,
                items_processed=phase.items_processed,
                items_total=phase.items_total,
                started_at=phase.started_at,
                completed_at=phase.completed_at,
                error=phase.error,
            )
else:
    # Fallback if pydantic not available
    PhaseStateSchema = PhaseState  # type: ignore
