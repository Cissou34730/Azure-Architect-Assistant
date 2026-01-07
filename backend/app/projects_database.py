"""
Database configuration and session management.
SQLAlchemy with async SQLite support.
"""

import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
import logging

from app.models.project import Base

logger = logging.getLogger(__name__)

# Database path from environment variable
BACKEND_ROOT = Path(__file__).parent.parent
DATA_DIR = BACKEND_ROOT / "data"
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
