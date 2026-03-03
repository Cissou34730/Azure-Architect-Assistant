"""
Ingestion V2 Router
Clean API endpoints for orchestrator-based ingestion.
See docs/SYSTEM_ARCHITECTURE.md for a pipeline overview.
"""

import logging
from contextlib import suppress
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing_extensions import TypedDict

from app.ingestion.application.status_query_service import StatusQueryService
from app.ingestion.infrastructure import create_job_repository, create_queue_repository
from app.kb import KBManager
from app.service_registry import get_ingestion_runtime_service, get_kb_manager
from app.services.ingestion_metrics_service import (
    IngestionMetrics,
    JobStatus,
    QueueMetrics,
    derive_job_status,
    get_job_counters,
    get_status_message,
    normalize_job_metrics,
)
from app.services.ingestion_runtime import IngestionRuntimeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


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


def get_ingestion_runtime_service_dep() -> IngestionRuntimeService:
    return get_ingestion_runtime_service()


def get_job_repository_dep() -> Any:
    return create_job_repository()


@router.post("/kb/{kb_id}/start", response_model=JobStatusResponse)
async def start_ingestion(
    kb_id: str,
    kb_manager: KBManager = Depends(get_kb_manager),
    runtime_service: IngestionRuntimeService = Depends(get_ingestion_runtime_service_dep),
) -> JobStatusResponse:
    try:
        payload = await runtime_service.start_ingestion(kb_id, kb_manager)
        return JobStatusResponse(**payload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to start ingestion for KB %s: %s", kb_id, exc)
        raise HTTPException(
            status_code=500, detail=f"Failed to start ingestion: {exc}"
        ) from exc


@router.post("/kb/{kb_id}/pause")
async def pause_ingestion(
    kb_id: str,
    runtime_service: IngestionRuntimeService = Depends(get_ingestion_runtime_service_dep),
) -> dict[str, Any]:
    try:
        return await runtime_service.pause_ingestion(kb_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to pause job for KB %s: %s", kb_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to pause job: {exc}") from exc


class ResumeResponse(TypedDict):
    """Response from resume operation."""

    status: str
    job_id: str
    kb_id: str
    message: str


@router.post("/kb/{kb_id}/resume")
async def resume_ingestion(
    kb_id: str,
    kb_manager: KBManager = Depends(get_kb_manager),
    runtime_service: IngestionRuntimeService = Depends(get_ingestion_runtime_service_dep),
) -> ResumeResponse:
    try:
        payload = await runtime_service.resume_ingestion(kb_id, kb_manager)
        return ResumeResponse(**payload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to resume job for KB %s: %s", kb_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to resume job: {exc}") from exc


@router.post("/kb/{kb_id}/cancel")
async def cancel_ingestion(
    kb_id: str,
    runtime_service: IngestionRuntimeService = Depends(get_ingestion_runtime_service_dep),
) -> dict[str, Any]:
    try:
        return await runtime_service.cancel_ingestion(kb_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to cancel job for KB %s: %s", kb_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {exc}") from exc


@router.get("/kb/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    repo: Any = Depends(get_job_repository_dep),
) -> JobStatusResponse:
    try:
        job = repo.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        status = repo.get_job_status(job_id)
        return JobStatusResponse(
            job_id=job.id,
            kb_id=job.kb_id,
            status=status,
            counters=job.counters,
            checkpoint=job.checkpoint,
            last_error=job.last_error,
            started_at=job.created_at,
            finished_at=job.finished_at,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get status for job %s: %s", job_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to get status for job: {job_id}") from exc


@router.get("/kb/{kb_id}/details")
async def get_kb_ingestion_details(
    kb_id: str,
    repo: Any = Depends(get_job_repository_dep),
) -> dict[str, Any]:
    try:
        status_service = StatusQueryService()
        status = status_service.get_status(kb_id)

        counters: dict[str, Any] = {}
        with suppress(Exception):
            job_id = repo.get_latest_job_id(kb_id)
            if job_id:
                job = repo.get_job(job_id)
                counters = job.counters or {}

        return {
            "kb_id": kb_id,
            "status": status.status,
            "current_phase": status.current_phase,
            "overall_progress": status.overall_progress,
            "phase_details": status.phase_details,
            "counters": counters,
        }
    except Exception as exc:
        logger.exception("Failed to get ingestion details for KB %s: %s", kb_id, exc)
        raise HTTPException(status_code=404, detail=f"KB details not found: {kb_id}") from exc


@router.get("/kb/{kb_id}/job-view", response_model=JobViewResponse)
async def get_kb_job_view(kb_id: str) -> JobViewResponse:
    """Return a combined ingestion job view for a KB (single frontend call)."""
    status_service = StatusQueryService()
    job_repo = create_job_repository()
    queue_repo = create_queue_repository()

    kb_status = status_service.get_status(kb_id)
    latest_job_state = job_repo.get_latest_job(kb_id)

    if not latest_job_state:
        return JobViewResponse(
            job_id=f"{kb_id}-job",
            kb_id=kb_id,
            status="not_started",
            phase="loading",
            progress=kb_status.overall_progress,
            message="Waiting to start",
            error=None,
            metrics=IngestionMetrics(),
            started_at=None,
            completed_at=None,
            phase_details=kb_status.phase_details,
        )

    job_id = latest_job_state.job_id
    latest_job_view = job_repo.get_job(job_id) if job_id else None

    raw_metrics = QueueMetrics()
    with suppress(Exception):
        stats = queue_repo.get_queue_stats(job_id)
        raw_metrics = QueueMetrics(
            pending=stats.get("pending", 0),
            processing=stats.get("processing", 0),
            done=stats.get("done", 0),
            error=stats.get("error", 0),
        )

    counters = get_job_counters(latest_job_view)
    metrics = normalize_job_metrics(kb_status, raw_metrics, counters)
    job_status = derive_job_status(latest_job_state, kb_status)
    message = get_status_message(job_status)

    return JobViewResponse(
        job_id=job_id,
        kb_id=kb_id,
        status=job_status,
        phase=kb_status.current_phase or "loading",
        progress=kb_status.overall_progress,
        message=message,
        error=latest_job_view.last_error if latest_job_view else None,
        metrics=metrics,
        started_at=latest_job_state.created_at,
        completed_at=latest_job_view.finished_at if latest_job_view else None,
        phase_details=kb_status.phase_details,
    )


async def cleanup_running_tasks() -> None:
    """Cleanup function to gracefully stop all running ingestion tasks."""
    await get_ingestion_runtime_service().cleanup_running_tasks()
