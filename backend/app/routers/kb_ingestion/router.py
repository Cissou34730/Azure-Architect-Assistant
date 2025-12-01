"""
FastAPI Router for KB Ingestion Endpoints
Clean routing layer - business logic delegated to operations.py
"""

from fastapi import APIRouter, HTTPException
import logging

from app.service_registry import get_kb_manager

from .models import (
    StartIngestionRequest,
    StartIngestionResponse,
    JobStatusResponse,
    JobListResponse
)
from .operations import get_ingestion_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingestion", tags=["kb-ingestion"])


# ============================================================================
# Ingestion Job Endpoints
# ============================================================================

@router.post("/kb/{kb_id}/start", response_model=StartIngestionResponse)
async def start_ingestion(kb_id: str):
    """Start ingestion for a knowledge base"""
    try:
        service = get_ingestion_service()
        result = service.start_ingestion(kb_id)
        
        kb_manager = get_kb_manager()
        kb_config = kb_manager.get_kb_config(kb_id)
        
        # Start ingestion using asyncio-based service (KB-centric)
        from app.ingestion.service import IngestionService
        ingest_service = IngestionService.instance()
        # Pass only kb_config to pipeline
        await ingest_service.start(kb_id, service.run_ingestion_pipeline, kb_config)
        
        return StartIngestionResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start ingestion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start ingestion: {str(e)}")


@router.get("/kb/{kb_id}/status", response_model=JobStatusResponse)
async def get_kb_status(kb_id: str):
    """Get ingestion status for a KB"""
    try:
        # Check if KB exists
        kb_manager = get_kb_manager()
        if not kb_manager.kb_exists(kb_id):
            raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_id}' not found")
        
        # Get state from IngestionService
        from app.ingestion.service import IngestionService
        ingest_service = IngestionService.instance()
        state = ingest_service.status(kb_id)
        
        if state:
            return JobStatusResponse(
                job_id=f"{kb_id}-job",
                kb_id=kb_id,
                status=state.status,
                phase=state.phase,
                progress=state.progress,
                message=state.message,
                error=state.error,
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
async def cancel_ingestion(kb_id: str):
    """Cancel the running ingestion job for a knowledge base"""
    try:
        # Cancel via KB-centric ingestion service
        from app.ingestion.service import IngestionService
        ingest_service = IngestionService.instance()
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
async def pause_ingestion(kb_id: str):
    """Pause the running ingestion job for a knowledge base"""
    try:
        from app.ingestion.service import IngestionService
        ingest_service = IngestionService.instance()
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
async def resume_ingestion(kb_id: str):
    """Resume a paused ingestion job for a knowledge base"""
    try:
        from app.ingestion.service import IngestionService
        ingest_service = IngestionService.instance()
        
        service = get_ingestion_service()
        kb_manager = get_kb_manager()
        kb_config = kb_manager.get_kb_config(kb_id)
        
        # Pass only kb_config to resume_or_start
        success = await ingest_service.resume_or_start(kb_id, service.run_ingestion_pipeline, kb_config)
        if not success:
            raise HTTPException(status_code=404, detail=f"Unable to resume/start ingestion for KB '{kb_id}'")
        return {"message": f"Ingestion resumed for KB '{kb_id}'", "kb_id": kb_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume ingestion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to resume ingestion: {str(e)}")



@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(kb_id: str = None, limit: int = 50):
    """List all ingestion jobs, optionally filtered by KB"""
    try:
        from app.ingestion.service import IngestionService
        ingest_service = IngestionService.instance()
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
