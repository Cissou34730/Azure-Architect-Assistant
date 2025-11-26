"""
FastAPI Router for KB Ingestion Endpoints
Clean routing layer - business logic delegated to operations.py
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
import logging
import asyncio

from app.kb.manager import KBManager
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
        kb_manager = KBManager()
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
        kb_manager = KBManager()
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
async def start_ingestion(kb_id: str, background_tasks: BackgroundTasks):
    """Start ingestion for a knowledge base"""
    try:
        service = get_ingestion_service()
        result = service.start_ingestion(kb_id)
        
        # Get job and KB config
        job_manager = get_job_manager()
        job = job_manager.get_job(result['job_id'])
        
        kb_manager = KBManager()
        kb_config = kb_manager.get_kb_config(kb_id)
        
        # Start ingestion in background
        background_tasks.add_task(service.run_ingestion_pipeline, job, kb_config)
        
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
        job_manager = get_job_manager()
        job = job_manager.get_latest_job_for_kb(kb_id)
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"No ingestion job found for KB '{kb_id}'"
            )
        
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
            completed_at=job.completed_at
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
        job_manager = get_job_manager()
        
        # Get latest job for this KB
        job = job_manager.get_latest_job_for_kb(kb_id)
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"No ingestion job found for KB '{kb_id}'"
            )
        
        if job.status != JobStatus.RUNNING:
            raise HTTPException(
                status_code=400,
                detail=f"Job {job.job_id} is not running (status: {job.status})"
            )
        
        # Cancel job
        job_manager.cancel_job(job.job_id)
        
        logger.info(f"Cancelled job {job.job_id} for KB: {kb_id}")
        
        return {
            "message": f"Ingestion job {job.job_id} cancelled",
            "job_id": job.job_id,
            "kb_id": kb_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel ingestion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cancel ingestion: {str(e)}")


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
