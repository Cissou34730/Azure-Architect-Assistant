"""
Database configuration and session management.
SQLAlchemy with async SQLite support.
"""

import logging
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.app_settings import get_app_settings
from app.models.project import Base

logger = logging.getLogger(__name__)

# Database path from central AppSettings or environment variable
BACKEND_ROOT = Path(__file__).parent.parent
DATA_DIR = BACKEND_ROOT / "data"
app_settings = None
try:
    app_settings = get_app_settings()
except Exception:  # noqa: BLE001
    app_settings = None

if app_settings and app_settings.projects_database:
    DB_PATH = Path(app_settings.projects_database)
else:
    DB_PATH = Path(os.getenv("PROJECTS_DATABASE", str(DATA_DIR / "projects.db")))

# Handle relative paths
if not DB_PATH.is_absolute():
    DB_PATH = BACKEND_ROOT / DB_PATH

# Ensure data directory exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Database URL for async SQLite
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,  # Set to True for SQL debugging
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_database():
    """Initialize database tables."""
    logger.info(f"Initializing database at: {DB_PATH}")

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables initialized successfully")


async def get_db():
    """Dependency for getting database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_database():
    """Close database connections."""
    await engine.dispose()
    logger.info("Database connections closed")

