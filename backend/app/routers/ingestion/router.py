"""
Ingestion V2 Router
Clean API endpoints for orchestrator-based ingestion.
See docs/SYSTEM_ARCHITECTURE.md for a pipeline overview.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import (
    get_ingestion_runtime_service_dependency,
    get_kb_manager,
)
from app.kb import KBManager
from app.services.ingestion_read_service import (
    IngestionReadService,
    get_ingestion_read_service,
)
from app.services.ingestion_runtime import IngestionRuntimeService

from .ingestion_models import (
    CancelResponse,
    JobStatusResponse,
    JobViewResponse,
    KBIngestionDetailsResponse,
    PauseResponse,
    ResumeResponse,
)

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


def get_ingestion_runtime_service_dep() -> IngestionRuntimeService:
    return get_ingestion_runtime_service_dependency()


def get_ingestion_read_service_dep() -> IngestionReadService:
    return get_ingestion_read_service()


@router.post("/kb/{kb_id}/start", response_model=JobStatusResponse)
async def start_ingestion(
    kb_id: str,
    kb_manager: KBManager = Depends(get_kb_manager),
    runtime_service: IngestionRuntimeService = Depends(get_ingestion_runtime_service_dep),
) -> JobStatusResponse:
    payload = await runtime_service.start_ingestion(kb_id, kb_manager)
    return JobStatusResponse(**payload)


@router.post("/kb/{kb_id}/pause", response_model=PauseResponse)
async def pause_ingestion(
    kb_id: str,
    runtime_service: IngestionRuntimeService = Depends(get_ingestion_runtime_service_dep),
) -> PauseResponse:
    payload = await runtime_service.pause_ingestion(kb_id)
    return PauseResponse.model_validate(payload)


@router.post("/kb/{kb_id}/resume", response_model=ResumeResponse)
async def resume_ingestion(
    kb_id: str,
    kb_manager: KBManager = Depends(get_kb_manager),
    runtime_service: IngestionRuntimeService = Depends(get_ingestion_runtime_service_dep),
) -> ResumeResponse:
    payload = await runtime_service.resume_ingestion(kb_id, kb_manager)
    return ResumeResponse.model_validate(payload)


@router.post("/kb/{kb_id}/cancel", response_model=CancelResponse)
async def cancel_ingestion(
    kb_id: str,
    runtime_service: IngestionRuntimeService = Depends(get_ingestion_runtime_service_dep),
) -> CancelResponse:
    payload = await runtime_service.cancel_ingestion(kb_id)
    return CancelResponse.model_validate(payload)


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    read_service: IngestionReadService = Depends(get_ingestion_read_service_dep),
) -> JobStatusResponse:
    try:
        payload = read_service.get_job_status(job_id)
        return JobStatusResponse.model_validate(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/kb/{kb_id}/details", response_model=KBIngestionDetailsResponse)
async def get_kb_ingestion_details(
    kb_id: str,
    read_service: IngestionReadService = Depends(get_ingestion_read_service_dep),
) -> KBIngestionDetailsResponse:
    try:
        payload = read_service.get_kb_ingestion_details(kb_id)
        return KBIngestionDetailsResponse.model_validate(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"KB details not found: {kb_id}") from exc


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


async def cleanup_running_tasks() -> None:
    """Cleanup function to gracefully stop all running ingestion tasks."""
    await get_ingestion_runtime_service_dependency().cleanup_running_tasks()
