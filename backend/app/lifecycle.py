"""
Application Lifecycle Management
Handles startup and shutdown events for the FastAPI application.
"""

import asyncio
import logging

from app.core.config import get_app_settings
from app.core.logging import configure_logging
from app.ingestion.ingestion_database import init_ingestion_database
from app.projects_database import close_database, init_database
from app.agents_system.runner import initialize_agent_runner, shutdown_agent_runner

logger = logging.getLogger(__name__)

# Global reference to MCP client for proper cleanup
_mcp_client_instance = None


async def startup():
    """
    Initialize database and load persisted ingestion states.
    KB indices are loaded lazily on first request for faster startup.
    """
    configure_logging(get_app_settings().log_level)

    logger.info("=" * 60)
    logger.info("STARTUP: Initializing services...")
    logger.info("=" * 60)

    try:
        # Initialize database
        logger.info("Initializing database...")
        await init_database()
        logger.info("Database initialized")

        # Initialize ingestion database (producer/consumer pipeline)
        logger.info("Initializing ingestion persistence...")
        await asyncio.to_thread(init_ingestion_database)
        logger.info("Ingestion persistence ready")

        # Load KB manager (configs only, no index preload)
        from app.service_registry import get_kb_manager

        logger.info("Loading KB Manager...")
        kb_mgr = get_kb_manager()
        logger.info(f"KB Manager ready ({len(kb_mgr.list_kbs())} knowledge bases)")
        logger.info("  Note: KB indices will be loaded lazily on first query")

        # Initialize agent system with MCP client
        try:
            global _mcp_client_instance
            from app.services.mcp.learn_mcp_client import MicrosoftLearnMCPClient
            
            logger.info("Initializing MCP client for agent system...")
            # Load MCP config from centralized core settings
            app_settings = get_app_settings()
            mcp_config = app_settings.get_mcp_server_config("microsoft_learn")
            
            mcp_client = MicrosoftLearnMCPClient(mcp_config)
            await mcp_client.initialize()
            _mcp_client_instance = mcp_client  # Store for cleanup
            logger.info("✓ MCP client initialized")

            logger.info("Initializing agent system...")
            await initialize_agent_runner(mcp_client)
            logger.info("✓ Agent system ready")
        except Exception as e:
            logger.warning(f"Failed to initialize agent system: {e}")
            logger.warning("Agent chat endpoints will not be available")

        logger.info("=" * 60)
        logger.info("STARTUP COMPLETE: Ready to accept requests")
        logger.info("=" * 60)

    except Exception as exc:
        logger.error(f"Error during startup: {exc}")
        logger.warning("Some services may be lazy-loaded on first request")


async def shutdown():
    """
    Cleanup on shutdown - stop running ingestion jobs gracefully.
    """
    global _mcp_client_instance

    logger.info("=" * 60)
    logger.info("SHUTDOWN: Stopping running ingestion jobs...")
    logger.info("=" * 60)

    # Shutdown agent system
    try:
        logger.info("Shutting down agent system...")
        await shutdown_agent_runner()
        logger.info("✓ Agent system shutdown")
    except Exception as e:
        logger.warning(f"Error shutting down agent system: {e}")

    # Close MCP client explicitly to avoid asyncio context errors
    if _mcp_client_instance:
        try:
            logger.info("Closing MCP client...")
            await _mcp_client_instance.close()
            _mcp_client_instance = None
            logger.info("✓ MCP client closed")
        except Exception as e:
            logger.debug(f"MCP client cleanup (expected during shutdown): {e}")

    # Close database connections
    await close_database()

    logger.info("=" * 60)
    logger.info("SHUTDOWN COMPLETE")
    logger.info("=" * 60)
