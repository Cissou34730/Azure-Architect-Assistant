"""
FastAPI Backend - Full Application Server
Provides multi-source KB query, project management, and architecture workflow.
Migrated from split TypeScript/Python architecture to unified Python backend.
"""

import logging
import warnings
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import lifecycle management
from app import lifecycle
from app.agents_system.agents.router import router as agent_router
from app.core.app_logging import configure_logging
from app.core.app_settings import get_app_settings
from app.core.signals import install_ingestion_signal_handlers

# Import routers
from app.routers.checklists.checklist_router import router as checklist_router
from app.routers.diagram_generation import router as diagram_generation_router
from app.routers.ingestion import cleanup_running_tasks
from app.routers.ingestion import router as ingestion_router
from app.routers.kb_management import router as kb_management_router
from app.routers.kb_query import router as kb_query_router
from app.routers.project_management import router as project_router
from app.services.diagram.database import close_diagram_database

# Suppress third-party Pydantic v2 warnings from dependencies not yet updated
warnings.filterwarnings(
    "ignore",
    message=r"The 'validate_default' attribute with value True was provided to the `Field\(\)` function.*",
    category=UserWarning,
)

settings = get_app_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)
logger.info("Loaded application settings via get_app_settings()")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown using FastAPI lifespan."""
    await lifecycle.startup()
    try:
        yield
    finally:
        # Graceful cleanup of resources
        cleanup_actions = [
            ("running ingestion tasks", cleanup_running_tasks),
            ("diagram database connections", close_diagram_database),
            ("general lifecycle resources", lifecycle.shutdown),
        ]
        for description, func in cleanup_actions:
            try:
                await func()
            except Exception as exc:
                logger.exception(f"Cleanup of {description} failed: {exc}")


# Initialize FastAPI app
app = FastAPI(
    title="Azure Architect Assistant - Full Stack Backend",
    description="Unified Python backend for project management, RAG queries, and architecture generation",
    version=settings.app_version,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Ideally restricted in production
    allow_headers=["*"],  # Ideally restricted in production
)

install_ingestion_signal_handlers()

# Include routers
app.include_router(project_router)  # Project management
app.include_router(kb_query_router)  # KB query endpoints
app.include_router(kb_management_router)  # KB health/list endpoints
app.include_router(ingestion_router)  # Orchestrator-based ingestion
app.include_router(agent_router)  # Agent chat endpoints
app.include_router(checklist_router)  # New normalized checklists
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
        version=settings.app_version,
    )


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {settings.backend_host}:{settings.backend_port}")
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )

