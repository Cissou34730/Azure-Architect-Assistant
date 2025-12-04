"""
Generic Ingestion Router - Multi-source KB ingestion endpoints
Handles KB creation, job management, and progress tracking
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import logging
from datetime import datetime

from app.kb.ingestion.job_manager import get_job_manager, JobStatus, IngestionPhase
from app.kb.ingestion.sources.web_documentation import WebDocumentationCrawler
from app.kb.ingestion.sources.web_generic import GenericWebCrawler
from app.kb.ingestion.sources.web_cleaner import WebContentCleaner
from app.kb.ingestion.sources.web_indexer import GenericIndexBuilder
from app.kb.ingestion.base import IngestionPipeline
from app.kb.knowledge_base_manager import KBManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingestion", tags=["kb-ingestion"])


# ============================================================================
# Request/Response Models
# ============================================================================

class SourceType(str, Enum):
    """Document source types"""
    WEB_DOCUMENTATION = "web_documentation"
    WEB_GENERIC = "web_generic"
    LOCAL_FILES = "local_files"


class WebDocumentationConfig(BaseModel):
    """Configuration for structured documentation crawler"""
    start_urls: List[HttpUrl]
    allowed_domains: Optional[List[str]] = None
    path_prefix: Optional[str] = None
    follow_links: bool = True
    max_pages: int = 1000


class WebGenericConfig(BaseModel):
    """Configuration for generic web crawler"""
    urls: List[HttpUrl]
    follow_links: bool = False
    max_depth: int = 1
    same_domain_only: bool = True


class CreateKBRequest(BaseModel):
    """Request to create a new knowledge base"""
    kb_id: str = Field(..., description="Unique KB identifier")
    name: str = Field(..., description="Human-readable KB name")
    description: Optional[str] = Field(None, description="KB description")
    source_type: SourceType = Field(..., description="Type of document source")
    source_config: Dict[str, Any] = Field(..., description="Source-specific configuration")
    embedding_model: str = Field(default="text-embedding-3-small", description="OpenAI embedding model")
    chunk_size: int = Field(default=800, description="Chunk size for indexing")
    chunk_overlap: int = Field(default=120, description="Chunk overlap for indexing")
    profiles: Optional[List[str]] = Field(default=["chat", "kb-query"], description="Query profiles")
    priority: int = Field(default=1, description="KB priority for multi-query")


class StartIngestionRequest(BaseModel):
    """Request to start ingestion for a KB"""
    kb_id: str = Field(..., description="KB identifier")


class JobStatusResponse(BaseModel):
    """Job status information"""
    job_id: str
    kb_id: str
    status: JobStatus
    phase: IngestionPhase
    progress: float
    message: str
    error: Optional[str] = None
    metrics: Dict[str, Any]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobListResponse(BaseModel):
    """List of all jobs"""
    jobs: List[JobStatusResponse]


class CreateKBResponse(BaseModel):
    """Response after KB creation"""
    message: str
    kb_id: str
    kb_name: str


class StartIngestionResponse(BaseModel):
    """Response after starting ingestion"""
    message: str
    job_id: str
    kb_id: str


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/kb/create", response_model=CreateKBResponse)
async def create_kb(request: CreateKBRequest):
    """
    Create a new knowledge base configuration.
    
    This endpoint:
    1. Validates KB ID uniqueness
    2. Creates KB directory structure
    3. Saves KB configuration to config.json
    4. Does NOT start ingestion (use /kb/{kb_id}/start for that)
    """
    try:
        kb_manager = KBManager()
        
        # Check if KB already exists
        if kb_manager.kb_exists(request.kb_id):
            raise HTTPException(
                status_code=400,
                detail=f"KB '{request.kb_id}' already exists"
            )
        
        # Create KB configuration
        kb_config = {
            "id": request.kb_id,
            "name": request.name,
            "description": request.description or "",
            "source_type": request.source_type,
            "source_config": request.source_config,
            "embedding_model": request.embedding_model,
            "chunk_size": request.chunk_size,
            "chunk_overlap": request.chunk_overlap,
            "profiles": request.profiles or ["chat", "kb-query"],
            "priority": request.priority,
            "created_at": datetime.now().isoformat(),
            "indexed": False
        }
        
        # Save KB configuration
        kb_manager.create_kb(request.kb_id, kb_config)
        
        logger.info(f"Created KB: {request.kb_id} ({request.name})")
        
        return CreateKBResponse(
            message=f"Knowledge base '{request.name}' created successfully",
            kb_id=request.kb_id,
            kb_name=request.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create KB: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create KB: {str(e)}")


@router.post("/kb/{kb_id}/start", response_model=StartIngestionResponse)
async def start_ingestion(kb_id: str, background_tasks: BackgroundTasks):
    """
    Start ingestion job for a knowledge base.
    
    This endpoint:
    1. Validates KB exists
    2. Creates ingestion job
    3. Starts background ingestion process
    4. Returns immediately with job ID
    
    The ingestion process runs asynchronously:
    1. Crawl documents from source
    2. Clean and extract content
    3. Build vector index
    4. Update KB configuration
    """
    try:
        kb_manager = KBManager()
        
        # Check if KB exists
        if not kb_manager.kb_exists(kb_id):
            raise HTTPException(
                status_code=404,
                detail=f"KB '{kb_id}' not found"
            )
        
        # Get KB configuration
        kb_config = kb_manager.get_kb_config(kb_id)
        
        # Create job
        job_manager = get_job_manager()
        source_type = kb_config.get("source_type", "unknown")
        job = job_manager.create_job(kb_id, kb_config["name"], source_type)
        
        # Start background ingestion
        background_tasks.add_task(_run_ingestion, job.job_id, kb_id, kb_config)
        
        logger.info(f"Started ingestion job {job.job_id} for KB: {kb_id}")
        
        return StartIngestionResponse(
            message=f"Ingestion started for KB '{kb_config['name']}'",
            job_id=job.job_id,
            kb_id=kb_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start ingestion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start ingestion: {str(e)}")


@router.get("/kb/{kb_id}/status", response_model=JobStatusResponse)
async def get_kb_status(kb_id: str):
    """
    Get the latest job status for a knowledge base.
    
    Returns:
    - Latest job for this KB
    - If no job found, returns 404
    """
    try:
        job_manager = get_job_manager()
        
        # Get latest job for this KB
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
        logger.error(f"Failed to get KB status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get KB status: {str(e)}")


@router.post("/kb/{kb_id}/cancel")
async def cancel_ingestion(kb_id: str):
    """
    Cancel the running ingestion job for a knowledge base.
    
    Note: Cancellation is cooperative. The job will stop at the next checkpoint.
    """
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
        import asyncio
        from app.kb.service import clear_index_cache
        
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
        if kb_config:
            storage_dir = kb_config.index_path
        else:
            storage_dir = None
        
        # Cancel any running jobs
        job = job_manager.get_latest_job_for_kb(kb_id)
        if job and job.status == JobStatus.RUNNING:
            job_manager.cancel_job(job.job_id)
            logger.info(f"Cancelled running job {job.job_id} before deleting KB: {kb_id}")
            # Wait a moment for job to clean up and release file handles
            await asyncio.sleep(1.0)
        
        # Clear index from memory cache to release file handles
        if storage_dir:
            clear_index_cache(kb_id=kb_id, storage_dir=storage_dir)
            logger.info(f"Cleared index cache for KB: {kb_id}")
            # Give OS time to release file handles
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


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(kb_id: Optional[str] = None, limit: int = 50):
    """
    List all ingestion jobs, optionally filtered by KB.
    
    Args:
        kb_id: Filter jobs by KB ID (optional)
        limit: Maximum number of jobs to return (default: 50)
    """
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


# ============================================================================
# Background Job Execution
# ============================================================================

async def _run_ingestion(job_id: str, kb_id: str, kb_config: Dict[str, Any]):
    """
    Background task to run the ingestion pipeline.
    
    This function:
    1. Creates the appropriate crawler, cleaner, and indexer
    2. Runs the ingestion pipeline
    3. Updates job status via callbacks
    4. Handles errors and updates KB configuration
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    job_manager = get_job_manager()
    kb_manager = KBManager()
    
    try:
        logger.info(f"=" * 80)
        logger.info(f"STARTING INGESTION JOB: {job_id}")
        logger.info(f"KB ID: {kb_id}")
        logger.info(f"=" * 80)
        
        # Create progress callback
        def progress_callback(phase: IngestionPhase, progress: float, message: str, metrics: Optional[Dict[str, Any]] = None):
            logger.info(f"Progress: [{phase.value}] {progress}% - {message}")
            job = job_manager.get_job(job_id)
            if job:
                job.update_progress(phase, int(progress), message, metrics)
        
        # Get source type and config
        source_type = kb_config["source_type"]
        source_config = kb_config["source_config"]
        
        # Create crawler based on source type
        logger.info(f"Creating crawler for KB {kb_id} with source type: {source_type}")
        logger.info(f"Source config: {source_config}")
        
        if source_type == SourceType.WEB_DOCUMENTATION:
            crawler = WebDocumentationCrawler(
                kb_id=kb_id,
                config=source_config
            )
        elif source_type == SourceType.WEB_GENERIC:
            crawler = GenericWebCrawler(
                kb_id=kb_id,
                config=source_config
            )
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
        
        # Create cleaner
        logger.info("Creating content cleaner...")
        cleaner = WebContentCleaner(kb_id=kb_id)
        
        # Create indexer
        logger.info("Creating index builder...")
        indexer = GenericIndexBuilder(kb_config=kb_config)
        
        # Create and run pipeline
        logger.info(f"Creating ingestion pipeline for KB {kb_id}")
        pipeline = IngestionPipeline(
            crawler=crawler,
            cleaner=cleaner,
            indexer=indexer
        )
        
        # Run synchronous pipeline in thread pool to avoid blocking
        logger.info(f"Starting pipeline execution for job {job_id}")
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(
                executor,
                pipeline.run,
                progress_callback
            )
        logger.info(f"Pipeline execution completed for job {job_id}")
        logger.info(f"Result: {result}")
        
        # Update KB configuration
        kb_config["indexed"] = True
        kb_config["last_indexed_at"] = datetime.now().isoformat()
        kb_manager.update_kb_config(kb_id, kb_config)
        
        # Mark job as completed
        job = job_manager.get_job(job_id)
        if job:
            job.complete(metrics=result.get('metrics', {}))
        
        logger.info(f"Ingestion job {job_id} completed successfully for KB: {kb_id}")
        
    except Exception as e:
        logger.error(f"Ingestion job {job_id} failed: {str(e)}", exc_info=True)
        job = job_manager.get_job(job_id)
        if job:
            job.fail(str(e))
