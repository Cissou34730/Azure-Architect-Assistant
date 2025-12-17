"""
Vector Index Builder
Builds vector indexes from pre-embedded documents using LlamaIndex.
Responsible ONLY for indexing - embedding is done separately.
"""

import os
import json
import logging
import tempfile
from typing import List, Any, Optional, Callable, Dict
from pathlib import Path

from llama_index.core import VectorStoreIndex, Settings, StorageContext, load_index_from_storage
from llama_index.core import Document as LlamaDocument

from .builder_base import BaseIndexBuilder
from app.services.ai import get_ai_service
from app.services.ai.adapters import AIServiceLLM

logger = logging.getLogger(__name__)


class VectorIndexBuilder(BaseIndexBuilder):
    """
    Vector index builder using LlamaIndex.
    Builds searchable index from PRE-EMBEDDED documents.
    Does NOT handle embedding generation - that's done by EmbedderFactory.
    """
    
    def __init__(
        self,
        kb_id: str,
        storage_dir: str,
        embedding_model: str = "text-embedding-3-small",
        generation_model: str = "gpt-4o-mini"
    ):
        """
        Initialize vector index builder.
        
        Args:
            kb_id: Knowledge base identifier
            storage_dir: Directory for index storage
            embedding_model: Model name (for metadata only)
            generation_model: Model for LLM/generation tasks
        """
        super().__init__(kb_id, storage_dir, embedding_model, generation_model)
        
        # Initialize LlamaIndex LLM using AIService adapter
        ai_service = get_ai_service()
        Settings.llm = AIServiceLLM(
            ai_service,
            model_name=generation_model,
            temperature=0.1
        )
        
        self.logger.info(f"VectorIndexBuilder ready KB={kb_id} storage={storage_dir}")
    
    def build_index(
        self,
        embedded_documents: List[LlamaDocument],
        progress_callback: Optional[Callable] = None,
        state = None
    ) -> str:
        """
        Build vector index from PRE-EMBEDDED documents.
        Expects documents that already have embeddings generated.
        
        Args:
            embedded_documents: List of LlamaIndex Documents WITH embeddings already set
            progress_callback: Optional callback(phase, progress, message, metrics)
            state: Optional IngestionState for cooperative pause/cancel checking
            
        Returns:
            Path to the created index
        """
        from app.ingestion.domain.phase_tracker import IngestionPhase
        
        self.logger.info(f"Index build start KB={self.kb_id}")
        
        if not embedded_documents:
            self.logger.warning("No documents provided for indexing")
            return self.storage_dir
        
        # Validate that documents have embeddings
        missing_embeddings = [i for i, doc in enumerate(embedded_documents) if not hasattr(doc, 'embedding') or doc.embedding is None]
        if missing_embeddings:
            self.logger.error(f"{len(missing_embeddings)} documents missing embeddings at indices: {missing_embeddings[:10]}")
            raise ValueError(f"Documents must have embeddings set before indexing. Found {len(missing_embeddings)} without embeddings.")
        
        # Load state to see if we're resuming
        processing_state = self._load_state()
        last_indexed_id = processing_state.get('last_indexed_id', 0)
        chunks_total = processing_state.get('chunks_total', 0)
        batches_processed = processing_state.get('batches_processed', 0)
        
        # Try to load existing index
        index = None
        if os.path.exists(os.path.join(self.storage_dir, 'docstore.json')):
            try:
                storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
                index = load_index_from_storage(storage_context)
                self.logger.info(f"Resuming index from doc_id {last_indexed_id + 1}")
            except Exception as e:
                self.logger.warning(f"Could not load existing index: {e}, building from scratch")
                index = None
        
        # Filter documents to only process new ones
        if last_indexed_id > 0:
            new_docs = [d for d in embedded_documents if d.metadata.get('doc_id', 0) > last_indexed_id]
            documents_to_process = new_docs
        else:
            documents_to_process = embedded_documents
        
        if not documents_to_process:
            self.logger.info("Index up to date (no new documents)")
            return self.storage_dir
        
        if progress_callback:
            progress_callback(
                IngestionPhase.INDEXING,
                0,
                f"Building index from {len(documents_to_process)} documents...",
                {'documents': len(documents_to_process)}
            )
        
        # Build or update index from pre-embedded documents
        self.logger.info(f"Indexing {len(documents_to_process)} pre-embedded documents")
        
        if index is None:
            # Build new index from pre-embedded documents
            if progress_callback:
                progress_callback(
                    IngestionPhase.INDEXING,
                    25,
                    "Creating new vector index...",
                    {}
                )
            index = VectorStoreIndex(documents_to_process, show_progress=True)
        else:
            # Append to existing index
            if progress_callback:
                progress_callback(
                    IngestionPhase.INDEXING,
                    25,
                    f"Appending {len(documents_to_process)} documents to existing index...",
                    {}
                )
            for doc in documents_to_process:
                index.insert(doc)
        
        if progress_callback:
            progress_callback(
                IngestionPhase.INDEXING,
                75,
                "Persisting index to storage...",
                {}
            )
        
        # Persist index
        os.makedirs(self.storage_dir, exist_ok=True)
        index.storage_context.persist(persist_dir=self.storage_dir)
        
        # Update state with newly indexed doc_ids
        if documents_to_process:
            max_doc_id = max(d.metadata.get('doc_id', 0) for d in documents_to_process)
            new_chunks_total = chunks_total + len(documents_to_process)
            self._save_state(max_doc_id, new_chunks_total, batches_processed + 1)
        
        # Save metadata
        self._save_index_metadata(len(embedded_documents), len(documents_to_process))
        
        if progress_callback:
            progress_callback(
                IngestionPhase.INDEXING,
                100,
                f"Index complete: {len(documents_to_process)} documents indexed",
                {'documents': len(documents_to_process)}
            )
        
        self.logger.info("=" * 70)
        self.logger.info("Vector index build complete!")
        self.logger.info(f"  Documents indexed: {len(documents_to_process)}")
        self.logger.info(f"  Storage: {self.storage_dir}")
        self.logger.info("=" * 70)
        
        return self.storage_dir
    
    
    def _save_index_metadata(self, doc_count: int, indexed_count: int):
        """Save index metadata"""
        metadata_file = os.path.join(self.storage_dir, "metadata.json")
        
        metadata = {
            'kb_id': self.kb_id,
            'documents': doc_count,
            'indexed_documents': indexed_count,
            'embedding_model': self.embedding_model,
            'generation_model': self.generation_model,
            'index_type': 'vector'
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

