"""
FastAPI Router for KB Ingestion Endpoints
Clean routing layer - business logic delegated to operations.py
"""

from fastapi import APIRouter, HTTPException
import logging
import asyncio

from app.service_registry import get_kb_manager, invalidate_kb_manager
from app.kb.ingestion.job_manager import get_job_manager, JobStatus
from app.kb.service import clear_index_cache

from .models import (
    CreateKBRequest,
    CreateKBResponse,
    StartIngestionRequest,
    StartIngestionResponse,
    JobStatusResponse,
    JobListResponse,
    KBListResponse
)
from .operations import get_ingestion_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingestion", tags=["kb-ingestion"])


# ============================================================================
# KB Management Endpoints
# ============================================================================

@router.post("/kb/create", response_model=CreateKBResponse)
async def create_kb(request: CreateKBRequest):
    """Create a new knowledge base"""
    try:
        service = get_ingestion_service()
        result = service.create_knowledge_base(request)
        
        # Invalidate KB manager cache to reload config
        invalidate_kb_manager()
        
        return CreateKBResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create KB: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create KB: {str(e)}")


@router.get("/kb/list", response_model=KBListResponse)
async def list_kbs():
    """List all knowledge bases"""
    try:
        kb_manager = get_kb_manager()
        kbs = kb_manager.list_kbs()
        return KBListResponse(knowledge_bases=kbs)
    except Exception as e:
        logger.error(f"Failed to list KBs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list KBs: {str(e)}")


@router.delete("/kb/{kb_id}")
async def delete_kb(kb_id: str):
    """
    Delete a knowledge base and all its data.
    
    This will:
    - Cancel any running ingestion jobs
    - Unload the index from memory
    - Remove the KB from configuration
    - Delete all KB data (index, documents, etc.)
    """
    try:
        kb_manager = get_kb_manager()
        job_manager = get_job_manager()
        
        # Check if KB exists
        if not kb_manager.kb_exists(kb_id):
            raise HTTPException(
                status_code=404,
                detail=f"Knowledge base '{kb_id}' not found"
            )
        
        # Get KB config before deletion
        kb_config = kb_manager.get_kb(kb_id)
        storage_dir = kb_config.index_path if kb_config else None
        
        # Cancel any running jobs
        job = job_manager.get_latest_job_for_kb(kb_id)
        if job and job.status == JobStatus.RUNNING:
            job_manager.cancel_job(job.job_id)
            logger.info(f"Cancelled running job {job.job_id} before deleting KB: {kb_id}")
            await asyncio.sleep(1.0)
        
        # Clear index from memory cache
        if storage_dir:
            clear_index_cache(kb_id=kb_id, storage_dir=storage_dir)
            logger.info(f"Cleared index cache for KB: {kb_id}")
            await asyncio.sleep(0.5)
        
        # Delete the KB
        kb_manager.delete_kb(kb_id)
        
        # Invalidate KB manager cache to reload config
        invalidate_kb_manager()
        
        logger.info(f"Deleted KB: {kb_id}")
        
        return {
            "message": f"Knowledge base '{kb_id}' deleted successfully",
            "kb_id": kb_id
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Failed to delete KB: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete KB: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete KB: {str(e)}")


# ============================================================================
# Ingestion Job Endpoints
# ============================================================================

@router.post("/kb/{kb_id}/start", response_model=StartIngestionResponse)
async def start_ingestion(kb_id: str):
    """Start ingestion for a knowledge base"""
    try:
        service = get_ingestion_service()
        result = service.start_ingestion(kb_id)
        
        # Get job and KB config
        job_manager = get_job_manager()
        job = job_manager.get_job(result['job_id'])
        
        kb_manager = get_kb_manager()
        kb_config = kb_manager.get_kb_config(kb_id)
        
        # Start ingestion using asyncio-based service (KB-centric)
        from app.ingestion.service import IngestionService
        ingest_service = IngestionService.instance()
        # Run the existing pipeline in a worker task (to_thread inside service)
        await ingest_service.start(kb_id, service.run_ingestion_pipeline, job, kb_config)
        
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
        
        # Prefer KB-centric state from IngestionService snapshots
        from app.ingestion.service import IngestionService
        ingest_service = IngestionService.instance()
        state = ingest_service.status(kb_id)
        if state:
            return JobStatusResponse(
                job_id=f"{kb_id}-job",  # placeholder, UI ignores job_id
                kb_id=kb_id,
                status=state.status,
                phase=state.phase,
                progress=state.progress,
                message=state.message,
                error=state.error,
                metrics=state.metrics,
                started_at=None,
                completed_at=None,
            )
        # Fallback to latest job manager entry if snapshot missing
        job_manager = get_job_manager()
        job = job_manager.get_latest_job_for_kb(kb_id)
        if job:
            return JobStatusResponse(
                job_id=job.job_id,
                kb_id=job.kb_id,
                status=job.status,
                phase=job.phase,
                progress=job.progress,
                message=job.message,
                error=job.error,
                metrics=job.metrics,
                started_at=job.started_at,
                completed_at=job.completed_at,
            )
        
        # No state or job found - return default "not started" state
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
        
        # Also update the job manager job status so the pipeline sees it
        job_manager = get_job_manager()
        job = job_manager.get_latest_job_for_kb(kb_id)
        if job:
            job.cancel()
        
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
        
        # Also update the job manager job status so the pipeline sees it
        job_manager = get_job_manager()
        job = job_manager.get_latest_job_for_kb(kb_id)
        if job:
            logger.info(f"PAUSE: Job status before pause: {job.status}")
            job.pause()
            logger.info(f"PAUSE: Job status after pause: {job.status}")
        else:
            logger.warning(f"PAUSE: No job found for KB '{kb_id}'")
        
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
        
        # First update the job manager job status
        job_manager = get_job_manager()
        job = job_manager.get_latest_job_for_kb(kb_id)
        if job:
            job.resume()
        
        # If no task exists (e.g., after restart), rehydrate by starting a worker with checkpoint-aware pipeline
        service = get_ingestion_service()
        kb_manager = get_kb_manager()
        kb_config = kb_manager.get_kb_config(kb_id)
        success = await ingest_service.resume_or_start(kb_id, service.run_ingestion_pipeline, job, kb_config)
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
        job_manager = get_job_manager()
        
        if kb_id:
            jobs = job_manager.get_jobs_for_kb(kb_id, limit=limit)
        else:
            jobs = job_manager.get_all_jobs(limit=limit)
        
        return JobListResponse(
            jobs=[
                JobStatusResponse(
                    job_id=job.job_id,
                    kb_id=job.kb_id,
                    status=job.status,
                    phase=job.phase,
                    progress=job.progress,
                    message=job.message,
                    error=job.error,
                    metrics=job.metrics,
                    started_at=job.started_at,
                    completed_at=job.completed_at
                )
                for job in jobs
            ]
        )
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")
