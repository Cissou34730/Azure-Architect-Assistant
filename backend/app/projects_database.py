"""
Database configuration and session management.
SQLAlchemy with async SQLite support.
"""

import logging
import os
from pathlib import Path

from sqlalchemy import text
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

# Log resolved path for debugging (esp. important for E2E tests)
logger.info(f"Projects database: {DB_PATH.absolute()}")

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
        await conn.run_sync(_run_additive_schema_migrations)

    logger.info("Database tables initialized successfully")


def _run_additive_schema_migrations(sync_conn) -> None:
    """Apply additive schema changes that create_all cannot enforce on existing DBs."""
    _ensure_documents_status_columns(sync_conn)


def _ensure_documents_status_columns(sync_conn) -> None:
    result = sync_conn.execute(text("PRAGMA table_info(documents)"))
    existing_columns = {str(row[1]) for row in result.fetchall()}

    additive_columns = (
        ("stored_path", "TEXT"),
        ("parse_status", "TEXT"),
        ("analysis_status", "TEXT"),
        ("parse_error", "TEXT"),
        ("analyzed_at", "TEXT"),
        ("last_analysis_run_id", "TEXT"),
    )

    for column_name, column_type in additive_columns:
        if column_name in existing_columns:
            continue
        sync_conn.execute(
            text(f"ALTER TABLE documents ADD COLUMN {column_name} {column_type}")
        )
        logger.info(
            "Applied additive migration on documents table: added column %s",
            column_name,
        )


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

