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

from app.kb import KBManager
from app.services.kb import MultiKBQueryService

logger = logging.getLogger(__name__)

# Global service instances (initialized at startup)
# Singletons maintain in-memory index cache for performance
_kb_manager: Optional[KBManager] = None
_multi_query_service: Optional[MultiKBQueryService] = None


def get_kb_manager() -> KBManager:
    """
    Get or create KBManager instance (singleton pattern).
    Manages knowledge base configurations.
    """
    global _kb_manager
    if _kb_manager is None:
        _kb_manager = KBManager()
        logger.info(f"KBManager ready ({len(_kb_manager.list_kbs())} KBs)")
    return _kb_manager


def get_multi_query_service() -> MultiKBQueryService:
    """
    Get or create MultiSourceQueryService instance (singleton pattern).
    Handles multi-source KB queries with profile support.
    """
    global _multi_query_service
    if _multi_query_service is None:
        manager = get_kb_manager()
        _multi_query_service = MultiKBQueryService(manager)
        logger.info("MultiSourceQueryService ready")
    return _multi_query_service


def invalidate_kb_manager():
    """
    Invalidate cached KB manager to reload configuration.
    Called after KB create/update/delete operations.
    
    NOTE: Forces reload of config.json on next access.
    """
    global _kb_manager, _multi_query_service
    # Cache invalidation (log suppressed)
    _kb_manager = None
    # Also invalidate multi_query_service since it depends on KB manager
    _multi_query_service = None
