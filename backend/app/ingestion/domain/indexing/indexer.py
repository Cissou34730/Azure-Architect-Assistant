"""
Indexer
Vector store indexing with idempotency checks and cleanup support.
"""

import logging
import os
import shutil
from typing import Optional
from pathlib import Path

from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage, Document

logger = logging.getLogger(__name__)


class Indexer:
    """
    Indexes embeddings to vector store with idempotency and cleanup.
    Uses LlamaIndex VectorStoreIndex with disk persistence.
    """
    
    def __init__(self, kb_id: str, storage_base_dir: str = "backend/data/indexes"):
        """
        Initialize indexer.
        
        Args:
            kb_id: Knowledge base identifier
            storage_base_dir: Base directory for index storage
        """
        self.kb_id = kb_id
        self.storage_dir = os.path.join(storage_base_dir, kb_id)
        self._index: Optional[VectorStoreIndex] = None
        self._indexed_hashes = set()  # In-memory cache of indexed content_hashes
        
        logger.info(f"Indexer initialized: kb_id={kb_id}, storage={self.storage_dir}")
    
    def _load_index(self) -> Optional[VectorStoreIndex]:
        """Load existing index from storage if available."""
        if self._index is not None:
            return self._index
        
        if os.path.exists(os.path.join(self.storage_dir, 'docstore.json')):
            try:
                storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
                self._index = load_index_from_storage(storage_context)
                
                # Build hash cache from existing documents
                docstore = self._index.docstore
                for doc_id in docstore.docs.keys():
                    doc = docstore.get_document(doc_id)
                    if doc and doc.metadata:
                        content_hash = doc.metadata.get('content_hash')
                        if content_hash:
                            self._indexed_hashes.add(content_hash)
                
                logger.info(f"Loaded existing index with {len(self._indexed_hashes)} documents")
                return self._index
            except Exception as e:
                logger.warning(f"Could not load existing index: {e}")
                self._index = None
                self._indexed_hashes.clear()
        
        return None
    
    def exists(self, kb_id: str, content_hash: str) -> bool:
        """
        Check if chunk with content_hash already indexed.
        
        Args:
            kb_id: Knowledge base identifier (must match instance kb_id)
            content_hash: Content hash to check
            
        Returns:
            True if already indexed, False otherwise
        """
        if kb_id != self.kb_id:
            raise ValueError(f"KB ID mismatch: expected {self.kb_id}, got {kb_id}")
        
        # Try cache first
        if content_hash in self._indexed_hashes:
            return True
        
        # Load index to populate cache if not loaded
        index = self._load_index()
        if index:
            # Check again after loading
            return content_hash in self._indexed_hashes
        
        return False
    
    def index(self, kb_id: str, embedding_result) -> None:
        """
        Index an embedding to the vector store.
        
        Args:
            kb_id: Knowledge base identifier (must match instance kb_id)
            embedding_result: EmbeddingResult with vector, content_hash, metadata
            
        Raises:
            ValueError: If kb_id mismatch or embedding invalid
        """
        if kb_id != self.kb_id:
            raise ValueError(f"KB ID mismatch: expected {self.kb_id}, got {kb_id}")
        
        if not embedding_result.vector:
            raise ValueError("Embedding result has no vector")
        
        # Create LlamaIndex Document with embedding
        doc = Document(
            text=embedding_result.text,  # Store original chunk text
            metadata=embedding_result.metadata,
            id_=embedding_result.content_hash,  # Use content_hash as document ID
            embedding=embedding_result.vector
        )
        
        # Load or create index
        index = self._load_index()
        
        if index is None:
            # Create new index
            os.makedirs(self.storage_dir, exist_ok=True)
            index = VectorStoreIndex([doc])
            self._index = index
            logger.info(f"Created new index for KB {kb_id}")
        else:
            # Insert into existing index
            index.insert(doc)
        
        # Update cache
        self._indexed_hashes.add(embedding_result.content_hash)
        
        # Persist immediately (atomic write)
        index.storage_context.persist(persist_dir=self.storage_dir)
        
        logger.debug(f"Indexed chunk {embedding_result.content_hash[:8]}")
    
    def delete_by_job(self, job_id: str, kb_id: str) -> None:
        """
        Delete all indexed data for a job/KB (cleanup on cancel).
        
        Args:
            job_id: Job identifier (for logging)
            kb_id: Knowledge base identifier (must match instance kb_id)
            
        Note:
            This is a destructive operation that removes the entire index directory.
            For fine-grained deletion, we would need per-document job_id tracking,
            which is deferred for simplicity.
        """
        if kb_id != self.kb_id:
            raise ValueError(f"KB ID mismatch: expected {self.kb_id}, got {kb_id}")
        
        if os.path.exists(self.storage_dir):
            try:
                shutil.rmtree(self.storage_dir)
                logger.info(f"Deleted index directory for KB {kb_id}: {self.storage_dir}")
            except Exception as e:
                logger.error(f"Failed to delete index directory {self.storage_dir}: {e}")
                raise
        else:
            logger.warning(f"Index directory does not exist, nothing to delete: {self.storage_dir}")
        
        # Clear in-memory state
        self._index = None
        self._indexed_hashes.clear()
