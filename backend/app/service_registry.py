"""
Service Manager - Singleton service instances
Handles initialization and lifecycle of services with startup preloading.

NOTE: Singleton pattern is intentional for keeping indices in memory for performance.
Each service caches loaded indices to avoid repeated disk I/O.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from app.kb import KBManager, MultiSourceQueryService, KnowledgeBaseService

logger = logging.getLogger(__name__)

# Global service instances (initialized at startup)
# Singletons maintain in-memory index cache for performance
_waf_kb_service: Optional[KnowledgeBaseService] = None
_kb_manager: Optional[KBManager] = None
_multi_query_service: Optional[MultiSourceQueryService] = None


def get_query_service() -> KnowledgeBaseService:
    """
    Get or create WAF KnowledgeBaseService instance (singleton pattern).
    Legacy endpoint for backward compatibility.
    
    NOTE: Singleton keeps index in memory for fast queries.
    """
    global _waf_kb_service
    if _waf_kb_service is None:
        logger.info("Initializing WAF KnowledgeBaseService")
        
        manager = get_kb_manager()
        waf_config = manager.get_kb('waf')
        
        if not waf_config:
            raise ValueError("WAF knowledge base not found in configuration")
        
        # KnowledgeBaseService automatically loads and caches index
        _waf_kb_service = KnowledgeBaseService(waf_config)
        logger.info("WAF KnowledgeBaseService initialized with cached index")
    
    return _waf_kb_service


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
    
    NOTE: Clears in-memory index cache.
    """
    global _waf_kb_service
    logger.info("Invalidating WAF KB service cache")
    _waf_kb_service = None
