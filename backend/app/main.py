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
from app.routers.ingestion_v2 import router as ingestion_v2_router

# Import lifecycle management
from app import lifecycle
from app.ingestion.application.orchestrator import IngestionOrchestrator
from app.routers.ingestion_v2 import cleanup_running_tasks# Load environment variables from root .env (one level up from backend)
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

# Suppress verbose HTTP client logs (OpenAI, httpx, urllib3)
for noisy_logger in ['httpx', 'openai', 'urllib3', 'httpcore']:
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

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


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize application services"""
    await lifecycle.startup()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup application resources - called on CTRL-C or server shutdown"""
    logger.warning("Server shutting down - requesting graceful pause of all ingestion jobs")
    
    # Stop running ingestion tasks gracefully
    await cleanup_running_tasks()
    
    # Cleanup other resources
    await lifecycle.shutdown()


# Include routers
app.include_router(project_router)             # Project management
app.include_router(kb_query_router)            # KB query endpoints
app.include_router(kb_management_router)       # KB health/list endpoints
# app.include_router(kb_ingestion_router)      # Legacy KB ingestion (DEPRECATED - use ingestion_v2)
app.include_router(ingestion_v2_router)        # Orchestrator-based ingestion (v2)


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
    port = int(os.getenv("BACKEND_PORT", "8000"))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

