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
from app.routers import query, kb, ingest, projects
from app.database import init_database, close_database

# Load environment variables from root .env
root_dir = Path(__file__).parent.parent.parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path)
logger_init = logging.getLogger(__name__)
logger_init.info(f"Loading environment from: {env_path}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        
        from app.services import get_kb_manager, get_multi_query_service
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
    """Cleanup on shutdown."""
    logger.info("Shutting down...")
    await close_database()
    logger.info("Shutdown complete")


# Include routers
app.include_router(projects.router)  # Project management endpoints
app.include_router(query.router)     # KB query endpoints
app.include_router(kb.router)        # KB health/list endpoints
app.include_router(ingest.router)    # KB ingestion endpoints


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

