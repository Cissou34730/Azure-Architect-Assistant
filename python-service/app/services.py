"""
Service Manager - Singleton service instances
Handles initialization and lifecycle of services with startup preloading
"""

import os
import logging
from pathlib import Path
from typing import Optional

from app.kb import KBManager, MultiSourceQueryService
from app.rag.kb_query import KnowledgeBaseQueryService, WAFQueryService

logger = logging.getLogger(__name__)

# Global service instances (initialized at startup)
_query_service: Optional[WAFQueryService] = None
_kb_manager: Optional[KBManager] = None
_multi_query_service: Optional[MultiSourceQueryService] = None


def get_query_service() -> WAFQueryService:
    """
    Get or create WAFQueryService instance (singleton pattern).
    Legacy service for backward compatibility.
    Index is preloaded at initialization for fast queries.
    """
    global _query_service
    if _query_service is None:
        storage_dir = os.getenv("WAF_STORAGE_DIR")
        if not storage_dir:
            # Default path relative to project root
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            storage_dir = os.path.join(project_root, "data", "knowledge_bases", "waf", "index")
        
        logger.info(f"Initializing WAFQueryService with storage_dir: {storage_dir}")
        
        # WAFQueryService automatically preloads the index
        _query_service = WAFQueryService(
            storage_dir=storage_dir,
            embedding_model="text-embedding-3-small",
            llm_model="gpt-4o-mini"
        )
        
        logger.info("WAF Query Service initialized with preloaded index")
    
    return _query_service


def get_kb_manager() -> KBManager:
    """
    Get or create KBManager instance (singleton pattern).
    Manages knowledge base configurations.
    """
    global _kb_manager
    if _kb_manager is None:
        logger.info("Initializing KBManager")
        _kb_manager = KBManager()
        logger.info(f"KBManager initialized with {len(_kb_manager.list_kbs())} knowledge bases")
    return _kb_manager


def get_multi_query_service() -> MultiSourceQueryService:
    """
    Get or create MultiSourceQueryService instance (singleton pattern).
    Handles multi-source KB queries with profile support.
    """
    global _multi_query_service
    if _multi_query_service is None:
        logger.info("Initializing MultiSourceQueryService")
        manager = get_kb_manager()
        _multi_query_service = MultiSourceQueryService(manager)
        logger.info("MultiSourceQueryService initialized")
    return _multi_query_service


def invalidate_query_service():
    """
    Invalidate cached query service to reload index.
    Called after index rebuild.
    """
    global _query_service
    logger.info("Invalidating WAF query service cache")
    _query_service = None
