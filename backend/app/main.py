"""
FastAPI Backend - Full Application Server
Provides multi-source KB query, project management, and architecture workflow.
Migrated from split TypeScript/Python architecture to unified Python backend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Import routers
from app.routers.kb_query import router as kb_query_router
from app.routers.kb_ingestion import router as kb_ingestion_router
from app.routers.kb_management import router as kb_management_router
from app.routers.project_management import router as project_router
from app.database import init_database, close_database# Load environment variables from root .env (one level up from backend)
backend_root = Path(__file__).parent.parent
root_dir = backend_root.parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path)

# Configure logging with timestamps and colors
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    force=True  # Override any existing configuration
)

# Set uvicorn loggers to use our format
for logger_name in ['uvicorn', 'uvicorn.error']:
    uvicorn_logger = logging.getLogger(logger_name)
    uvicorn_logger.setLevel(logging.INFO)

# Keep uvicorn.access with default handler for HTTP request logs
access_logger = logging.getLogger('uvicorn.access')
access_logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger.info(f"Loading environment from: {env_path}")

# Initialize FastAPI app
app = FastAPI(
    title="Azure Architect Assistant - Full Stack Backend",
    description="Unified Python backend for project management, RAG queries, and architecture generation",
    version="3.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event - preload services and initialize database
@app.on_event("startup")
async def startup_event():
    """
    Initialize database and preload high-priority KB indices at startup.
    Uses parallel loading for hot-preload KBs (priority <= 5).
    """
    logger.info("=" * 60)
    logger.info("STARTUP: Initializing database and hot-preloading KBs...")
    logger.info("=" * 60)
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        await init_database()
        logger.info("✓ Database initialized")
        
        from app.service_registry import get_kb_manager, get_multi_query_service
        from app.kb.service import KnowledgeBaseService
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        # Preload KB manager
        logger.info("Loading KB Manager...")
        kb_mgr = get_kb_manager()
        logger.info(f"✓ KB Manager ready ({len(kb_mgr.list_kbs())} knowledge bases)")
        
        # Get high-priority KBs for hot preload (priority <= 5)
        all_kbs = kb_mgr.get_active_kbs()
        hot_preload_kbs = [kb for kb in all_kbs if kb.priority <= 5]
        lazy_load_kbs = [kb for kb in all_kbs if kb.priority > 5]
        
        logger.info(f"Hot preload: {len(hot_preload_kbs)} KBs (priority <= 5)")
        logger.info(f"Lazy load: {len(lazy_load_kbs)} KBs (priority > 5)")
        
        # Parallel preload high-priority KBs
        if hot_preload_kbs:
            logger.info(f"Preloading {len(hot_preload_kbs)} high-priority KBs in parallel...")
            
            def load_kb_index(kb_config):
                """Load a single KB index (blocking operation)."""
                try:
                    logger.info(f"[{kb_config.id}] Loading index...")
                    kb_service = KnowledgeBaseService(kb_config)
                    # Trigger index load by calling _load_index
                    kb_service._load_index()
                    logger.info(f"✓ [{kb_config.id}] Index loaded ({kb_config.name})")
                    return kb_config.id, True
                except Exception as e:
                    logger.error(f"✗ [{kb_config.id}] Failed to load: {e}")
                    return kb_config.id, False
            
            # Use ThreadPoolExecutor for parallel I/O-bound loading
            with ThreadPoolExecutor(max_workers=min(len(hot_preload_kbs), 5)) as executor:
                loop = asyncio.get_event_loop()
                tasks = [
                    loop.run_in_executor(executor, load_kb_index, kb)
                    for kb in hot_preload_kbs
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Log results
                success_count = sum(1 for _, success in results if isinstance(success, bool) and success)
                logger.info(f"✓ Preloaded {success_count}/{len(hot_preload_kbs)} high-priority KBs")
        
        # Initialize multi-source query service (will use cached indexes)
        logger.info("Initializing Multi-Source Query Service...")
        multi_service = get_multi_query_service()
        logger.info("✓ Multi-Source Query Service ready")

        # Load persisted ingestion states
        try:
            from app.ingestion.service import IngestionService
            ingest_service = IngestionService.instance()
            ingest_service.load_all_states()
            logger.info("✓ Loaded persisted ingestion job states")
            # Backfill snapshots from current JobManager if any jobs exist
            ingest_service.backfill_from_job_manager()
            logger.info("✓ Backfilled snapshots from JobManager")
        except Exception as e:
            logger.warning(f"Failed to load ingestion states: {e}")
        
        logger.info("=" * 60)
        logger.info("STARTUP COMPLETE: Database and hot-preload KBs ready!")
        if lazy_load_kbs:
            logger.info(f"Note: {len(lazy_load_kbs)} KBs will be lazy-loaded on first use")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        logger.warning("Some services may be lazy-loaded on first request")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown - cancel running ingestion jobs."""
    logger.info("=" * 60)
    logger.info("SHUTDOWN: Cancelling running ingestion jobs...")
    logger.info("=" * 60)
    
    # Cancel any running ingestion jobs
    try:
        from app.kb.ingestion.job_manager import get_job_manager
        import asyncio
        
        job_manager = get_job_manager()
        running_jobs = [job for job in job_manager.get_all_jobs() 
                       if job.status.value in ['running', 'pending']]
        
        if running_jobs:
            logger.info(f"Found {len(running_jobs)} active ingestion jobs")
            for job in running_jobs:
                logger.info(f"  Cancelling job {job.job_id} for KB {job.kb_id}...")
                job.cancel()
                
                # If the job has an asyncio task, cancel it
                if job._task and not job._task.done():
                    job._task.cancel()
                    try:
                        await asyncio.wait_for(job._task, timeout=2.0)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass
                
                logger.info(f"  ✓ Cancelled job {job.job_id}")
            
            logger.info(f"✓ All {len(running_jobs)} jobs cancelled")
        else:
            logger.info("No active jobs to cancel")
    except Exception as e:
        logger.warning(f"Error cancelling jobs during shutdown: {e}")
    
    # Cancel asyncio-based ingestion tasks
    try:
        from app.ingestion.service import IngestionService
        ingest_service = IngestionService.instance()
        await ingest_service.cancel_all()
    except Exception as e:
        logger.warning(f"Error cancelling asyncio ingestion tasks: {e}")

    await close_database()
    logger.info("=" * 60)
    logger.info("SHUTDOWN COMPLETE")
    logger.info("=" * 60)


# Include routers
app.include_router(project_router)             # Project management
app.include_router(kb_query_router)            # KB query endpoints
app.include_router(kb_management_router)       # KB health/list endpoints
app.include_router(kb_ingestion_router)        # Generic KB ingestion


# Health check
class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Service health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="Azure Architect Assistant - Full Stack Backend",
        version="3.0.0"
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PYTHON_PORT", "8000"))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

