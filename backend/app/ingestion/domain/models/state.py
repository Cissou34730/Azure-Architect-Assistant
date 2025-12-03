"""Ingestion state domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False


@dataclass
class IngestionState:
    """In-memory view of an ingestion job for API consumption."""

    kb_id: str
    job_id: str
    status: str = "pending"  # pending | running | paused | completed | failed | cancelled
    phase: str = "loading"
    progress: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    error: Optional[str] = None
    paused: bool = False
    cancel_requested: bool = False
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Phase-level tracking (optional, populated from phase_tracker if available)
    phase_status: Optional[Dict[str, Any]] = None


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
        paused: bool = False
        cancel_requested: bool = False
        created_at: Optional[datetime] = None
        started_at: Optional[datetime] = None
        completed_at: Optional[datetime] = None
        phase_status: Optional[Dict[str, Any]] = None

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
                paused=state.paused,
                cancel_requested=state.cancel_requested,
                created_at=state.created_at,
                started_at=state.started_at,
                completed_at=state.completed_at,
                phase_status=state.phase_status,
            )
else:
    # Fallback if pydantic not available
    IngestionStateSchema = IngestionState  # type: ignore
