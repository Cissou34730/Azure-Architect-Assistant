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
            
            # Progress callback
            def progress_callback(phase: IngestionPhase, progress: int, message: str, metrics: Dict[str, Any] = None):
                job.update_progress(phase, progress, message, metrics or {})
            
            # Phase 1: Load documents using appropriate source handler
            progress_callback(IngestionPhase.CRAWLING, 0, "Loading documents from source...", {})
            
            handler = SourceHandlerFactory.create_handler(source_type, kb_id)
            documents = self._load_documents_from_source(handler, source_type, source_config)
            
            logger.info(f"✓ Loaded {len(documents)} documents from source")
            progress_callback(
                IngestionPhase.CLEANING, 
                50, 
                f"Loaded {len(documents)} documents", 
                {"documents_loaded": len(documents)}
            )
            
            if not documents:
                raise ValueError(f"No documents loaded from source")
            
            # Save documents to disk
            self._save_documents_to_disk(kb_id, documents)
            
            # Phase 2: Chunk documents
            progress_callback(IngestionPhase.CLEANING, 55, "Chunking documents...", {})
            
            # Convert LlamaIndex Documents to dict format for chunking
            documents_dict = self._convert_documents_to_dict(documents)
            
            # Get chunking configuration
            chunk_size = kb_config.get('chunk_size', 1024)
            chunk_overlap = kb_config.get('chunk_overlap', 200)
            chunking_strategy = kb_config.get('chunking_strategy', 'semantic')
            
            # Create chunker and chunk documents
            chunker = ChunkerFactory.create_chunker(
                strategy=chunking_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            chunks = chunker.chunk_documents(documents_dict)
            
            logger.info(f"✓ Created {len(chunks)} chunks from {len(documents)} documents")
            
            # Phase 3: Build index
            progress_callback(IngestionPhase.INDEXING, 60, f"Building index from {len(chunks)} chunks...", {})
            
            # Get storage directory
            backend_root = Path(__file__).parent.parent.parent.parent
            if 'paths' in kb_config and 'index' in kb_config['paths']:
                index_path = kb_config['paths']['index']
                if Path(index_path).is_absolute():
                    storage_dir = index_path
                else:
                    storage_dir = str(backend_root / index_path)
            else:
                storage_dir = str(backend_root / "data" / "knowledge_bases" / kb_id / "index")
            
            # Get embedding and generation models
            embedding_model = kb_config.get('embedding_model', 'text-embedding-3-small')
            generation_model = kb_config.get('generation_model', 'gpt-4o-mini')
            index_type = kb_config.get('index_type', 'vector')
            
            # Create index builder and build index
            index_builder = IndexBuilderFactory.create_builder(
                index_type=index_type,
                kb_id=kb_id,
                storage_dir=storage_dir,
                embedding_model=embedding_model,
                generation_model=generation_model
            )
            index_path = index_builder.build_index(documents_dict, progress_callback)
            
            logger.info(f"✓ Index built at: {index_path}")
            
            # Mark job as complete
            logger.info(f"=== Ingestion completed for KB: {kb_id} ===")
            logger.info(f"  Documents processed: {len(documents)}")
            logger.info(f"  Chunks created: {len(chunks)}")
            
            job.complete(metrics={
                'documents_processed': len(documents),
                'chunks_created': len(chunks),
                'source_count': len(documents)
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
    ) -> List[Document]:
        """Load documents from source based on type"""
        
        logger.info(f"Loading documents from {source_type} with config: {source_config}")
        
        try:
            # Use the handler's unified ingest() method
            documents = handler.ingest(source_config)
            logger.info(f"Handler returned {len(documents)} documents")
            return documents
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
