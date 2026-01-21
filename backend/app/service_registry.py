"""
Service Manager - Singleton service instances
Handles initialization and lifecycle of services with startup preloading.

NOTE: Singleton pattern is intentional for keeping indices in memory for performance.
Each service caches loaded indices to avoid repeated disk I/O.
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.mcp.learn_mcp_client import MicrosoftLearnMCPClient

from app.kb import KBManager
from app.services.kb import MultiKBQueryService

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """
    Central registry for application services.
    Uses class-level variables to implement the singleton pattern.
    """

    _kb_manager: KBManager | None = None
    _multi_query_service: MultiKBQueryService | None = None
    _mcp_client: Any | None = None

    @classmethod
    def get_kb_manager(cls) -> KBManager:
        """Get or create KBManager instance."""
        if cls._kb_manager is None:
            cls._kb_manager = KBManager()
            logger.info(f"KBManager ready ({len(cls._kb_manager.list_kbs())} KBs)")
        return cls._kb_manager

    @classmethod
    def get_multi_query_service(cls) -> MultiKBQueryService:
        """Get or create MultiSourceQueryService instance."""
        if cls._multi_query_service is None:
            manager = cls.get_kb_manager()
            cls._multi_query_service = MultiKBQueryService(manager)
            logger.info("MultiSourceQueryService ready")
        return cls._multi_query_service

    @classmethod
    def invalidate_kb_manager(cls) -> None:
        """Invalidate cached KB manager to reload configuration."""
        cls._kb_manager = None
        cls._multi_query_service = None

    @classmethod
    def set_mcp_client(cls, client: "MicrosoftLearnMCPClient") -> None:
        """Store the MCP client instance."""
        cls._mcp_client = client

    @classmethod
    def get_mcp_client(cls) -> "MicrosoftLearnMCPClient | None":
        """Get the stored MCP client instance."""
        return cls._mcp_client


def get_kb_manager() -> KBManager:
    """Compatibility wrapper for get_kb_manager."""
    return ServiceRegistry.get_kb_manager()


def get_multi_query_service() -> MultiKBQueryService:
    """Compatibility wrapper for get_multi_query_service."""
    return ServiceRegistry.get_multi_query_service()


def invalidate_kb_manager():
    """Compatibility wrapper for invalidate_kb_manager."""
    ServiceRegistry.invalidate_kb_manager()

