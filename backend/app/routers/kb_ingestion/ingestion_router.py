"""
FastAPI Router for KB Ingestion Endpoints
Clean routing layer - business logic delegated to operations.py
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
import logging

from app.ingestion.application.ingestion_service import IngestionService
from app.service_registry import get_kb_manager
from app.kb.manager import KBManager

from .ingestion_models import (
    StartIngestionRequest,
    StartIngestionResponse,
    JobStatusResponse,
    JobListResponse
)
from .ingestion_operations import KBIngestionService, get_ingestion_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingestion", tags=["kb-ingestion"])


# ============================================================================
# Dependency Injection
# ============================================================================

def get_kb_manager_dep() -> KBManager:
    """Dependency for KB Manager - allows mocking in tests"""
    return get_kb_manager()


def get_ingestion_service_dep() -> IngestionService:
    """Dependency for Ingestion Service - allows mocking in tests"""
    return IngestionService.instance()


def get_operations_service_dep() -> KBIngestionService:
    """Dependency for Operations Service - allows mocking in tests"""
    return get_ingestion_service()


# ============================================================================
# Ingestion Job Endpoints
# ============================================================================

@router.post("/kb/{kb_id}/start", response_model=StartIngestionResponse)
async def start_ingestion(
    kb_id: str,
    kb_manager: KBManager = Depends(get_kb_manager_dep),
    ingest_service: IngestionService = Depends(get_ingestion_service_dep),
    operations: KBIngestionService = Depends(get_operations_service_dep)
) -> StartIngestionResponse:
    """Start ingestion for a knowledge base"""
    try:
        # Validate and get orchestration result
        result = operations.start_ingestion(kb_id)
        
        # Get KB configuration
        kb_config = kb_manager.get_kb_config(kb_id)
        
        # Start ingestion
        await ingest_service.start(kb_id, kb_config)
        
        return StartIngestionResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start ingestion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start ingestion: {str(e)}")


@router.get("/kb/{kb_id}/status", response_model=JobStatusResponse)
async def get_kb_status(
    kb_id: str,
    kb_manager: KBManager = Depends(get_kb_manager_dep),
    ingest_service: IngestionService = Depends(get_ingestion_service_dep)
) -> JobStatusResponse:
    """Get ingestion status for a KB"""
    try:
        # Check if KB exists
        if not kb_manager.kb_exists(kb_id):
            raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_id}' not found")
        
        # Get state from IngestionService
        state = ingest_service.status(kb_id)
        
        if state:
            # Enrich with live queue stats
            queue_has_work = False
            if state.job_id:
                try:
                    from app.ingestion.infrastructure.repository import create_database_repository
                    repo = create_database_repository()
                    queue_stats = repo.get_queue_stats(state.job_id)
                    state.metrics.update({
                        'chunks_pending': queue_stats['pending'],
                        'chunks_processing': queue_stats['processing'],
                        'chunks_embedded': queue_stats['done'],
                        'chunks_failed': queue_stats['error'],
                        'chunks_queued': sum(queue_stats.values()),
                    })
                    # Check if there's pending work (can resume)
                    queue_has_work = queue_stats['pending'] > 0 or queue_stats['processing'] > 0
                except Exception as e:
                    logger.warning(f"Failed to get queue stats: {e}")
            
            # Override status if job failed but work remains (should show as paused/resumable)
            adjusted_status = state.status
            adjusted_message = state.message
            if state.status == "failed" and queue_has_work:
                adjusted_status = "paused"
                adjusted_message = f"Ingestion incomplete: {queue_stats['pending']} chunks pending. Click Resume to continue."
                logger.info(f"KB {kb_id}: Failed job has {queue_stats['pending']} pending chunks - treating as paused/resumable")
            
            return JobStatusResponse(
                job_id=f"{kb_id}-job",
                kb_id=kb_id,
                status=adjusted_status,
                phase=state.phase,
                progress=state.progress,
                message=adjusted_message,
                error=state.error if adjusted_status == "failed" else None,
                metrics=state.metrics,
                started_at=state.started_at,
                completed_at=state.completed_at,
            )
        
        # No state found - return default "not started" state
        return JobStatusResponse(
            job_id=f"{kb_id}-pending",
            kb_id=kb_id,
            status="pending",
            phase="crawling",
            progress=0,
            message="No ingestion started",
            error=None,
            metrics={},
            started_at=None,
            completed_at=None,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.post("/kb/{kb_id}/cancel")
async def cancel_ingestion(
    kb_id: str,
    ingest_service: IngestionService = Depends(get_ingestion_service_dep)
) -> Dict[str, str]:
    """Cancel the running ingestion job for a knowledge base"""
    try:
        success = await ingest_service.cancel(kb_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"No active ingestion for KB '{kb_id}'")
        
        return {"message": f"Ingestion cancelled for KB '{kb_id}'", "kb_id": kb_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel ingestion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cancel ingestion: {str(e)}")


@router.post("/kb/{kb_id}/pause")
async def pause_ingestion(
    kb_id: str,
    ingest_service: IngestionService = Depends(get_ingestion_service_dep)
) -> Dict[str, str]:
    """Pause the running ingestion job for a knowledge base"""
    try:
        success = await ingest_service.pause(kb_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"No running ingestion for KB '{kb_id}'")
        
        return {"message": f"Ingestion paused for KB '{kb_id}'", "kb_id": kb_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause ingestion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to pause ingestion: {str(e)}")


@router.post("/kb/{kb_id}/resume")
async def resume_ingestion(
    kb_id: str,
    kb_manager: KBManager = Depends(get_kb_manager_dep),
    ingest_service: IngestionService = Depends(get_ingestion_service_dep)
) -> Dict[str, str]:
    """Resume a paused ingestion job for a knowledge base"""
    try:
        logger.info(f"[resume_endpoint] KB {kb_id}: Resume endpoint called")
        
        logger.info(f"[resume_endpoint] KB {kb_id}: Checking if KB exists")
        kb_config = kb_manager.get_kb_config(kb_id)
        logger.info(f"[resume_endpoint] KB {kb_id}: KB config retrieved, calling resume")
        
        # Resume with kb_config only
        success = await ingest_service.resume(kb_id, kb_config)
        logger.info(f"[resume_endpoint] KB {kb_id}: resume returned {success}")
        if not success:
            logger.error(f"[resume_endpoint] KB {kb_id}: resume returned False")
            raise HTTPException(status_code=404, detail=f"Unable to resume ingestion for KB '{kb_id}'")
        return {"message": f"Ingestion resumed for KB '{kb_id}'", "kb_id": kb_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[resume_endpoint] Failed to resume ingestion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to resume ingestion: {str(e)}")



@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    kb_id: Optional[str] = None,
    limit: int = 50,
    ingest_service: IngestionService = Depends(get_ingestion_service_dep)
) -> JobListResponse:
    """List all ingestion jobs, optionally filtered by KB"""
    try:
        states = ingest_service.list_kb_states()
        
        # Filter by kb_id if specified
        if kb_id:
            states = {k: v for k, v in states.items() if k == kb_id}
        
        # Convert to list and limit
        state_list = list(states.values())[:limit]
        
        return JobListResponse(
            jobs=[
                JobStatusResponse(
                    job_id=f"{state.kb_id}-job",
                    kb_id=state.kb_id,
                    status=state.status,
                    phase=state.phase,
                    progress=state.progress,
                    message=state.message,
                    error=state.error,
                    metrics=state.metrics,
                    started_at=state.started_at,
                    completed_at=state.completed_at
                )
                for state in state_list
            ]
        )
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")
