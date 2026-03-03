"""
Ingestion V2 Router
Clean API endpoints for orchestrator-based ingestion.
See docs/SYSTEM_ARCHITECTURE.md for a pipeline overview.
"""

import logging
from datetime import datetime
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing_extensions import TypedDict

from app.dependencies import (
    get_ingestion_runtime_service_dependency,
    get_kb_manager,
)
from app.ingestion.infrastructure import create_job_repository
from app.kb import KBManager
from app.routers.error_utils import internal_server_error
from app.services.ingestion_metrics_service import (
    IngestionMetrics,
    JobStatus,
)
from app.services.ingestion_read_service import (
    IngestionReadService,
    get_ingestion_read_service,
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
    return get_ingestion_runtime_service_dependency()


def get_job_repository_dep() -> Any:
    return create_job_repository()


def get_ingestion_read_service_dep() -> IngestionReadService:
    return get_ingestion_read_service()


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
        raise internal_server_error(
            logger=logger,
            message=f"Failed to start ingestion for KB {kb_id}: {exc!s}",
            exc=exc,
            detail_prefix="Failed to start ingestion",
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
        raise internal_server_error(
            logger=logger,
            message=f"Failed to pause ingestion for KB {kb_id}: {exc!s}",
            exc=exc,
            detail_prefix="Failed to pause job",
        ) from exc


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
        return cast(ResumeResponse, payload)
    except HTTPException:
        raise
    except Exception as exc:
        raise internal_server_error(
            logger=logger,
            message=f"Failed to resume ingestion for KB {kb_id}: {exc!s}",
            exc=exc,
            detail_prefix="Failed to resume job",
        ) from exc


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
        raise internal_server_error(
            logger=logger,
            message=f"Failed to cancel ingestion for KB {kb_id}: {exc!s}",
            exc=exc,
            detail_prefix="Failed to cancel job",
        ) from exc


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
        raise internal_server_error(
            logger=logger,
            message=f"Failed to get status for job {job_id}: {exc!s}",
            exc=exc,
            detail_prefix="Failed to get status for job",
        ) from exc


@router.get("/kb/{kb_id}/details")
async def get_kb_ingestion_details(
    kb_id: str,
    read_service: IngestionReadService = Depends(get_ingestion_read_service_dep),
) -> dict[str, Any]:
    try:
        return read_service.get_kb_ingestion_details(kb_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"KB details not found: {kb_id}") from exc
    except Exception as exc:
        raise internal_server_error(
            logger=logger,
            message=f"Failed to get ingestion details for KB {kb_id}: {exc!s}",
            exc=exc,
            detail_prefix="Failed to get KB details",
        ) from exc


@router.get("/kb/{kb_id}/job-view", response_model=JobViewResponse)
async def get_kb_job_view(
    kb_id: str,
    read_service: IngestionReadService = Depends(get_ingestion_read_service_dep),
) -> JobViewResponse:
    """Return a combined ingestion job view for a KB (single frontend call)."""
    try:
        return JobViewResponse.model_validate(read_service.get_kb_job_view(kb_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"KB job view not found: {kb_id}") from exc
    except Exception as exc:
        raise internal_server_error(
            logger=logger,
            message=f"Failed to get job view for KB {kb_id}: {exc!s}",
            exc=exc,
            detail_prefix="Failed to get KB job view",
        ) from exc


async def cleanup_running_tasks() -> None:
    """Cleanup function to gracefully stop all running ingestion tasks."""
    await get_ingestion_runtime_service_dependency().cleanup_running_tasks()
