"""
Business Logic for KB Ingestion Operations
Separated from routing layer for better maintainability
"""

import logging
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.service_registry import get_kb_manager
from app.kb.ingestion.job_manager import get_job_manager, IngestionJob, IngestionPhase
from app.kb.ingestion.sources.web_documentation import WebDocumentationCrawler
from app.kb.ingestion.sources.web_generic import GenericWebCrawler
from app.kb.ingestion.sources.web_cleaner import WebContentCleaner
from app.kb.ingestion.sources.web_indexer import GenericIndexBuilder
from app.kb.ingestion.base import IngestionPipeline

from .models import SourceType, CreateKBRequest

logger = logging.getLogger(__name__)


class KBIngestionService:
    """Service layer for KB ingestion operations"""
    
    def __init__(self):
        self.kb_manager = get_kb_manager()
        self.job_manager = get_job_manager()
    
    def create_knowledge_base(self, request: CreateKBRequest) -> Dict[str, str]:
        """
        Create a new knowledge base.
        
        Args:
            request: KB creation request
            
        Returns:
            Dict with kb_id, kb_name, message
            
        Raises:
            ValueError: If KB already exists or validation fails
        """
        # Check if KB already exists
        if self.kb_manager.kb_exists(request.kb_id):
            raise ValueError(f"Knowledge base '{request.kb_id}' already exists")
        
        # Build KB configuration
        kb_config = {
            'id': request.kb_id,
            'name': request.name,
            'description': request.description or '',
            'status': 'active',
            'source_type': request.source_type.value,
            'source_config': request.source_config,
            'embedding_model': request.embedding_model,
            'chunk_size': request.chunk_size,
            'chunk_overlap': request.chunk_overlap,
            'profiles': request.profiles or ['chat', 'kb-query'],
            'priority': request.priority,
            'indexed': False
        }
        
        # Create KB
        self.kb_manager.create_kb(request.kb_id, kb_config)
        
        logger.info(f"Created KB: {request.kb_id} ({request.name})")
        
        return {
            "message": f"Knowledge base '{request.name}' created successfully",
            "kb_id": request.kb_id,
            "kb_name": request.name
        }
    
    def start_ingestion(self, kb_id: str) -> Dict[str, str]:
        """
        Start ingestion for a knowledge base.
        
        Args:
            kb_id: Knowledge base identifier
            
        Returns:
            Dict with job_id, kb_id, message
            
        Raises:
            ValueError: If KB not found or job already running
        """
        # Check if KB exists
        if not self.kb_manager.kb_exists(kb_id):
            raise ValueError(f"Knowledge base '{kb_id}' not found")
        
        # Check if job already running
        existing_job = self.job_manager.get_latest_job_for_kb(kb_id)
        if existing_job and existing_job.status.value == 'running':
            raise ValueError(f"Ingestion already running for KB '{kb_id}'")
        
        # Get KB configuration
        kb_config = self.kb_manager.get_kb_config(kb_id)
        kb_name = kb_config.get('name', kb_id)
        source_type = kb_config.get('source_type', 'web_generic')
        
        # Create and start job
        job = self.job_manager.create_job(kb_id, kb_name, source_type)
        
        logger.info(f"Starting ingestion job {job.job_id} for KB: {kb_id}")
        
        return {
            "message": f"Ingestion started for '{kb_name}'",
            "job_id": job.job_id,
            "kb_id": kb_id
        }
    
    def run_ingestion_pipeline(self, job: IngestionJob, kb_config: Dict[str, Any]):
        """
        Execute the ingestion pipeline for a KB.
        
        Args:
            job: Ingestion job
            kb_config: KB configuration
        """
        try:
            kb_id = job.kb_id
            source_type = kb_config.get('source_type', 'web_generic')
            source_config = kb_config.get('source_config', {})
            
            logger.info(f"=== Starting ingestion for KB: {kb_id} ===")
            
            # Progress callback
            def progress_callback(phase: IngestionPhase, progress: int, message: str, metrics: Dict[str, Any] = None):
                job.update_progress(phase, progress, message, metrics or {})
            
            # Initialize crawler based on source type
            if source_type == SourceType.WEB_DOCUMENTATION.value:
                crawler = WebDocumentationCrawler(kb_id, source_config)
            else:
                crawler = GenericWebCrawler(kb_id, source_config)
            
            # Initialize cleaner and indexer
            cleaner = WebContentCleaner(kb_id=kb_id)
            indexer = GenericIndexBuilder(kb_config=kb_config)
            
            # Create and run pipeline
            pipeline = IngestionPipeline(
                crawler=crawler,
                cleaner=cleaner,
                indexer=indexer,
                progress_callback=progress_callback
            )
            
            # Run pipeline in thread pool to avoid blocking async event loop
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(pipeline.run)
                result = future.result()
            
            logger.info(f"=== Ingestion completed for KB: {kb_id} ===")
            logger.info(f"  Documents: {result.get('documents_processed', 0)}")
            logger.info(f"  Chunks: {result.get('chunks_created', 0)}")
            
            # Mark job as complete
            job.complete(metrics={
                'documents_processed': result.get('documents_processed', 0),
                'chunks_created': result.get('chunks_created', 0),
                'urls_crawled': result.get('urls_crawled', 0)
            })
            
        except Exception as e:
            logger.error(f"Ingestion failed for KB {job.kb_id}: {str(e)}", exc_info=True)
            job.fail(str(e))
            raise


# Singleton instance
_ingestion_service = None


def get_ingestion_service() -> KBIngestionService:
    """Get singleton ingestion service instance"""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = KBIngestionService()
    return _ingestion_service
