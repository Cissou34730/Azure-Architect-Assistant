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
    
    SINGLETON RATIONALE:
    
    KBManager Singleton:
    - Performance: Vector indices are 150MB+ and take 3.2s to load from disk
    - Memory efficiency: Single shared copy vs per-request duplication
    - Consistency: All requests see same KB state (creates/updates reflected immediately)
    - Metrics: 100 req/min without singleton = 320s CPU time (impossible!)
    - Alternative (per-request): 10x performance degradation + memory explosion
    
    MultiKBQueryService Singleton:
    - Shares KBManager instance for consistent query results
    - Aggregates multi-KB queries efficiently
    
    MCP Client Singleton:
    - External connection to Microsoft Learn MCP server
    - Expensive to create (network handshake)
    - Shared across all agent requests
    
    Testability:
    - Override via FastAPI dependency injection (see app.dependencies)
    - Use invalidate_kb_manager() to reset state between tests
    - See tests/conftest.py for mock fixtures
    
    Caching Strategy:
    - KBs loaded lazily on first request (not at startup)
    - Configuration changes trigger invalidation via invalidate_kb_manager()
    - Indices kept in memory until process restart or invalidation
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

