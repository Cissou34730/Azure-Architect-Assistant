"""
FastAPI Backend - Full Application Server
Provides multi-source KB query, project management, and architecture workflow.
Migrated from split TypeScript/Python architecture to unified Python backend.
"""

import os
import logging
import warnings
from pathlib import Path
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Suppress third-party Pydantic v2 warnings from dependencies not yet updated
warnings.filterwarnings(
    "ignore",
    message=r"The 'validate_default' attribute with value True was provided to the `Field\(\)` function.*",
    category=UserWarning,
)

# Import routers
from app.routers.kb_query import router as kb_query_router
from app.routers.kb_management import router as kb_management_router
from app.routers.project_management import router as project_router
from app.routers.ingestion import router as ingestion_router
from app.agents_system.agents.router import router as agent_router
from app.routers.diagram_generation import router as diagram_generation_router

# Import lifecycle management
from app import lifecycle
from app.routers.ingestion import cleanup_running_tasks
from app.core.config import get_app_settings
from app.core.logging import configure_logging
from app.core.signals import install_ingestion_signal_handlers
from app.services.diagram.database import close_diagram_database

# Load environment variables from root .env (one level up from backend)
backend_root = Path(__file__).parent.parent
root_dir = backend_root.parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path)

settings = get_app_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)
logger.info(f"Loading environment from: {env_path}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown using FastAPI lifespan."""
    await lifecycle.startup()
    try:
        yield
    finally:
        # Stop running ingestion tasks gracefully
        try:
            await cleanup_running_tasks()
        except Exception as exc:
            logger.exception(f"cleanup_running_tasks failed: {exc}")

        # Cleanup diagram database connections
        try:
            await close_diagram_database()
        except Exception as exc:
            logger.exception(f"close_diagram_database failed: {exc}")

        # Cleanup other resources (includes MCP client shutdown)
        try:
            await lifecycle.shutdown()
        except Exception as exc:
            logger.exception(f"lifecycle.shutdown failed: {exc}")


# Initialize FastAPI app
app = FastAPI(
    title="Azure Architect Assistant - Full Stack Backend",
    description="Unified Python backend for project management, RAG queries, and architecture generation",
    version="3.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


install_ingestion_signal_handlers()


# Include routers
app.include_router(project_router)  # Project management
app.include_router(kb_query_router)  # KB query endpoints
app.include_router(kb_management_router)  # KB health/list endpoints
app.include_router(ingestion_router)  # Orchestrator-based ingestion
app.include_router(agent_router)  # Agent chat endpoints
app.include_router(diagram_generation_router, prefix="/api/v1")  # Diagram generation


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
        version="3.0.0",
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("BACKEND_PORT", "8000"))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
