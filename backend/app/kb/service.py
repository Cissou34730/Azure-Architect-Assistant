"""
Knowledge Base Index Service
Manages index loading/caching only; query logic lives in app.services.kb.
"""

import os
import logging
from typing import Dict, Optional
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

from .knowledge_base_manager import KBConfig

logger = logging.getLogger(__name__)

# Global index cache across all KBs
_INDEX_CACHE: Dict[str, VectorStoreIndex] = {}


class KnowledgeBaseService:
    """Service for managing index lifecycle for a knowledge base."""
    
    def __init__(self, kb_config: KBConfig, similarity_threshold: float = 0.5):
        """
        Initialize knowledge base service.
        
        Args:
            kb_config: KB configuration
            similarity_threshold: Minimum similarity score for results
        """
        self.kb_config = kb_config
        self.kb_id = kb_config.id
        self.kb_name = kb_config.name
        self.storage_dir = kb_config.index_path
        self._settings_configured = False
        
        logger.info(f"[{self.kb_id}] Service initialized - Storage: {self.storage_dir}")
    
    def _ensure_settings(self):
        """Lazy configuration of LlamaIndex settings."""
        if not self._settings_configured:
            # Configure LlamaIndex settings for this KB
            Settings.embed_model = OpenAIEmbedding(model=self.kb_config.embedding_model)
            Settings.llm = OpenAI(
                model=self.kb_config.generation_model,
                temperature=0.1,
                max_tokens=1000,
                timeout=90.0
            )
            self._settings_configured = True
    
    def _load_index(self) -> VectorStoreIndex:
        """Load index from storage with global caching."""
        self._ensure_settings()  # Configure settings before loading index
        
        cache_key = self.storage_dir
        
        if cache_key in _INDEX_CACHE:
            logger.info(f"[{self.kb_id}] Using cached index")
            return _INDEX_CACHE[cache_key]
        
        from llama_index.core import load_index_from_storage
        
        logger.info(f"[{self.kb_id}] Loading index from {self.storage_dir}")
        
        if not os.path.exists(self.storage_dir):
            raise FileNotFoundError(f"Index not found: {self.storage_dir}")
        
        storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
        index = load_index_from_storage(storage_context)
        
        _INDEX_CACHE[cache_key] = index
        logger.info(f"[{self.kb_id}] Index loaded and cached")
        
        return index
    
    def get_index(self) -> VectorStoreIndex:
        """Public accessor to obtain the loaded index for this KB."""
        return self._load_index()
    
    def is_index_ready(self) -> bool:
        """Check if index exists and is ready."""
        if not os.path.exists(self.storage_dir):
            return False
        # Consider index ready only if core index files exist
        docstore_path = os.path.join(self.storage_dir, 'docstore.json')
        return os.path.exists(docstore_path)


def clear_index_cache(kb_id: Optional[str] = None, storage_dir: Optional[str] = None):
    """
    Clear cached indexes from memory.
    
    Args:
        kb_id: KB ID to clear (optional, for logging)
        storage_dir: Storage directory path to remove from cache
    """
    global _INDEX_CACHE
    
    if storage_dir:
        if storage_dir in _INDEX_CACHE:
            del _INDEX_CACHE[storage_dir]
            logger.info(f"[{kb_id or 'Unknown'}] Cleared index cache for: {storage_dir}")
        else:
            logger.debug(f"[{kb_id or 'Unknown'}] Index not in cache: {storage_dir}")
    else:
        # Clear all cached indexes
        _INDEX_CACHE.clear()
        logger.info("Cleared all index caches")


def get_cached_index_count() -> int:
    """Get number of cached indexes."""
    return len(_INDEX_CACHE)
