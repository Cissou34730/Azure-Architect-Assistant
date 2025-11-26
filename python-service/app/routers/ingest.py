"""
Ingestion Router - Document ingestion endpoints
Handles WAF documentation crawling and indexing (legacy)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import logging
import asyncio
from datetime import datetime

from app.rag.crawler import WAFCrawler
from app.rag.cleaner import WAFIngestionPipeline
from app.rag.indexer import WAFIndexBuilder
from app.services import invalidate_query_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])


# Response Model
class IngestionResponse(BaseModel):
    message: str
    jobId: str


@router.post("/phase1", response_model=IngestionResponse)
async def ingest_phase1():
    """
    Phase 1: Crawl and clean WAF documentation.
    
    This is a long-running operation (~20-30 minutes).
    Returns immediately with a job ID.
    The process runs in the background:
    1. Crawl WAF documentation URLs
    2. Clean and extract content
    3. Export for validation
    """
    try:
        job_id = f"phase1-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        async def run_phase1():
            try:
                logger.info(f"[{job_id}] Starting Phase 1: Crawling WAF documentation")
                
                # Get project root
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
                
                # Crawl WAF documentation
                crawler = WAFCrawler()
                output_file = os.path.join(project_root, "waf_urls.txt")
                crawler.save_urls(output_file)
                
                logger.info(f"[{job_id}] Starting cleaning documents")
                
                # Clean documents
                pipeline = WAFIngestionPipeline()
                documents = pipeline.process_urls_from_file(output_file)
                
                # Export for validation
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


@router.post("/phase2", response_model=IngestionResponse)
async def ingest_phase2():
    """
    Phase 2: Build vector index from approved documents.
    
    This is a long-running operation (~10-15 minutes).
    Returns immediately with a job ID.
    The process runs in the background:
    1. Load approved documents
    2. Chunk and embed
    3. Build vector index
    4. Store for queries
    """
    try:
        job_id = f"phase2-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        async def run_phase2():
            try:
                logger.info(f"[{job_id}] Starting Phase 2: Building index")
                
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
                manifest_file = os.path.join(project_root, "validation_manifest.json")
                
                if not os.path.exists(manifest_file):
                    raise FileNotFoundError(f"Validation manifest not found: {manifest_file}")
                
                # Get storage directory
                storage_dir = os.getenv("WAF_STORAGE_DIR")
                if not storage_dir:
                    storage_dir = os.path.join(project_root, "data", "knowledge_bases", "waf", "index")
                
                # Build index
                builder = WAFIndexBuilder(
                    chunk_size=800,
                    chunk_overlap=120,
                    storage_dir=storage_dir
                )
                
                builder.build_index(manifest_file)
                
                logger.info(f"[{job_id}] Phase 2 completed successfully")
                
                # Invalidate cached service to reload new index
                invalidate_query_service()
                
            except Exception as e:
                logger.error(f"[{job_id}] Phase 2 failed: {str(e)}", exc_info=True)
        
        # Start background task
        asyncio.create_task(run_phase2())
        
        return IngestionResponse(
            message="Phase 2 started: Building vector index from approved documents",
            jobId=job_id
        )
        
    except Exception as e:
        logger.error(f"Failed to start Phase 2: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start Phase 2: {str(e)}")
