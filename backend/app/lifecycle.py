"""
Application Lifecycle Management
Handles startup and shutdown events for the FastAPI application.
"""

import asyncio
import logging

from app.core.config import get_app_settings
from app.core.logging import configure_logging
from app.ingestion.application.ingestion_service import IngestionService
from app.ingestion.ingestion_database import init_ingestion_database
from app.projects_database import close_database, init_database

logger = logging.getLogger(__name__)


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

        # Initialize ingestion service (loads persisted states automatically)
        try:
            ingest_service = IngestionService.instance()
            logger.info("Ingestion service initialized")
        except Exception as exc:
            logger.warning(f"Failed to initialize ingestion service: {exc}")

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
    logger.info("=" * 60)
    logger.info("SHUTDOWN: Stopping running ingestion jobs...")
    logger.info("=" * 60)

    # Cancel asyncio-based ingestion tasks
    try:
        ingest_service = IngestionService.instance()

        try:
            await asyncio.wait_for(ingest_service.pause_all(), timeout=5.0)
            logger.info("All ingestion jobs stopped")
        except asyncio.TimeoutError:
            logger.warning("Timeout stopping ingestion jobs (5s exceeded)")

    except Exception as exc:
        logger.warning(f"Error cancelling ingestion tasks: {exc}")

    # Close database connections
    await close_database()

    logger.info("=" * 60)
    logger.info("SHUTDOWN COMPLETE")
    logger.info("=" * 60)
