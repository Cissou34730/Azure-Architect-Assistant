"""
Application Lifecycle Management
Handles startup and shutdown events for the FastAPI application.
"""

import logging
import asyncio
from app.database import init_database, close_database
from app.ingestion.db import init_ingestion_database
from app.ingestion.service_components.manager import IngestionService

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
        
        # Load persisted ingestion states
        try:
            ingest_service = IngestionService.instance()
            ingest_service.load_all_states()
            logger.info("✓ Loaded persisted ingestion job states")
        except Exception as e:
            logger.warning(f"Failed to load ingestion states: {e}")
        
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
    logger.info("SHUTDOWN: Cancelling running ingestion jobs...")
    logger.info("=" * 60)
    
    # Cancel asyncio-based ingestion tasks
    try:
        ingest_service = IngestionService.instance()
        
        try:
            await asyncio.wait_for(ingest_service.cancel_all(), timeout=5.0)
            logger.info("✓ All ingestion jobs cancelled")
        except asyncio.TimeoutError:
            logger.warning("⚠ Timeout cancelling ingestion jobs (5s exceeded)")
        
    except Exception as e:
        logger.warning(f"Error cancelling ingestion tasks: {e}")

    # Close database connections
    await close_database()
    
    logger.info("=" * 60)
    logger.info("SHUTDOWN COMPLETE")
    logger.info("=" * 60)
