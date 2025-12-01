"""
Vector Index Builder
Builds vector indexes using LlamaIndex.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

from llama_index.core import Document, VectorStoreIndex, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

from .base import BaseIndexBuilder

logger = logging.getLogger(__name__)


class VectorIndexBuilder(BaseIndexBuilder):
    """
    Vector index builder using LlamaIndex.
    Creates vector embeddings and builds searchable index.
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
            embedding_model: Model for embeddings
            generation_model: Model for generation/LLM tasks
        """
        super().__init__(kb_id, storage_dir, embedding_model, generation_model)
        
        # Initialize LlamaIndex settings
        Settings.embed_model = OpenAIEmbedding(model=embedding_model)
        Settings.llm = OpenAI(model=generation_model, temperature=0.1)
        
        self.logger.info(f"VectorIndexBuilder init KB='{kb_id}' storage={storage_dir}")
    
    def _get_state_path(self) -> str:
        """Get path to unified state file."""
        kb_dir = Path(self.storage_dir).parent
        return str(kb_dir / "state.json")
    
    def _load_state(self) -> Dict[str, Any]:
        """Load processing state from unified state.json."""
        state_path = self._get_state_path()
        if os.path.exists(state_path):
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('processing', {
                        'last_indexed_id': 0,
                        'chunks_total': 0,
                        'batches_processed': 0
                    })
            except Exception as e:
                self.logger.warning(f"Could not load state: {e}")
        return {
            'last_indexed_id': 0,
            'chunks_total': 0,
            'batches_processed': 0
        }
    
    def _save_state(self, last_indexed_id: int, chunks_total: int, batches_processed: int = 0):
        """Save processing state to unified state.json."""
        state_path = self._get_state_path()
        try:
            # Load existing state (preserve other sections like job, crawl)
            state = {}
            if os.path.exists(state_path):
                try:
                    with open(state_path, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                except Exception:
                    state = {}
            
            # Update only processing section
            from datetime import datetime
            state['kb_id'] = self.kb_id
            state['version'] = 1
            state['updated_at'] = datetime.now().isoformat()
            state['processing'] = {
                'last_indexed_id': last_indexed_id,
                'chunks_total': chunks_total,
                'batches_processed': batches_processed
            }
            
            # Atomic write using tempfile
            state_dir = os.path.dirname(state_path)
            os.makedirs(state_dir, exist_ok=True)
            
            tmp_fd, tmp_name = tempfile.mkstemp(dir=state_dir, suffix='.tmp')
            with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
            os.replace(tmp_name, state_path)
            
            # State checkpoint saved (verbosity reduced)
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
    
    def build_index(
        self,
        documents: List[Dict[str, Any]],
        progress_callback: Optional[Callable] = None,
        state = None
    ) -> str:
        """
        Build vector index from documents with incremental support.
        Resumes from last indexed doc_id if checkpoint exists.
        
        Args:
            documents: List of documents with 'content' and 'metadata' keys
            progress_callback: Optional callback(phase, progress, message, metrics)
            state: Optional IngestionState for cooperative pause/cancel checking
            
        Returns:
            Path to the created index
        """
        from ..base import IngestionPhase
        from llama_index.core import StorageContext, load_index_from_storage
        
        self.logger.info(f"Index build start KB={self.kb_id}")
        
        # Validate documents
        if not self.validate_documents(documents):
            raise ValueError("Document validation failed")
        
        # Load state to see if we're resuming
        processing_state = self._load_state()
        last_indexed_id = processing_state.get('last_indexed_id', 0)
        chunks_total = processing_state.get('chunks_total', 0)
        batches_processed = processing_state.get('batches_processed', 0)
        
        # Try to load existing index
        index = None
        if os.path.exists(os.path.join(self.storage_dir, 'docstore.json')):
            try:
                self.logger.info(f"Loading existing index")
                storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
                index = load_index_from_storage(storage_context)
                self.logger.info(f"Resume from doc_id {last_indexed_id + 1}")
            except Exception as e:
                self.logger.warning(f"Could not load existing index: {e}, building from scratch")
                index = None
        
        # Filter documents to only process new ones
        if last_indexed_id > 0:
            new_docs = [d for d in documents if d.get('metadata', {}).get('doc_id', 0) > last_indexed_id]
            self.logger.info(f"Resuming: {len(new_docs)} new documents to index (skipping first {last_indexed_id})")
            documents_to_process = new_docs
        else:
            documents_to_process = documents
            self.logger.info(f"Starting fresh: {len(documents_to_process)} documents to index")
        
        if not documents_to_process:
            self.logger.info("No new documents to index, index is up to date")
            return self.storage_dir
        
        if progress_callback:
            progress_callback(
                IngestionPhase.EMBEDDING,
                0,
                "Converting documents...",
                {'documents': len(documents_to_process)}
            )
        
        # Convert to LlamaIndex documents
        llama_docs = self._build_llama_documents(documents_to_process)
        
        if not llama_docs:
            self.logger.warning("No valid documents to index")
            return self.storage_dir
        
        self.logger.info(f"Converted {len(llama_docs)} documents")
        
        if progress_callback:
            progress_callback(
                IngestionPhase.EMBEDDING,
                25,
                f"Building index from {len(llama_docs)} documents...",
                {'documents': len(llama_docs)}
            )
        
        # Build or update index
        self.logger.info("Generating embeddings and building index...")
        if progress_callback:
            progress_callback(
                IngestionPhase.EMBEDDING,
                50,
                "Generating embeddings...",
                {}
            )
        
        if index is None:
            # Build new index - pause/cancel handled at pipeline level (batch boundaries)
            index = VectorStoreIndex.from_documents(
                llama_docs,
                show_progress=True
            )
        else:
            # Append to existing index - pause/cancel handled at pipeline level
            for doc in llama_docs:
                index.insert(doc)
            self.logger.info(f"Appended {len(llama_docs)} documents to existing index")
        
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
        
        self.logger.info(f"Index persisted to {self.storage_dir}")
        
        # Update state with newly indexed doc_ids
        if documents_to_process:
            max_doc_id = max(d.get('metadata', {}).get('doc_id', 0) for d in documents_to_process)
            new_chunks_total = chunks_total + len(llama_docs)
            self._save_state(max_doc_id, new_chunks_total, batches_processed + 1)
        
        # Save metadata
        self._save_index_metadata(len(documents), len(llama_docs))
        
        if progress_callback:
            progress_callback(
                IngestionPhase.INDEXING,
                100,
                f"Index complete: {len(documents)} documents",
                {'documents': len(documents)}
            )
        
        self.logger.info("=" * 70)
        self.logger.info("Vector index build complete!")
        self.logger.info(f"  Documents: {len(documents)}")
        self.logger.info(f"  Storage: {self.storage_dir}")
        self.logger.info("=" * 70)
        
        return self.storage_dir
    
    def _build_llama_documents(self, documents: List[Dict[str, Any]]) -> List[Document]:
        """
        Convert documents to LlamaIndex Document objects.
        
        Args:
            documents: List of documents with 'content' and 'metadata' keys
            
        Returns:
            List of LlamaIndex Documents
        """
        llama_docs = []
        
        for i, doc in enumerate(documents):
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            
            if not content:
                self.logger.warning(f"Skipping document {i}: empty content")
                continue
            
            # Create document ID
            doc_id = metadata.get('url') or metadata.get('file_path') or f"doc_{i}"
            if len(doc_id) > 200:  # Truncate long IDs
                doc_id = doc_id[:200]
            
            llama_doc = Document(
                text=content,
                metadata=metadata,
                id_=doc_id
            )
            
            llama_docs.append(llama_doc)
        
        self.logger.info(f"Created {len(llama_docs)} LlamaIndex documents")
        return llama_docs
    
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
        
        self.logger.info(f"Metadata saved to {metadata_file}")
