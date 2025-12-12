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
        
        # Clear any stale shutdown flag
        IngestionOrchestrator.clear_shutdown_flag()
        
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


@router.post("/kb/{kb_id}/pause")
async def pause_ingestion(kb_id: str):
    """
    Pause ingestion job for a KB by cancelling the running task.
    This mimics the old threading.Event pattern: signal stop, wait for graceful exit.
    
    Args:
        kb_id: Knowledge base identifier
        
    Returns:
        Success message
    """
    try:
        # Get latest job for this KB
        job_id = repo.get_latest_job_id(kb_id)
        if not job_id:
            raise HTTPException(status_code=404, detail=f"No job found for KB '{kb_id}'")
        
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
        
        return {"status": "paused", "job_id": job_id, "kb_id": kb_id, "message": "Job paused successfully"}
        
    except Exception as e:
        logger.exception(f"Failed to pause job for KB {kb_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to pause job: {e}")


@router.post("/kb/{kb_id}/resume")
async def resume_ingestion(
    kb_id: str,
    kb_manager: KBManager = Depends(get_kb_manager)
):
    """
    Resume paused ingestion job for a KB.
    Restarts the orchestrator from the saved checkpoint.
    
    Args:
        kb_id: Knowledge base identifier
        kb_manager: KB manager to fetch configuration
        
    Returns:
        Success message
    """
    import asyncio
    
    try:
        # Get latest job for this KB
        job_id = repo.get_latest_job_id(kb_id)
        if not job_id:
            raise HTTPException(status_code=404, detail=f"No job found for KB '{kb_id}'")
        
        # Get job details
        job = repo.get_job(job_id)
        
        # Verify job is paused
        status = repo.get_job_status(job_id)
        if status != 'paused':
            logger.warning(f"Attempted to resume job {job_id} but status is {status}, not paused")
            return {"status": status, "job_id": job_id, "kb_id": kb_id, "message": f"Job is {status}, not paused"}
        
        # Check if task already running
        if job_id in _running_tasks:
            logger.warning(f"Job {job_id} already has a running task")
            return {"status": "running", "job_id": job_id, "kb_id": kb_id, "message": "Job already running"}
        
        # Get KB configuration
        if not kb_manager.kb_exists(kb_id):
            raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_id}' not found")
        
        kb_config = kb_manager.get_kb_config(kb_id)
        kb_config['kb_id'] = kb_id
        
        # Clear any stale shutdown flag before resuming
        IngestionOrchestrator.clear_shutdown_flag()
        
        # Update status to running
        repo.update_job(job_id, status="running")
        
        # Restart orchestrator task from checkpoint
        task = asyncio.create_task(run_orchestrator_background(job_id, kb_id, kb_config))
        task.set_name(f"ingestion-{kb_id}-{job_id}-resumed")
        _running_tasks[job_id] = task
        
        logger.info(f"✅ Resumed job {job_id} for KB {kb_id} (task: {task.get_name()})")
        return {"status": "running", "job_id": job_id, "kb_id": kb_id, "message": "Job resumed successfully"}
        
    except Exception as e:
        logger.exception(f"Failed to resume job for KB {kb_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resume job: {e}")


@router.post("/kb/{kb_id}/cancel")
async def cancel_ingestion(kb_id: str):
    """
    Cancel ingestion job for a KB and trigger cleanup.
    
    Args:
        kb_id: Knowledge base identifier
        
    Returns:
        Success message
        
    Note:
        Cleanup (delete vectors, reset state) happens in orchestrator on next gate check.
    """
    try:
        # Get latest job for this KB
        job_id = repo.get_latest_job_id(kb_id)
        if not job_id:
            raise HTTPException(status_code=404, detail=f"No job found for KB '{kb_id}'")
        
        repo.update_job(job_id, status="canceled")
        logger.info(f"Canceled job {job_id} for KB {kb_id}")
        return {"status": "canceled", "job_id": job_id, "kb_id": kb_id}
    except Exception as e:
        logger.exception(f"Failed to cancel job for KB {kb_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {e}")
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


@router.get("/kb/{kb_id}/details")
async def get_kb_ingestion_details(kb_id: str):
    """
    Get detailed ingestion status for a KB including phase details.
    This endpoint provides comprehensive status information for the frontend.
    
    Args:
        kb_id: Knowledge base identifier
        
    Returns:
        Detailed ingestion status with phase breakdown
    """
    from app.ingestion.application.status_query_service import StatusQueryService
    
    try:
        status_service = StatusQueryService()
        status = status_service.get_status(kb_id)
        
        # Get job counters if available
        try:
            job_id = repo.get_latest_job_id(kb_id)
            if job_id:
                job = repo.get_job(job_id)
                counters = job.counters
            else:
                counters = {}
        except Exception:
            counters = {}
        
        return {
            "kb_id": kb_id,
            "status": status.status,
            "current_phase": status.current_phase,
            "overall_progress": status.overall_progress,
            "phase_details": status.phase_details,
            "counters": counters
        }
    except Exception as e:
        logger.exception(f"Failed to get ingestion details for KB {kb_id}: {e}")
        raise HTTPException(status_code=404, detail=f"KB details not found: {kb_id}")


async def cleanup_running_tasks():
    """
    Cleanup function to gracefully stop all running ingestion tasks.
    Called during application shutdown.
    """
    import asyncio

    logger.warning("=" * 80)
    logger.warning(f"cleanup_running_tasks CALLED - {len(_running_tasks)} tasks running")
    logger.warning(f"Task job_ids: {list(_running_tasks.keys())}")
    logger.warning("=" * 80)

    if not _running_tasks:
        logger.warning("No running tasks to clean up")
        return

    # Snapshot tasks to avoid race conditions while we manipulate the dict
    tasks_snapshot = list(_running_tasks.items())

    logger.warning("Step 1: Setting shutdown flag on orchestrators...")
    from app.ingestion.application.orchestrator import IngestionOrchestrator
    IngestionOrchestrator.request_shutdown()

    # Proactively mark jobs as paused so they can be resumed even if tasks ignore cancellation
    logger.warning("Step 1b: Marking jobs as paused in the repository...")
    for job_id, _ in tasks_snapshot:
        try:
            repo.set_job_status(job_id, status="paused")
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(f"Could not mark job {job_id} as paused: {exc}")

    # Give tasks time to checkpoint on their own before we cancel them
    logger.warning("Step 2: Waiting 2 seconds for tasks to checkpoint gracefully...")
    await asyncio.sleep(2.0)

    # Cancel any tasks that haven't stopped yet
    logger.warning("Step 3: Cancelling tasks that are still running...")
    pending = []
    for job_id, task in tasks_snapshot:
        if task.done():
            logger.warning(f"  Task for job {job_id} already finished")
            _running_tasks.pop(job_id, None)
            continue

        logger.warning(f"  Cancelling task for job {job_id}: {task.get_name()}")
        task.cancel()
        pending.append((job_id, task))

    if pending:
        logger.warning(f"Step 4: Waiting for up to 5 seconds for {len(pending)} task(s) to stop...")
        done, still_running = await asyncio.wait(
            [t for _, t in pending],
            timeout=5.0,
            return_when=asyncio.ALL_COMPLETED,
        )

        for job_id, task in pending:
            if task in done:
                _running_tasks.pop(job_id, None)
                logger.warning(f"  Task for job {job_id} stopped")
        if still_running:
            hanging = [t.get_name() for t in still_running]
            logger.warning(f"  Tasks still running after timeout: {hanging} - allowing shutdown to continue")
    else:
        logger.warning("Step 4: All tasks stopped gracefully")

    logger.warning("=" * 80)
    logger.warning("cleanup_running_tasks COMPLETE - All ingestion tasks stopped (or marked paused)")
    logger.warning("=" * 80)
