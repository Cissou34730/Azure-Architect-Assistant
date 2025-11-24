"""
FastAPI Backend for RAG (LlamaIndex + OpenAI)
Provides WAF documentation query and ingestion endpoints.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

from app.rag.query import WAFQueryService
from app.rag.crawler import WAFCrawler
from app.rag.cleaner import WAFIngestionPipeline
from app.rag.indexer import WAFIndexBuilder

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
    description="RAG service for WAF documentation queries using LlamaIndex",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global service instance (lazy loaded)
_query_service: Optional[WAFQueryService] = None

def get_query_service() -> WAFQueryService:
    """Get or create WAFQueryService instance (singleton pattern)."""
    global _query_service
    if _query_service is None:
        storage_dir = os.getenv("WAF_STORAGE_DIR")
        if not storage_dir:
            # Default path relative to project root
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            storage_dir = os.path.join(project_root, "data", "knowledge_bases", "waf", "index")
        
        logger.info(f"Initializing WAFQueryService with storage_dir: {storage_dir}")
        _query_service = WAFQueryService(
            storage_dir=storage_dir,
            embedding_model="text-embedding-3-small",
            llm_model="gpt-4o-mini"
        )
        
        # Pre-load index
        try:
            _query_service._load_index()
            logger.info("Index pre-loaded successfully")
        except Exception as e:
            logger.warning(f"Could not pre-load index: {e}")
    
    return _query_service


# Request/Response Models
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question to ask about WAF documentation")
    topK: Optional[int] = Field(5, ge=1, le=20, description="Number of relevant chunks to retrieve")
    metadataFilters: Optional[Dict[str, Any]] = Field(None, description="Optional metadata filters")


class SourceInfo(BaseModel):
    url: str
    title: str
    section: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceInfo]
    hasResults: bool
    suggestedFollowUps: Optional[List[str]] = None


class HealthResponse(BaseModel):
    status: str
    index_ready: bool
    storage_dir: str


class IngestionRequest(BaseModel):
    phase: int = Field(..., ge=1, le=2, description="Ingestion phase (1 or 2)")


class IngestionResponse(BaseModel):
    message: str
    jobId: str


# API Endpoints

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint - API information."""
    return {
        "service": "Azure Architect Assistant - RAG Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    storage_dir = os.getenv("WAF_STORAGE_DIR", "")
    if not storage_dir:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        storage_dir = os.path.join(project_root, "data", "knowledge_bases", "waf", "index")
    
    index_ready = os.path.exists(storage_dir) and os.path.exists(os.path.join(storage_dir, "docstore.json"))
    
    return HealthResponse(
        status="healthy",
        index_ready=index_ready,
        storage_dir=storage_dir
    )


@app.post("/query", response_model=QueryResponse)
async def query_waf(request: QueryRequest):
    """
    Query WAF documentation using RAG.
    
    Returns answer with sources and suggested follow-up questions.
    """
    try:
        logger.info(f"Query request received: {request.question[:100]}")
        
        service = get_query_service()
        
        result = service.query(
            question=request.question,
            top_k=request.topK or 5,
            metadata_filters=request.metadataFilters
        )
        
        # Convert to response model
        sources = [
            SourceInfo(
                url=source['url'],
                title=source['title'],
                section=source['section'],
                score=source['score']
            )
            for source in result.get('sources', [])
        ]
        
        return QueryResponse(
            answer=result['answer'],
            sources=sources,
            hasResults=result.get('has_results', True),
            suggestedFollowUps=result.get('suggested_follow_ups')
        )
        
    except Exception as e:
        logger.error(f"Query failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.post("/ingest/phase1", response_model=IngestionResponse)
async def ingest_phase1():
    """
    Phase 1: Crawl and clean WAF documentation.
    
    This is a long-running operation (~5-10 minutes).
    Returns immediately with a job ID. Check status separately.
    """
    try:
        import asyncio
        from datetime import datetime
        
        job_id = f"phase1-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Run in background (in production, use Celery/RQ)
        async def run_phase1():
            try:
                logger.info(f"[{job_id}] Starting Phase 1: Crawling")
                crawler = WAFCrawler(
                    start_url="https://learn.microsoft.com/en-us/azure/well-architected/",
                    max_depth=3,
                    max_pages=500
                )
                urls = crawler.crawl()
                
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                output_file = os.path.join(project_root, "waf_urls.txt")
                crawler.save_urls(output_file)
                
                logger.info(f"[{job_id}] Starting Phase 1: Cleaning documents")
                pipeline = WAFIngestionPipeline()
                documents = pipeline.process_urls_from_file(output_file)
                
                output_dir = os.path.join(project_root, "cleaned_documents")
                manifest_file = os.path.join(project_root, "validation_manifest.json")
                pipeline.export_for_validation(documents, output_dir, manifest_file)
                
                logger.info(f"[{job_id}] Phase 1 completed successfully")
            except Exception as e:
                logger.error(f"[{job_id}] Phase 1 failed: {str(e)}", exc_info=True)
        
        # Start background task
        asyncio.create_task(run_phase1())
        
        return IngestionResponse(
            message="Phase 1 started: Crawling and cleaning WAF documentation",
            jobId=job_id
        )
        
    except Exception as e:
        logger.error(f"Failed to start Phase 1: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start ingestion: {str(e)}")


@app.post("/ingest/phase2", response_model=IngestionResponse)
async def ingest_phase2():
    """
    Phase 2: Build vector index from approved documents.
    
    This is a long-running operation (~10-15 minutes).
    Returns immediately with a job ID.
    """
    try:
        import asyncio
        from datetime import datetime
        
        job_id = f"phase2-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        async def run_phase2():
            try:
                logger.info(f"[{job_id}] Starting Phase 2: Building index")
                
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                manifest_file = os.path.join(project_root, "validation_manifest.json")
                
                if not os.path.exists(manifest_file):
                    raise FileNotFoundError(f"Validation manifest not found: {manifest_file}")
                
                storage_dir = os.getenv("WAF_STORAGE_DIR")
                if not storage_dir:
                    storage_dir = os.path.join(project_root, "data", "knowledge_bases", "waf", "index")
                
                builder = WAFIndexBuilder(
                    chunk_size=800,
                    chunk_overlap=120,
                    storage_dir=storage_dir
                )
                
                builder.build_index(manifest_file)
                
                logger.info(f"[{job_id}] Phase 2 completed successfully")
                
                # Invalidate cached service to reload new index
                global _query_service
                _query_service = None
                
            except Exception as e:
                logger.error(f"[{job_id}] Phase 2 failed: {str(e)}", exc_info=True)
        
        asyncio.create_task(run_phase2())
        
        return IngestionResponse(
            message="Phase 2 started: Building vector index from approved documents",
            jobId=job_id
        )
        
    except Exception as e:
        logger.error(f"Failed to start Phase 2: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start Phase 2: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PYTHON_PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
