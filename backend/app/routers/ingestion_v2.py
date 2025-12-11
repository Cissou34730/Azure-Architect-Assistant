"""
Ingestion V2 Router
Clean API endpoints for orchestrator-based ingestion.
Per backend/docs/ingestion/OrchestratorSpec.md
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.ingestion.application.orchestrator import IngestionOrchestrator, WorkflowDefinition, RetryPolicy
from app.ingestion.infrastructure.repository import DatabaseRepository
from app.service_registry import get_kb_manager
from app.kb.knowledge_base_manager import KBManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


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

# Track running orchestrator tasks for graceful shutdown
_running_tasks: Dict[str, asyncio.Task] = {}  # job_id -> task mapping


async def run_orchestrator_background(job_id: str, kb_id: str, kb_config: Dict[str, Any]):
    """
    Background task to run orchestrator.
    
    Args:
        job_id: Job identifier
        kb_id: Knowledge base identifier
        kb_config: KB configuration
    """
    import asyncio
    
    orchestrator = IngestionOrchestrator(
        repo=repo,
        workflow=WorkflowDefinition(),
        retry_policy=RetryPolicy(max_attempts=3)
    )
    
    try:
        await orchestrator.run(job_id, kb_id, kb_config)
    except asyncio.CancelledError:
        logger.warning(f"Orchestrator task cancelled for job {job_id} - pausing")
        repo.set_job_status(job_id, status='paused')
        raise
    except Exception as e:
        logger.exception(f"Orchestrator failed for job {job_id}: {e}")
    finally:
        # Remove from tracking
        if job_id in _running_tasks:
            del _running_tasks[job_id]


@router.post("/kb/{kb_id}/start", response_model=JobStatusResponse)
async def start_ingestion(
    kb_id: str,
    kb_manager: KBManager = Depends(get_kb_manager)
):
    """
    Start ingestion for a knowledge base.
    Fetches KB configuration from KBManager (like legacy endpoint).
    
    Args:
        kb_id: Knowledge base identifier
        kb_manager: KB manager to fetch configuration
        
    Returns:
        Job status response
    """
    import asyncio
    
    try:
        # Get KB configuration from manager (like legacy endpoint)
        if not kb_manager.kb_exists(kb_id):
            raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_id}' not found")
        
        kb_config = kb_manager.get_kb_config(kb_id)
        
        # Ensure kb_id is in config (loader expects it)
        kb_config['kb_id'] = kb_id
        
        # Extract source information
        source_type = kb_config.get('source_type', 'unknown')
        source_config = kb_config.get('source_config', {})
        
        # Create job
        job_id = repo.create_job(
            kb_id=kb_id,
            source_type=source_type,
            source_config=source_config,
            priority=0
        )
        
        # Create asyncio task (not BackgroundTasks)
        task = asyncio.create_task(run_orchestrator_background(job_id, kb_id, kb_config))
        task.set_name(f"ingestion-{kb_id}-{job_id}")
        _running_tasks[job_id] = task  # Track by job_id for pause/cancel
        
        logger.info(f"Started ingestion job {job_id} for KB {kb_id} (task: {task.get_name()})")
        
        return JobStatusResponse(
            job_id=job_id,
            kb_id=kb_id,
            status="running",
            started_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.exception(f"Failed to start ingestion for KB {kb_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start ingestion: {e}")


@router.post("/kb/{job_id}/pause")
async def pause_ingestion(job_id: str):
    """
    Pause ingestion job by cancelling the running task.
    This mimics the old threading.Event pattern: signal stop, wait for graceful exit.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Success message
    """
    try:
        # Check if task is running
        task = _running_tasks.get(job_id)
        
        if not task:
            # Task not running, just update database
            repo.update_job(job_id, status="paused")
            logger.info(f"Job {job_id} not running - marked as paused in database")
            return {"status": "paused", "job_id": job_id, "message": "Job was not running"}
        
        # Cancel the task (this will trigger CancelledError in run_orchestrator_background)
        logger.info(f"Cancelling task for job {job_id}")
        task.cancel()
        
        # Wait a moment for graceful shutdown (like old system's thread join)
        try:
            await asyncio.wait_for(task, timeout=5.0)
            logger.info(f"Task for job {job_id} stopped gracefully")
        except asyncio.TimeoutError:
            logger.warning(f"Task for job {job_id} did not stop within 5 seconds")
        except asyncio.CancelledError:
            pass  # Expected
        
        return {"status": "paused", "job_id": job_id, "message": "Job paused successfully"}
        
    except Exception as e:
        logger.exception(f"Failed to pause job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to pause job: {e}")


@router.post("/kb/{job_id}/resume")
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


@router.post("/kb/{job_id}/cancel")
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


@router.get("/kb/{job_id}/status", response_model=JobStatusResponse)
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


async def cleanup_running_tasks():
    """
    Cleanup function to gracefully stop all running ingestion tasks.
    Called during application shutdown.
    """
    import asyncio
    
    logger.warning(f"cleanup_running_tasks called - {len(_running_tasks)} tasks running")
    
    if not _running_tasks:
        logger.warning("No running tasks to clean up")
        return
    
    logger.warning(f"Cancelling {len(_running_tasks)} running ingestion tasks...")
    
    # Request shutdown flag
    from app.ingestion.application.orchestrator import IngestionOrchestrator
    IngestionOrchestrator.request_shutdown()
    
    # Give tasks time to save state gracefully
    logger.warning("Waiting 2 seconds for tasks to save state...")
    await asyncio.sleep(2.0)
    
    # Cancel any tasks that haven't stopped yet
    tasks_cancelled = 0
    for job_id, task in list(_running_tasks.items()):
        if not task.done():
            logger.warning(f"Cancelling task for job {job_id}: {task.get_name()}")
            task.cancel()
            tasks_cancelled += 1
    
    if tasks_cancelled > 0:
        logger.warning(f"Cancelled {tasks_cancelled} tasks that didn't stop gracefully")
    
    # Wait for all tasks to complete
    if _running_tasks:
        logger.warning("Waiting for all tasks to complete...")
        await asyncio.gather(*_running_tasks.values(), return_exceptions=True)
    
    logger.warning("All ingestion tasks stopped")
