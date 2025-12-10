"""
Ingestion V2 Router
Clean API endpoints for orchestrator-based ingestion.
Per backend/docs/ingestion/OrchestratorSpec.md
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.ingestion.application.orchestrator import IngestionOrchestrator, WorkflowDefinition, RetryPolicy
from app.ingestion.infrastructure.repository import DatabaseRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingestion/v2", tags=["ingestion-v2"])


# Request/Response models
class StartIngestionRequest(BaseModel):
    """Request to start ingestion for a KB."""
    source_type: str
    source_config: Dict[str, Any]
    embedding_model: Optional[str] = "text-embedding-3-small"
    chunking: Optional[Dict[str, Any]] = None


class JobStatusResponse(BaseModel):
    """Job status response."""
    job_id: str
    kb_id: str
    status: str
    counters: Optional[Dict[str, Any]] = None
    checkpoint: Optional[Dict[str, Any]] = None
    last_error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


# Global repository instance
repo = DatabaseRepository()


async def run_orchestrator_background(job_id: str, kb_id: str, kb_config: Dict[str, Any]):
    """
    Background task to run orchestrator.
    
    Args:
        job_id: Job identifier
        kb_id: Knowledge base identifier
        kb_config: KB configuration
    """
    orchestrator = IngestionOrchestrator(
        repo=repo,
        workflow=WorkflowDefinition(),
        retry_policy=RetryPolicy(max_attempts=3)
    )
    
    try:
        await orchestrator.run(job_id, kb_id, kb_config)
    except Exception as e:
        logger.exception(f"Orchestrator failed for job {job_id}: {e}")


@router.post("/jobs/{kb_id}/start", response_model=JobStatusResponse)
async def start_ingestion(
    kb_id: str,
    request: StartIngestionRequest,
    background_tasks: BackgroundTasks
):
    """
    Start ingestion for a knowledge base.
    
    Args:
        kb_id: Knowledge base identifier
        request: Ingestion configuration
        background_tasks: FastAPI background tasks
        
    Returns:
        Job status response
    """
    try:
        # Create job
        job_id = repo.create_job(
            kb_id=kb_id,
            source_type=request.source_type,
            source_config=request.source_config,
            priority=0
        )
        
        # Build KB config for orchestrator
        kb_config = {
            'kb_id': kb_id,
            'source_type': request.source_type,
            'source_config': request.source_config,
            'embedding_model': request.embedding_model,
            'chunking': request.chunking or {}
        }
        
        # Spawn orchestrator in background
        background_tasks.add_task(run_orchestrator_background, job_id, kb_id, kb_config)
        
        logger.info(f"Started ingestion job {job_id} for KB {kb_id}")
        
        return JobStatusResponse(
            job_id=job_id,
            kb_id=kb_id,
            status="running",
            started_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.exception(f"Failed to start ingestion for KB {kb_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start ingestion: {e}")


@router.post("/jobs/{job_id}/pause")
async def pause_ingestion(job_id: str):
    """
    Pause ingestion job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Success message
    """
    try:
    try:
        repo.update_job(job_id, status="paused")
        logger.info(f"Paused job {job_id}")
        return {"status": "paused", "job_id": job_id}
    except Exception as e:
        logger.exception(f"Failed to pause job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to pause job: {e}")


@router.post("/jobs/{job_id}/resume")
async def resume_ingestion(job_id: str):
    """
    Resume paused ingestion job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Success message
    """
    try:
        repo.update_job(job_id, status="running")
        logger.info(f"Resumed job {job_id}")
        return {"status": "running", "job_id": job_id}
    except Exception as e:
        logger.exception(f"Failed to resume job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resume job: {e}")


@router.post("/jobs/{job_id}/cancel")
async def cancel_ingestion(job_id: str):
    """
    Cancel ingestion job and trigger cleanup.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Success message
        
    Note:
        Cleanup (delete vectors, reset state) happens in orchestrator on next gate check.
    """
    try:
        repo.update_job(job_id, status="canceled")
        logger.info(f"Canceled job {job_id}")
        return {"status": "canceled", "job_id": job_id}
    except Exception as e:
        logger.exception(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {e}")


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get job status and progress.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Job status response with counters and checkpoint
    """
    try:
        # Get job details
        job = repo.get_job(job_id)
        status = repo.get_job_status(job_id)
        
        return JobStatusResponse(
            job_id=job.id,
            kb_id=job.kb_id,
            status=status,
            counters=job.counters,
            checkpoint=job.checkpoint,
            last_error=job.last_error,
            started_at=None,  # TODO: Add created_at to JobView
            finished_at=job.finished_at
        )
    except Exception as e:
        logger.exception(f"Failed to get status for job {job_id}: {e}")
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
