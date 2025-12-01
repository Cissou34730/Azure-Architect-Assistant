"""
Business Logic for KB Ingestion Operations
Separated from routing layer for better maintainability
"""

import logging
import asyncio
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from llama_index.core import Document

from app.service_registry import get_kb_manager
from app.kb.ingestion.base import IngestionPhase
from app.kb.ingestion.sources import SourceHandlerFactory
from app.kb.ingestion.chunking import ChunkerFactory
from app.kb.ingestion.indexing import IndexBuilderFactory

from .models import SourceType, CreateKBRequest

logger = logging.getLogger(__name__)


class KBIngestionService:
    """Service layer for KB ingestion operations"""
    
    def __init__(self):
        pass
    
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
        
        # Note: IngestionService.start() will check if job already running
        # No need to check here as it's handled by the service layer
        
        # Get KB configuration
        kb_config = kb_manager.get_kb_config(kb_id)
        kb_name = kb_config.get('name', kb_id)
        
        logger.info(f"Starting ingestion for KB: {kb_id}")
        
        return {
            "message": f"Ingestion started for '{kb_name}'",
            "job_id": f"{kb_id}-job",
            "kb_id": kb_id
        }
    
    async def run_ingestion_pipeline(self, kb_config: Dict[str, Any], state=None):
        """
        Execute the ingestion pipeline for a KB using LlamaIndex source handlers.
        Pure async function with cooperative pause/cancel checking.
        
        Args:
            kb_config: KB configuration
            state: Optional IngestionState for cooperative pause/cancel checking
        """
        try:
            kb_id = kb_config.get('id', kb_config.get('kb_id'))
            source_type = kb_config.get('source_type', 'website')
            source_config = kb_config.get('source_config', {})
            
            logger.info(f"=== Starting ingestion for KB: {kb_id} ===")
            logger.info(f"  Source type: {source_type}")

            # Check if cancelled before starting
            if state and state.cancel_requested:
                logger.info(f"KB {kb_id} was cancelled before starting")
                return
            
            # Progress callback - updates state and persists immediately
            def progress_callback(phase: IngestionPhase, progress: int, message: str, metrics: Dict[str, Any] = None):
                # Update IngestionState
                if state:
                    state.phase = phase.value if hasattr(phase, 'value') else str(phase)
                    state.progress = progress
                    state.message = message
                    if metrics:
                        state.metrics.update(metrics)
                    
                    # Persist state immediately for live updates
                    from app.ingestion.service import IngestionService
                    ingest_service = IngestionService.instance()
                    ingest_service._persist_state(state)
            
            # Phase 1: Load documents using appropriate source handler
            progress_callback(IngestionPhase.CRAWLING, 0, "Loading documents from source...", {})
            
            # Cooperative pause check - await while paused
            if state:
                while state.paused:
                    logger.info(f"KB {kb_id} is paused, waiting...")
                    await asyncio.sleep(0.5)
                
                # Check cancellation after pause
                if state.cancel_requested:
                    logger.info(f"KB {kb_id} was cancelled during pause")
                    return
            
            # Pass state to handler for checking in tight loops
            handler = SourceHandlerFactory.create_handler(source_type, kb_id, state=state)
            
            logger.info(f"PIPELINE: Created handler, ready to load documents")
            
            # Helper for cooperative pause/cancel checking
            async def check_pause_cancel(checkpoint_name: str):
                """Cooperative check: await while paused, return True if cancelled"""
                if not state:
                    return False
                
                while state.paused:
                    logger.info(f"KB {kb_id} paused at {checkpoint_name}")
                    # Persist state during pause
                    from app.ingestion.service import IngestionService
                    ingest_service = IngestionService.instance()
                    ingest_service._persist_state(state)
                    await asyncio.sleep(0.5)
                
                if state.cancel_requested:
                    logger.info(f"KB {kb_id} cancelled at {checkpoint_name}")
                    # Persist state before exiting
                    from app.ingestion.service import IngestionService
                    ingest_service = IngestionService.instance()
                    ingest_service._persist_state(state)
                    return True
                return False
            
            # Process documents in batches with incremental indexing
            all_documents = []
            total_chunks_indexed = 0
            batch_num = 0
            
            # Get configuration once
            chunk_size = kb_config.get('chunk_size', 1024)
            chunk_overlap = kb_config.get('chunk_overlap', 200)
            chunking_strategy = kb_config.get('chunking_strategy', 'semantic')
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
                    
                    # Cooperative pause/cancel check
                    if await check_pause_cancel(f"batch {batch_num} start"):
                        logger.info(f"Indexed {total_chunks_indexed} chunks from {len(all_documents)} documents before stop")
                        return
                    
                    # Save batch documents to disk
                    self._save_documents_to_disk(kb_id, document_batch)
                    all_documents.extend(document_batch)
                    
                    # Yield control to event loop
                    await asyncio.sleep(0)
                    
                    # Update progress - Phase 1: Loading
                    progress_callback(
                        IngestionPhase.CRAWLING,
                        min(30, 10 + batch_num),
                        f"Loaded batch {batch_num} ({len(all_documents)} documents total)",
                        {"documents_loaded": len(all_documents), "batch_num": batch_num}
                    )
                    
                    # Cooperative pause/cancel check after saving
                    if await check_pause_cancel(f"batch {batch_num} after save"):
                        return
                    
                    # Phase 2: Chunk this batch
                    logger.info(f"Chunking batch {batch_num}...")
                    progress_callback(
                        IngestionPhase.CLEANING,
                        min(50, 30 + batch_num),
                        f"Chunking batch {batch_num}...",
                        {}
                    )
                    
                    documents_dict = self._convert_documents_to_dict(document_batch)
                    batch_chunks = chunker.chunk_documents(documents_dict, state=state)
                    
                    # Yield control to event loop after expensive operation
                    await asyncio.sleep(0)
                    
                    logger.info(f"✓ Batch {batch_num}: Created {len(batch_chunks)} chunks")
                    
                    # Cooperative pause/cancel check after chunking
                    if await check_pause_cancel(f"batch {batch_num} after chunk"):
                        return
                    
                    # Phase 3: Index this batch immediately (incremental)
                    logger.info(f"Indexing batch {batch_num} ({len(batch_chunks)} chunks)...")
                    progress_callback(
                        IngestionPhase.EMBEDDING,
                        min(70, 50 + batch_num * 2),
                        f"Embedding batch {batch_num}...",
                        {"chunks_indexed": total_chunks_indexed}
                    )
                    
                    progress_callback(
                        IngestionPhase.INDEXING,
                        min(90, 60 + batch_num * 2),
                        f"Indexing batch {batch_num}...",
                        {"chunks_indexed": total_chunks_indexed}
                    )
                    
                    # Pass only NEW documents from this batch to index builder
                    # The builder will check checkpoint and append incrementally
                    index_path = index_builder.build_index(documents_dict, progress_callback, state=state)
                    
                    # Yield control to event loop after expensive operation
                    await asyncio.sleep(0)
                    
                    logger.info(f"✓ Indexed batch {batch_num} incrementally")
                    
                    total_chunks_indexed += len(batch_chunks)
                    logger.info(f"✓ Total: {len(all_documents)} docs, {total_chunks_indexed} chunks indexed")
                    
                    # Update metrics and persist state after successful batch completion
                    if state:
                        state.metrics['batches_processed'] = batch_num
                        state.metrics['chunks_total'] = total_chunks_indexed
                        state.metrics['documents_processed'] = len(all_documents)
                        
                        from app.ingestion.service import IngestionService
                        ingest_service = IngestionService.instance()
                        ingest_service._persist_state(state)
                    
            except GeneratorExit:
                logger.info(f"Generator closed - processing stopped at batch {batch_num}")
            except asyncio.CancelledError:
                logger.info(f"KB {kb_id} was cancelled by system shutdown")
                if state:
                    state.status = "cancelled"
                raise
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
            
            # Mark as complete
            logger.info(f"=== Ingestion completed for KB: {kb_id} ===")
            logger.info(f"  Documents processed: {len(all_documents)}")
            logger.info(f"  Chunks indexed: {total_chunks_indexed}")
            logger.info(f"  Index path: {storage_dir}")
            
            if state:
                state.status = "completed"
                state.metrics = {
                    'documents_processed': len(all_documents),
                    'chunks_created': total_chunks_indexed,
                    'source_count': len(all_documents),
                    'batches_processed': batch_num
                }
            
        except Exception as e:
            logger.error(f"Ingestion failed for KB {kb_id}: {str(e)}", exc_info=True)
            if state:
                state.status = "failed"
                state.error = str(e)
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
        """Persist documents to disk with ID-based naming: {id:04d}_{page-name}.md"""
        import re
        from urllib.parse import urlparse
        
        backend_root = Path(__file__).parent.parent.parent.parent
        doc_dir = backend_root / "data" / "knowledge_bases" / kb_id / "documents"
        doc_dir.mkdir(parents=True, exist_ok=True)
        
        for doc in documents:
            meta = doc.metadata or {}
            doc_id = meta.get('doc_id', 0)
            url = meta.get('url', '')
            
            # Extract page name from URL
            if url:
                parsed = urlparse(url)
                path = parsed.path.rstrip('/')
                page_name = path.split('/')[-1] if path else 'index'
                # Remove file extensions
                page_name = re.sub(r'\.(html?|php|asp)$', '', page_name)
            else:
                page_name = 'document'
            
            # Sanitize for Windows: remove invalid chars
            page_name = re.sub(r'[<>:"/\\|?*]', '_', page_name)
            page_name = re.sub(r'\s+', '_', page_name)
            page_name = page_name.strip('._')
            
            if not page_name or page_name == '_':
                page_name = 'document'
            
            # Limit length
            if len(page_name) > 100:
                page_name = page_name[:100]
            
            # Format: {id:04d}_{page-name}.md
            filename = f"{doc_id:04d}_{page_name}.md"
            doc_path = doc_dir / filename
            
            try:
                with open(doc_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Doc ID: {doc_id}\n")
                    f.write(f"# URL: {url}\n\n")
                    f.write(doc.text or "")
            except Exception as e:
                logger.error(f"Failed to save document {doc_id}: {e}")
    
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
