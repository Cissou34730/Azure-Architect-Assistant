"""
Application Lifecycle Management
Handles startup and shutdown events for the FastAPI application.
"""

import logging
import asyncio
from app.projects_database import init_database, close_database
from app.ingestion.ingestion_database import init_ingestion_database
from app.ingestion.application.ingestion_service import IngestionService
from app.agents_system.runner import initialize_agent_runner, shutdown_agent_runner

logger = logging.getLogger(__name__)


async def startup():
    """
    Initialize database and load persisted ingestion states.
    KB indices are loaded lazily on first request for faster startup.
    """
    logger.info("=" * 60)
    logger.info("STARTUP: Initializing services...")
    logger.info("=" * 60)
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        await init_database()
        logger.info("✓ Database initialized")
        
        # Initialize ingestion database (producer/consumer pipeline)
        logger.info("Initializing ingestion persistence...")
        await asyncio.to_thread(init_ingestion_database)
        logger.info("✓ Ingestion persistence ready")

        # Load KB manager (configs only, no index preload)
        from app.service_registry import get_kb_manager
        logger.info("Loading KB Manager...")
        kb_mgr = get_kb_manager()
        logger.info(f"✓ KB Manager ready ({len(kb_mgr.list_kbs())} knowledge bases)")
        logger.info("  Note: KB indices will be loaded lazily on first query")
        
        # Initialize ingestion service (loads persisted states automatically)
        try:
            ingest_service = IngestionService.instance()
            logger.info("✓ Ingestion service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize ingestion service: {e}")
        
        # Initialize agent system with MCP client
        try:
            from app.services.mcp.learn_mcp_client import MicrosoftLearnMCPClient
            logger.info("Initializing MCP client for agent system...")
            mcp_config = {
                "endpoint": "https://learn.microsoft.com/api/mcp",
                "timeout": 30,
            }
            mcp_client = MicrosoftLearnMCPClient(mcp_config)
            await mcp_client.initialize()
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
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        logger.warning("Some services may be lazy-loaded on first request")


async def shutdown():
    """
    Cleanup on shutdown - cancel running ingestion jobs gracefully.
    """
    logger.info("=" * 60)
    logger.info("SHUTDOWN: Pausing running ingestion jobs...")
    logger.info("=" * 60)
    
    # Cancel asyncio-based ingestion tasks
    try:
        ingest_service = IngestionService.instance()
        
        try:
            await asyncio.wait_for(ingest_service.pause_all(), timeout=5.0)
            logger.info("✓ All ingestion jobs paused")
        except asyncio.TimeoutError:
            logger.warning("⚠ Timeout pausing ingestion jobs (5s exceeded)")
        
    except Exception as e:
        logger.warning(f"Error cancelling ingestion tasks: {e}")

    # Shutdown agent system
    try:
        logger.info("Shutting down agent system...")
        await shutdown_agent_runner()
        logger.info("✓ Agent system shutdown")
    except Exception as e:
        logger.warning(f"Error shutting down agent system: {e}")
    
    # Close database connections
    await close_database()
    
    logger.info("=" * 60)
    logger.info("SHUTDOWN COMPLETE")
    logger.info("=" * 60)
