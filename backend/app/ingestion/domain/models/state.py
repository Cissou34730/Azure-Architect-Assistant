"""Ingestion state domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, List

try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

from app.ingestion.domain.enums import JobStatus, JobPhase, PhaseStatus


@dataclass
class IngestionState:
    """In-memory view of an ingestion job for API consumption."""

    kb_id: str
    job_id: str
    status: str = "pending"  # pending | running | completed | failed
    phase: str = "loading"
    progress: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Phase-level tracking (populated from phase_tracker)
    phases: Dict[str, Any] = field(default_factory=dict)

    def get_overall_status(self) -> str:
        """
        Calculate overall job status based on phase statuses.
        
        Logic:
        - If any phase is FAILED -> job is FAILED
        - If all phases are COMPLETED -> job is COMPLETED
        - If any phase is RUNNING or PAUSED -> job is RUNNING
        - Otherwise -> job is PENDING/NOT_STARTED
        """
        if not self.phases:
            return self.status
        
        phase_statuses = [p.get("status", PhaseStatus.NOT_STARTED.value) for p in self.phases.values()]
        
        # Check for failures
        if PhaseStatus.FAILED.value in phase_statuses:
            return JobStatus.FAILED.value
        
        # Check if all completed
        if all(s == PhaseStatus.COMPLETED.value for s in phase_statuses):
            return JobStatus.COMPLETED.value
        
        # Check if any running or paused
        if PhaseStatus.RUNNING.value in phase_statuses or PhaseStatus.PAUSED.value in phase_statuses:
            return JobStatus.RUNNING.value
        
        # Default to current status
        return self.status

    def get_current_phase(self) -> Optional[str]:
        """
        Determine which phase is currently active.
        
        Returns the name of the first phase that is RUNNING or PAUSED.
        If no phase is active, returns the first NOT_STARTED phase.
        If all phases are completed, returns None.
        """
        if not self.phases:
            return self.phase
        
        # Phase order
        phase_order = [
            JobPhase.LOADING.value,
            JobPhase.CHUNKING.value,
            JobPhase.EMBEDDING.value,
            JobPhase.INDEXING.value,
        ]
        
        # First check for active phases (running or paused)
        for phase_name in phase_order:
            if phase_name in self.phases:
                status = self.phases[phase_name].get("status", PhaseStatus.NOT_STARTED.value)
                if status in (PhaseStatus.RUNNING.value, PhaseStatus.PAUSED.value):
                    return phase_name
        
        # Then check for first not-started phase
        for phase_name in phase_order:
            if phase_name in self.phases:
                status = self.phases[phase_name].get("status", PhaseStatus.NOT_STARTED.value)
                if status == PhaseStatus.NOT_STARTED.value:
                    return phase_name
        
        # All phases completed or failed
        return None

    def get_overall_progress(self) -> int:
        """
        Calculate overall progress across all phases.
        Each phase contributes 25% to the total (4 phases).
        """
        if not self.phases:
            return self.progress
        
        phase_order = [
            JobPhase.LOADING.value,
            JobPhase.CHUNKING.value,
            JobPhase.EMBEDDING.value,
            JobPhase.INDEXING.value,
        ]
        
        total_progress = 0
        weight_per_phase = 25  # 100 / 4 phases
        
        for phase_name in phase_order:
            if phase_name in self.phases:
                phase_progress = self.phases[phase_name].get("progress", 0)
                total_progress += (phase_progress * weight_per_phase) // 100
        
        return min(100, total_progress)


if PYDANTIC_AVAILABLE:
    class IngestionStateSchema(BaseModel):
        """Pydantic-compatible schema for API serialization."""

        kb_id: str
        job_id: str
        status: str = Field(default="pending")
        phase: str = Field(default="loading")
        progress: int = Field(default=0, ge=0, le=100)
        metrics: Dict[str, Any] = Field(default_factory=dict)
        message: str = Field(default="")
        error: Optional[str] = None
        created_at: Optional[datetime] = None
        started_at: Optional[datetime] = None
        completed_at: Optional[datetime] = None
        phases: Dict[str, Any] = Field(default_factory=dict)

        class Config:
            from_attributes = True

        @classmethod
        def from_state(cls, state: IngestionState) -> "IngestionStateSchema":
            """Convert dataclass to pydantic model."""
            return cls(
                kb_id=state.kb_id,
                job_id=state.job_id,
                status=state.status,
                phase=state.phase,
                progress=state.progress,
                metrics=state.metrics,
                message=state.message,
                error=state.error,
                created_at=state.created_at,
                started_at=state.started_at,
                completed_at=state.completed_at,
                phases=state.phases,
            )
else:
    # Fallback if pydantic not available
    IngestionStateSchema = IngestionState  # type: ignore
