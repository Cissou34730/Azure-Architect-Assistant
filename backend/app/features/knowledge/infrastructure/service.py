"""Knowledge Base index service."""

import logging
import os
from typing import cast

from llama_index.core import Settings, StorageContext, VectorStoreIndex, load_index_from_storage

from app.shared.ai import get_ai_service
from app.shared.ai.adapters import AIServiceEmbedding, AIServiceLLM
from app.shared.config.app_settings import get_app_settings

from .models import KBConfig

logger = logging.getLogger(__name__)

_INDEX_CACHE: dict[str, VectorStoreIndex] = {}


class KnowledgeBaseService:
    """Service for managing index lifecycle for a knowledge base."""

    def __init__(self, kb_config: KBConfig, similarity_threshold: float | None = None):
        self.kb_config = kb_config
        self.kb_id = kb_config.id
        self.similarity_threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else get_app_settings().kb_similarity_threshold
        )
        self.kb_name = kb_config.name
        self.storage_dir = kb_config.index_path
        self._settings_configured = False

        logger.info(f"[{self.kb_id}] Service initialized - Storage: {self.storage_dir}")

    def _ensure_settings(self) -> None:
        if not self._settings_configured:
            ai_service = get_ai_service()
            Settings.embed_model = AIServiceEmbedding(
                ai_service, model_name=self.kb_config.embedding_model
            )
            Settings.llm = AIServiceLLM(
                ai_service, model_name=self.kb_config.generation_model
            )
            self._settings_configured = True

    def _load_index(self) -> VectorStoreIndex:
        self._ensure_settings()

        cache_key = self.storage_dir
        if cache_key in _INDEX_CACHE:
            logger.info(f"[{self.kb_id}] Using cached index")
            return _INDEX_CACHE[cache_key]

        logger.info(f"[{self.kb_id}] Loading index from {self.storage_dir}")
        if not os.path.exists(self.storage_dir):
            raise FileNotFoundError(f"Index not found: {self.storage_dir}")

        storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
        index = cast(VectorStoreIndex, load_index_from_storage(storage_context))
        _INDEX_CACHE[cache_key] = index
        logger.info(f"[{self.kb_id}] Index loaded and cached")
        return index

    def get_index(self) -> VectorStoreIndex:
        return self._load_index()

    def is_index_ready(self) -> bool:
        if not os.path.exists(self.storage_dir):
            return False
        docstore_path = os.path.join(self.storage_dir, "docstore.json")
        return os.path.exists(docstore_path)


def clear_index_cache(
    kb_id: str | None = None, storage_dir: str | None = None
) -> None:
    if storage_dir:
        if storage_dir in _INDEX_CACHE:
            del _INDEX_CACHE[storage_dir]
            logger.info(f"[{kb_id or 'Unknown'}] Cleared index cache for: {storage_dir}")
        else:
            logger.debug(f"[{kb_id or 'Unknown'}] Index not in cache: {storage_dir}")
    else:
        _INDEX_CACHE.clear()
        logger.info("Cleared all index caches")


def get_cached_index_count() -> int:
    return len(_INDEX_CACHE)
