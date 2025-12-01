"""Shared ingestion state dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class IngestionState:
    """In-memory view of an ingestion job for API consumption."""

    kb_id: str
    job_id: str
    status: str = "pending"  # pending | running | paused | completed | failed | cancelled
    phase: str = "crawling"
    progress: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    error: Optional[str] = None
    paused: bool = False
    cancel_requested: bool = False
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
