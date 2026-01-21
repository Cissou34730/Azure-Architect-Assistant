"""
Vector Index Builder
Builds vector indexes from pre-embedded documents using LlamaIndex.
Responsible ONLY for indexing - embedding is done separately.
"""

import json
import logging
import os
from collections.abc import Callable
from typing import Any, cast

from llama_index.core import Document as LlamaDocument
from llama_index.core import (
    Settings,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)

from app.ingestion.domain.phase_tracker import IngestionPhase
from app.services.ai import get_ai_service
from app.services.ai.adapters import AIServiceLLM

from .builder_base import BaseIndexBuilder

logger = logging.getLogger(__name__)

# Constants
INDEX_DOCSTORE_FILE = "docstore.json"
INDEX_PROGRESS_BATCH_SIZE = 100
INDEX_P_START = 25
INDEX_P_BATCH = 50
INDEX_P_COMPLETE = 100


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
        embedding_model: str | None = None,
        generation_model: str | None = None,
    ) -> None:
        """
        Initialize vector index builder.
        """
        ai_service = get_ai_service()
        emb_model = embedding_model or ai_service.config.openai_embedding_model
        gen_model = generation_model or ai_service.config.openai_llm_model

        super().__init__(kb_id, storage_dir, emb_model, gen_model)

        # Initialize LlamaIndex LLM using AIService adapter
        Settings.llm = AIServiceLLM(ai_service, model_name=gen_model)
        self.logger.info(f"VectorIndexBuilder ready KB={kb_id} storage={storage_dir}")

    def build_index(
        self,
        embedded_documents: Any,
        progress_callback: Callable[..., Any] | None = None,
        state: Any | None = None,
    ) -> str:
        """Build vector index from PRE-EMBEDDED documents."""
        self.logger.info(f"Index build start KB={self.kb_id}")

        if not embedded_documents:
            self.logger.warning("No documents provided for indexing")
            return self.storage_dir

        self._validate_embeddings(embedded_documents)

        # Load state and existing index
        proc_state = self._load_state()
        last_id = proc_state.get("last_indexed_id", 0)
        index = self._try_load_existing_index(last_id)

        # Filter and process
        to_process = self._filter_documents(embedded_documents, last_id)
        if not to_process:
            self.logger.info("Index up to date (no new documents)")
            return self.storage_dir

        self._log_and_callback(progress_callback, to_process)

        if index is None:
            if progress_callback:
                progress_callback(IngestionPhase.INDEXING, INDEX_P_START, "Creating new index...", {})
            index = VectorStoreIndex(to_process, show_progress=True)
        else:
            self._update_existing_index(index, to_process, progress_callback)

        return self._persist_index_and_state(index, to_process, proc_state, progress_callback)

    def _validate_embeddings(self, docs: list[LlamaDocument]) -> None:
        """Ensure all documents have embeddings set."""
        missing = [i for i, d in enumerate(docs) if not hasattr(d, "embedding") or d.embedding is None]
        if missing:
            raise ValueError(f"Found {len(missing)} documents missing embeddings. Indexing requires pre-embedded docs.")

    def _try_load_existing_index(self, last_id: int) -> VectorStoreIndex | None:
        """Try to load existing index from storage."""
        if not os.path.exists(os.path.join(self.storage_dir, INDEX_DOCSTORE_FILE)):
            return None

        try:
            storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
            index = load_index_from_storage(storage_context)
            self.logger.info(f"Resuming index from doc_id {last_id + 1}")
            return cast(VectorStoreIndex, index)
        except (OSError, ValueError, RuntimeError) as e:
            self.logger.warning(f"Could not load existing index: {e}, building from scratch")
            return None

    def _filter_documents(self, docs: list[LlamaDocument], last_id: int) -> list[LlamaDocument]:
        """Filter list to only includes documents not yet indexed."""
        if last_id <= 0:
            return docs
        return [d for d in docs if d.metadata.get("doc_id", 0) > last_id]

    def _log_and_callback(self, cb: Callable[..., Any] | None, to_process: list[LlamaDocument]) -> None:
        """Log indexing start and trigger callback."""
        msg = f"Building index from {len(to_process)} documents..."
        self.logger.info(msg)
        if cb:
            cb(IngestionPhase.INDEXING, 0, msg, {"documents": len(to_process)})

    def _update_existing_index(
        self,
        index: VectorStoreIndex,
        to_process: list[LlamaDocument],
        progress_callback: Callable[..., Any] | None
    ) -> None:
        """Update existing index with batches and progress callbacks."""
        for i in range(0, len(to_process), INDEX_PROGRESS_BATCH_SIZE):
            batch = to_process[i : i + INDEX_PROGRESS_BATCH_SIZE]
            for doc in batch:
                index.insert(doc)

            if progress_callback:
                progress = INDEX_P_START + int((i / len(to_process)) * INDEX_P_BATCH)
                progress_callback(
                    IngestionPhase.INDEXING,
                    progress,
                    f"Indexed {i + len(batch)}/{len(to_process)} documents",
                    {"indexed": i + len(batch), "total": len(to_process)},
                )

    def _persist_index_and_state(
        self,
        index: VectorStoreIndex,
        to_process: list[LlamaDocument],
        proc_state: dict[str, Any],
        progress_callback: Callable[..., Any] | None
    ) -> str:
        """Persist index to disk and update internal state."""
        if progress_callback:
            progress_callback(IngestionPhase.INDEXING, INDEX_P_COMPLETE - 5, "Persisting index...", {})

        os.makedirs(self.storage_dir, exist_ok=True)
        index.storage_context.persist(persist_dir=self.storage_dir)

        # Update and save state
        if to_process:
            max_id = max(d.metadata.get("doc_id", 0) for d in to_process)
            proc_state["last_indexed_id"] = max_id
            proc_state["chunks_total"] = proc_state.get("chunks_total", 0) + len(to_process)
            proc_state["batches_processed"] = proc_state.get("batches_processed", 0) + 1
            self._save_state(proc_state)

        # Save metadata
        self._save_index_metadata(len(to_process))

        if progress_callback:
            progress_callback(
                IngestionPhase.INDEXING,
                INDEX_P_COMPLETE,
                f"Index complete: {len(to_process)} documents indexed",
                {"documents": len(to_process)},
            )

        self.logger.info(f"Index build complete: {self.storage_dir}")
        return self.storage_dir

    def _save_index_metadata(self, indexed_count: int) -> None:
        """Save index metadata in JSON format."""
        metadata_file = os.path.join(self.storage_dir, "metadata.json")
        metadata = {
            "kb_id": self.kb_id,
            "indexed_documents": indexed_count,
            "embedding_model": self.embedding_model,
            "generation_model": self.generation_model,
            "index_type": "vector",
        }
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
