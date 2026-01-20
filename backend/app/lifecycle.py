"""
Application Lifecycle Management
Handles startup and shutdown events for the FastAPI application.
"""

import asyncio
import logging
from pathlib import Path

from app.core.config import get_app_settings
from app.core.logging import configure_logging
from app.ingestion.ingestion_database import init_ingestion_database
from app.projects_database import close_database, init_database
from app.agents_system.runner import initialize_agent_runner, shutdown_agent_runner
from app.services.diagram.database import init_diagram_database, close_diagram_database
from app.agents_system.services.mindmap_loader import initialize_mindmap

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
        # Load architecture mind map (required for AAA features)
        repo_root = Path(__file__).resolve().parents[2]
        mindmap_path = repo_root / "docs" / "arch_mindmap.json"
        logger.info("Loading architecture mind map from %s", mindmap_path)
        initialize_mindmap(mindmap_path)
        logger.info("✓ Architecture mind map loaded")

        # Initialize database
        logger.info("Initializing database...")
        await init_database()
        logger.info("Database initialized")

        # Initialize ingestion database (producer/consumer pipeline)
        logger.info("Initializing ingestion persistence...")
        await asyncio.to_thread(init_ingestion_database)
        logger.info("Ingestion persistence ready")

        # Initialize diagram database
        logger.info("Initializing diagram database...")
        await init_diagram_database()
        logger.info("Diagram database ready")

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
        raise


async def shutdown():
    """
    Cleanup on shutdown - stop running ingestion jobs gracefully.
    """
    global _mcp_client_instance

    logger.info("=" * 60)
    logger.info("SHUTDOWN: Cleaning up services...")
    logger.info("=" * 60)

    # Shutdown agent system first (which uses MCP client)
    try:
        logger.info("Shutting down agent system...")
        await shutdown_agent_runner()
        logger.info("✓ Agent system shutdown")
    except Exception as e:
        logger.warning(f"Error shutting down agent system: {e}")

    # Close MCP client in the same event loop where it was initialized
    if _mcp_client_instance:
        try:
            logger.info("Closing MCP client...")
            # Properly close with reasonable timeout
            await asyncio.wait_for(_mcp_client_instance.close(), timeout=5.0)
            _mcp_client_instance = None
            logger.info("✓ MCP client closed cleanly")
        except asyncio.TimeoutError:
            logger.warning("MCP client close timed out after 5s")
            _mcp_client_instance = None
        except Exception as e:
            logger.warning(f"Error closing MCP client: {e}")
            _mcp_client_instance = None

    # Close database connections
    await close_database()

    # Close diagram database connections
    try:
        logger.info("Closing diagram database...")
        await close_diagram_database()
        logger.info("✓ Diagram database closed")
    except Exception as e:
        logger.warning(f"Error closing diagram database: {e}")

    logger.info("=" * 60)
    logger.info("SHUTDOWN COMPLETE")
    logger.info("=" * 60)
