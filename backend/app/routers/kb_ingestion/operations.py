"""
Business Logic for KB Ingestion Operations
Separated from routing layer for better maintainability
"""

import logging
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from llama_index.core import Document

from app.service_registry import get_kb_manager
from app.kb.ingestion.job_manager import get_job_manager, IngestionJob, IngestionPhase
from app.kb.ingestion.sources import SourceHandlerFactory
from app.kb.ingestion.chunking import ChunkerFactory
from app.kb.ingestion.indexing import IndexBuilderFactory

from .models import SourceType, CreateKBRequest

logger = logging.getLogger(__name__)


class KBIngestionService:
    """Service layer for KB ingestion operations"""
    
    def __init__(self):
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
        # Get fresh KB manager instance
        kb_manager = get_kb_manager()
        
        # Check if KB already exists
        if kb_manager.kb_exists(request.kb_id):
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
        kb_manager.create_kb(request.kb_id, kb_config)
        
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
        # Get fresh KB manager instance
        kb_manager = get_kb_manager()
        
        # Check if KB exists
        if not kb_manager.kb_exists(kb_id):
            raise ValueError(f"Knowledge base '{kb_id}' not found")
        
        # Check if job already running
        existing_job = self.job_manager.get_latest_job_for_kb(kb_id)
        if existing_job and existing_job.status.value == 'running':
            raise ValueError(f"Ingestion already running for KB '{kb_id}'")
        
        # Get KB configuration
        kb_config = kb_manager.get_kb_config(kb_id)
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
        Execute the ingestion pipeline for a KB using LlamaIndex source handlers.
        
        Args:
            job: Ingestion job
            kb_config: KB configuration
        """
        try:
            kb_id = job.kb_id
            source_type = kb_config.get('source_type', 'website')
            source_config = kb_config.get('source_config', {})
            
            logger.info(f"=== Starting ingestion for KB: {kb_id} ===")
            logger.info(f"  Source type: {source_type}")
            
            # Check if job was cancelled before starting
            if job.status.value == 'cancelled':
                logger.info(f"Job {job.job_id} was cancelled before starting")
                return
            
            # Progress callback
            def progress_callback(phase: IngestionPhase, progress: int, message: str, metrics: Dict[str, Any] = None):
                job.update_progress(phase, progress, message, metrics or {})
            
            # Phase 1: Load documents using appropriate source handler
            progress_callback(IngestionPhase.CRAWLING, 0, "Loading documents from source...", {})
            
            # Check cancellation before expensive operation
            if job.status.value == 'cancelled':
                logger.info(f"Job {job.job_id} was cancelled during document loading")
                return
            
            handler = SourceHandlerFactory.create_handler(source_type, kb_id, job=job)
            
            # Process documents in batches with incremental indexing
            all_documents = []
            total_chunks_indexed = 0
            batch_num = 0
            
            # Get configuration once
            chunk_size = kb_config.get('chunk_size', 1024)
            chunk_overlap = kb_config.get('chunk_overlap', 200)
            chunking_strategy = kb_config.get('chunking_strategy', 'semantic')
            
            # Create chunker once
            chunker = ChunkerFactory.create_chunker(
                strategy=chunking_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            # Setup index builder once (for incremental updates)
            backend_root = Path(__file__).parent.parent.parent.parent
            if 'paths' in kb_config and 'index' in kb_config['paths']:
                index_path = kb_config['paths']['index']
                if Path(index_path).is_absolute():
                    storage_dir = index_path
                else:
                    storage_dir = str(backend_root / index_path)
            else:
                storage_dir = str(backend_root / "data" / "knowledge_bases" / kb_id / "index")
            
            embedding_model = kb_config.get('embedding_model', 'text-embedding-3-small')
            generation_model = kb_config.get('generation_model', 'gpt-4o-mini')
            index_type = kb_config.get('index_type', 'vector')
            
            index_builder = IndexBuilderFactory.create_builder(
                index_type=index_type,
                kb_id=kb_id,
                storage_dir=storage_dir,
                embedding_model=embedding_model,
                generation_model=generation_model
            )
            
            logger.info("Starting batch processing with incremental indexing...")
            
            # Process each batch as it's yielded from the source
            try:
                for document_batch in self._load_documents_from_source(handler, source_type, source_config):
                    batch_num += 1
                    batch_size = len(document_batch)
                    
                    logger.info(f"\n=== Processing Batch {batch_num} ({batch_size} documents) ===")
                    
                    # Check cancellation
                    if job.status.value == 'cancelled':
                        logger.info(f"Job {job.job_id} was cancelled during batch {batch_num}")
                        logger.info(f"Indexed {total_chunks_indexed} chunks from {len(all_documents)} documents before cancellation")
                        return
                    
                    # Save batch documents to disk
                    self._save_documents_to_disk(kb_id, document_batch)
                    all_documents.extend(document_batch)
                    
                    # Update progress - Phase 1: Loading
                    progress_callback(
                        IngestionPhase.CRAWLING,
                        min(30, 10 + batch_num),
                        f"Loaded batch {batch_num} ({len(all_documents)} documents total)",
                        {"documents_loaded": len(all_documents), "batch_num": batch_num}
                    )
                    
                    # Phase 2: Chunk this batch
                    logger.info(f"Chunking batch {batch_num}...")
                    progress_callback(
                        IngestionPhase.CLEANING,
                        min(50, 30 + batch_num),
                        f"Chunking batch {batch_num}...",
                        {}
                    )
                    
                    documents_dict = self._convert_documents_to_dict(document_batch)
                    batch_chunks = chunker.chunk_documents(documents_dict)
                    
                    logger.info(f"✓ Batch {batch_num}: Created {len(batch_chunks)} chunks")
                    
                    # Phase 3: Index this batch immediately
                    logger.info(f"Indexing batch {batch_num} ({len(batch_chunks)} chunks)...")
                    progress_callback(
                        IngestionPhase.INDEXING,
                        min(90, 50 + batch_num),
                        f"Indexing batch {batch_num}...",
                        {"chunks_indexed": total_chunks_indexed}
                    )
                    
                    # Index this batch (incremental update)
                    if batch_num == 1:
                        # First batch: create new index
                        index_path = index_builder.build_index(documents_dict, progress_callback)
                        logger.info(f"✓ Created index with batch 1")
                    else:
                        # Subsequent batches: add to existing index
                        # Note: LlamaIndex doesn't support incremental updates well, so we rebuild
                        # For production, consider using a database-backed vector store
                        all_docs_dict = self._convert_documents_to_dict(all_documents)
                        index_path = index_builder.build_index(all_docs_dict, progress_callback)
                        logger.info(f"✓ Updated index (now contains {len(all_documents)} documents)")
                    
                    total_chunks_indexed += len(batch_chunks)
                    logger.info(f"✓ Total: {len(all_documents)} docs, {total_chunks_indexed} chunks indexed")
                    
            except GeneratorExit:
                logger.info(f"Generator closed - processing stopped at batch {batch_num}")
            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {e}", exc_info=True)
                raise
            
            # Verify we got documents
            if not all_documents:
                raise ValueError(f"No documents loaded from source")
            
            logger.info(f"\n=== Batch Processing Complete ===")
            logger.info(f"Total batches processed: {batch_num}")
            logger.info(f"Total documents: {len(all_documents)}")
            logger.info(f"Total chunks indexed: {total_chunks_indexed}")
            logger.info(f"Index location: {storage_dir}")
            
            if all_documents:
                logger.info(f"First doc metadata: {all_documents[0].metadata}")
                logger.info(f"First doc text preview: {all_documents[0].text[:200]}")
            
            # Mark job as complete
            logger.info(f"=== Ingestion completed for KB: {kb_id} ===")
            logger.info(f"  Documents processed: {len(all_documents)}")
            logger.info(f"  Chunks indexed: {total_chunks_indexed}")
            logger.info(f"  Index path: {storage_dir}")
            
            job.complete(metrics={
                'documents_processed': len(all_documents),
                'chunks_created': total_chunks_indexed,
                'source_count': len(all_documents),
                'batches_processed': batch_num
            })
            
        except Exception as e:
            logger.error(f"Ingestion failed for KB {job.kb_id}: {str(e)}", exc_info=True)
            job.fail(str(e))
            raise
    
    def _load_documents_from_source(
        self, 
        handler, 
        source_type: str, 
        source_config: Dict[str, Any]
    ):
        """Load documents from source based on type (returns generator for batch processing)"""
        
        logger.info(f"Loading documents from {source_type} with config: {source_config}")
        
        try:
            # Use the handler's unified ingest() method
            result = handler.ingest(source_config)
            
            # If result is a generator/iterator (batch mode), yield batches
            if hasattr(result, '__iter__') and not isinstance(result, (list, tuple)):
                logger.info(f"Handler returned generator for batch processing")
                for batch in result:
                    logger.info(f"Yielding batch of {len(batch)} documents")
                    yield batch
            else:
                # Legacy mode: handler returned list of all documents
                # Wrap in single batch
                logger.info(f"Handler returned {len(result)} documents (converting to single batch)")
                yield result
        except Exception as e:
            logger.error(f"Failed to load documents from {source_type}: {e}", exc_info=True)
            raise
    
    def _save_documents_to_disk(self, kb_id: str, documents: List[Document]):
        """Save documents to disk for reference"""
        backend_root = Path(__file__).parent.parent.parent.parent
        doc_dir = backend_root / "data" / "knowledge_bases" / kb_id / "documents"
        doc_dir.mkdir(parents=True, exist_ok=True)
        
        for i, doc in enumerate(documents):
            # Create safe filename
            source_type = doc.metadata.get('source_type', 'unknown')
            content_type = doc.metadata.get('content_type', 'main')
            
            if source_type == 'website':
                url = doc.metadata.get('url', f'doc_{i}')
                safe_name = url.replace('https://', '').replace('http://', '').replace('/', '_')
            elif source_type == 'youtube':
                video_id = doc.metadata.get('video_id', f'video_{i}')
                safe_name = f"youtube_{video_id}_{content_type}"
            elif source_type in ['pdf', 'pdf_online']:
                file_name = doc.metadata.get('file_name', f'pdf_{i}')
                page_num = doc.metadata.get('page_label', i)
                safe_name = f"pdf_{file_name}_page{page_num}".replace('.pdf', '')
            elif source_type == 'markdown':
                file_name = doc.metadata.get('file_name', f'md_{i}')
                safe_name = f"md_{file_name}".replace('.md', '')
            else:
                safe_name = f"doc_{i}"
            
            # Truncate if too long
            if len(safe_name) > 200:
                safe_name = safe_name[:200]
            
            doc_path = doc_dir / f"{safe_name}.txt"
            
            with open(doc_path, 'w', encoding='utf-8') as f:
                f.write(f"Source Type: {source_type}\n")
                f.write(f"Content Type: {content_type}\n")
                for key, value in doc.metadata.items():
                    f.write(f"{key}: {value}\n")
                f.write("=" * 80 + "\n\n")
                f.write(doc.get_content())
    
    def _convert_documents_to_dict(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """Convert LlamaIndex Documents to dict format for indexer"""
        return [
            {
                'content': doc.get_content(),
                'metadata': doc.metadata
            }
            for doc in documents
        ]


# Singleton instance
_ingestion_service = None


def get_ingestion_service() -> KBIngestionService:
    """Get singleton ingestion service instance"""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = KBIngestionService()
    return _ingestion_service
