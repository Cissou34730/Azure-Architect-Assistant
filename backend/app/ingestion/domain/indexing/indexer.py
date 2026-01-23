"""
Indexer
Vector store indexing with idempotency checks and cleanup support.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import cast

from llama_index.core import (
    Document,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)

from app.ingestion.domain.embedding.embedder import EmbeddingResult
from app.core.app_settings import get_kb_storage_root

logger = logging.getLogger(__name__)


class Indexer:
    """
    Indexes embeddings to vector store with idempotency and cleanup.
    Uses LlamaIndex VectorStoreIndex with disk persistence.
    """

    def __init__(self, kb_id: str, storage_base_dir: str | None = None):
        """
        Initialize indexer.

        Args:
            kb_id: Knowledge base identifier
            storage_base_dir: Base directory for knowledge bases storage (default: backend/data/knowledge_bases)
        """
        self.kb_id = kb_id

        # Single source of truth: respect KNOWLEDGE_BASES_ROOT (resolved relative to backend root).
        if storage_base_dir is None:
            storage_base_dir = str(get_kb_storage_root())

        self.storage_dir = os.path.join(storage_base_dir, kb_id, 'index')
        self.checkpoint_file = os.path.join(storage_base_dir, kb_id, 'checkpoint.json')
        self._index: VectorStoreIndex | None = None
        self._indexed_hashes: set[str] = set()  # In-memory cache of indexed content_hashes
        self._pending_persist = False  # Track if index has unpersisted changes

        # Load checkpoint for crash recovery
        self._load_checkpoint()

        logger.info(f'Indexer initialized: kb_id={kb_id}, storage={self.storage_dir}, checkpoint_hashes={len(self._indexed_hashes)}')

    def _load_checkpoint(self) -> None:
        """Load checkpoint file to recover processed content hashes after crash."""
        if os.path.exists(self.checkpoint_file):
            try:
                import json
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._indexed_hashes = set(data.get('indexed_hashes', []))
                    logger.info(f'Loaded checkpoint with {len(self._indexed_hashes)} processed hashes')
            except Exception as e:
                logger.warning(f'Failed to load checkpoint file: {e}')
                self._indexed_hashes = set()

    def _save_checkpoint(self) -> None:
        """Save checkpoint file immediately after indexing (lightweight operation)."""
        try:
            import json
            os.makedirs(os.path.dirname(self.checkpoint_file), exist_ok=True)
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump({'indexed_hashes': list(self._indexed_hashes)}, f)
        except Exception as e:
            logger.error(f'Failed to save checkpoint: {e}')

    def _load_index(self) -> VectorStoreIndex | None:
        """Load existing index from storage if available."""
        if self._index is not None:
            return self._index

        if os.path.exists(os.path.join(self.storage_dir, 'docstore.json')):
            try:
                storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
                self._index = cast(VectorStoreIndex, load_index_from_storage(storage_context))

                # Build hash cache from existing documents
                docstore = self._index.docstore
                for doc_id in docstore.docs:
                    doc = docstore.get_document(doc_id)
                    if doc and doc.metadata:
                        content_hash = doc.metadata.get('content_hash')
                        if content_hash:
                            self._indexed_hashes.add(content_hash)

                logger.info(f'Loaded existing index with {len(self._indexed_hashes)} documents')
                return self._index
            except (OSError, ValueError, RuntimeError) as e:
                logger.warning(f'Could not load existing index: {e}')
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
            raise ValueError(f'KB ID mismatch: expected {self.kb_id}, got {kb_id}')

        # Try cache first
        if content_hash in self._indexed_hashes:
            return True

        # Load index to populate cache if not loaded
        index = self._load_index()
        if index:
            # Check again after loading
            return content_hash in self._indexed_hashes

        return False

    def index(self, kb_id: str, embedding_result: EmbeddingResult) -> None:
        """
        Index an embedding to the vector store.

        Args:
            kb_id: Knowledge base identifier (must match instance kb_id)
            embedding_result: EmbeddingResult with vector, content_hash, metadata

        Raises:
            ValueError: If kb_id mismatch or embedding invalid
        """
        if kb_id != self.kb_id:
            raise ValueError(f'KB ID mismatch: expected {self.kb_id}, got {kb_id}')

        if not embedding_result.vector:
            raise ValueError('Embedding result has no vector')

        # Create LlamaIndex Document with embedding
        doc = Document(
            text=embedding_result.text,  # Store original chunk text
            metadata=embedding_result.metadata,
            id_=embedding_result.content_hash,  # Use content_hash as document ID
            embedding=embedding_result.vector,
        )

        # Load or create index
        index = self._load_index()

        if index is None:
            # Create new index
            os.makedirs(self.storage_dir, exist_ok=True)
            index = VectorStoreIndex([doc])
            self._index = index
            # Persist immediately on first chunk to create valid index files
            # This prevents repeated index recreation on subsequent chunks
            index.storage_context.persist(persist_dir=self.storage_dir)
            logger.info(f'Created new index for KB {kb_id} and persisted initial state')
        else:
            # Insert into existing index
            index.insert(doc)

        # Update cache and checkpoint (lightweight write for crash recovery)
        self._indexed_hashes.add(embedding_result.content_hash)
        self._pending_persist = True
        self._save_checkpoint()

        logger.debug(f'Indexed chunk {embedding_result.content_hash[:8]}')

    def persist(self) -> None:
        """Persist index to disk (call after batch processing to avoid per-chunk overhead)."""
        if self._index and self._pending_persist:
            try:
                self._index.storage_context.persist(persist_dir=self.storage_dir)
                self._pending_persist = False
                logger.info(f'Persisted index with {len(self._indexed_hashes)} total chunks')
            except Exception as e:
                logger.error(f'Failed to persist index: {e}')
                raise

    def delete_by_job(self, job_id: str, kb_id: str) -> None:
        """
        Delete all indexed data for a job/KB (cleanup on cancel).

        Args:
            job_id: Job identifier (for logging)
            kb_id: Knowledge base identifier (must match instance kb_id)

        Note:
            This is a destructive operation that removes the entire index directory
            and all stored documents. KB config is preserved (stored separately).
        """
        if kb_id != self.kb_id:
            raise ValueError(f'KB ID mismatch: expected {self.kb_id}, got {kb_id}')

        logger.info(f'DELETE_BY_JOB called for KB {kb_id}, job {job_id}')
        logger.info(f'  storage_dir: {self.storage_dir}')
        logger.info(f'  checkpoint_file: {self.checkpoint_file}')

        # Delete index directory
        if os.path.exists(self.storage_dir):
            try:
                shutil.rmtree(self.storage_dir)
                logger.info(f'Deleted index directory for KB {kb_id}: {self.storage_dir}')
            except Exception as e:
                logger.error(f'Failed to delete index directory {self.storage_dir}: {e}')
                raise
        else:
            logger.warning(f'Index directory does not exist, nothing to delete: {self.storage_dir}')

        # Delete documents directory
        kb_base = os.path.dirname(self.storage_dir)  # Go up from {kb_id}/index to {kb_id}
        documents_dir = os.path.join(kb_base, 'documents')
        if os.path.exists(documents_dir):
            try:
                shutil.rmtree(documents_dir)
                logger.info(f'Deleted documents directory for KB {kb_id}: {documents_dir}')
            except Exception as e:
                logger.error(f'Failed to delete documents directory {documents_dir}: {e}')
                raise
        else:
            logger.warning(f'Documents directory does not exist, nothing to delete: {documents_dir}')

        # Delete checkpoint file
        if os.path.exists(self.checkpoint_file):
            try:
                os.remove(self.checkpoint_file)
                logger.info(f'Deleted checkpoint file: {self.checkpoint_file}')
            except Exception as e:
                logger.warning(f'Failed to delete checkpoint file: {e}')

        # Clear in-memory state
        self._index = None
        self._indexed_hashes.clear()
        self._pending_persist = False
        logger.info(f'Cleared in-memory state for KB {kb_id}')
