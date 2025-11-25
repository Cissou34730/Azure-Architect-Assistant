"""
FastAPI Backend for RAG (LlamaIndex + OpenAI)
Provides multi-source knowledge base query and ingestion endpoints with profile-based selection.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Import routers
from app.routers import query, kb, ingest

# Load environment variables from root .env (shared with Express backend)
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
    title="Azure Architect Assistant - RAG Service",
    description="Multi-source RAG service for architecture guidance using LlamaIndex",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event - preload services and indices
@app.on_event("startup")
async def startup_event():
    """
    Preload services and indices at startup for fast first queries.
    This ensures that LlamaIndex loads into memory before any API requests.
    """
    logger.info("=" * 60)
    logger.info("STARTUP: Preloading services and indices...")
    logger.info("=" * 60)
    
    try:
        from app.services import get_query_service, get_kb_manager, get_multi_query_service
        
        # Preload WAF query service (loads index into memory)
        logger.info("Preloading WAF Query Service...")
        waf_service = get_query_service()
        logger.info("✓ WAF Query Service ready")
        
        # Preload KB manager
        logger.info("Preloading KB Manager...")
        kb_mgr = get_kb_manager()
        logger.info(f"✓ KB Manager ready ({len(kb_mgr.list_kbs())} knowledge bases)")
        
        # Preload multi-source query service
        logger.info("Preloading Multi-Source Query Service...")
        multi_service = get_multi_query_service()
        logger.info("✓ Multi-Source Query Service ready")
        
        logger.info("=" * 60)
        logger.info("STARTUP COMPLETE: All services preloaded and ready!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error during startup preload: {e}")
        logger.warning("Services will be lazy-loaded on first request")


# Include routers
app.include_router(query.router)
app.include_router(kb.router)
app.include_router(ingest.router)


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
        service="Azure Architect Assistant - RAG Service",
        version="2.0.0"
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PYTHON_PORT", "8000"))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

