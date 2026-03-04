"""Pydantic models for ingestion API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.services.ingestion_metrics_service import IngestionMetrics, JobStatus


class JobStatusResponse(BaseModel):
    """Job status response."""

    job_id: str
    kb_id: str
    status: str
    counters: dict[str, Any] | None = None
    checkpoint: dict[str, Any] | None = None
    last_error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobViewResponse(BaseModel):
    """Full job view for frontend (aligned with IngestionJob type)."""

    job_id: str
    kb_id: str
    status: JobStatus
    phase: str
    progress: int
    message: str
    error: str | None
    metrics: IngestionMetrics
    started_at: datetime | None
    completed_at: datetime | None
    phase_details: list[dict[str, Any]] | None = None


class PauseResponse(BaseModel):
    """Response from pause operation."""

    status: str
    job_id: str
    kb_id: str | None = None
    message: str


class ResumeResponse(BaseModel):
    """Response from resume operation."""

    status: str
    job_id: str
    kb_id: str
    message: str


class CancelResponse(BaseModel):
    """Response from cancel operation."""

    status: str
    job_id: str
    kb_id: str


class KBIngestionDetailsResponse(BaseModel):
    """Response for KB ingestion details endpoint."""

    kb_id: str
    status: str
    current_phase: str | None = None
    overall_progress: int | None = None
    phase_details: list[dict[str, Any]] | None = None
    counters: dict[str, Any] = Field(default_factory=dict)
