"""Database configuration and session management."""

import logging
import os
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.project import Base
from app.shared.config.app_settings import get_app_settings

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = BACKEND_ROOT / "data"
DATA_ROOT = Path(os.getenv("DATA_ROOT", str(DATA_DIR)))
app_settings = None
try:
    app_settings = get_app_settings()
except (ValidationError, ValueError):
    app_settings = None

if app_settings and app_settings.projects_database:
    DB_PATH = Path(app_settings.projects_database)
else:
    DB_PATH = Path(os.getenv("PROJECTS_DATABASE", str(DATA_ROOT / "projects.db")))

if not DB_PATH.is_absolute():
    DB_PATH = BACKEND_ROOT / DB_PATH

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
logger.info("Projects database: %s", DB_PATH.absolute())

DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"
engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_database() -> None:
    logger.info("Initializing database at: %s", DB_PATH)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_run_additive_schema_migrations)
    logger.info("Database tables initialized successfully")


def _run_additive_schema_migrations(sync_conn) -> None:
    _ensure_documents_status_columns(sync_conn)
    _ensure_pending_changes_tables(sync_conn)


def _ensure_documents_status_columns(sync_conn) -> None:
    result = sync_conn.execute(
        text("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'documents'")
    )
    if result.scalar_one_or_none() is None:
        return

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
        sync_conn.execute(text(f"ALTER TABLE documents ADD COLUMN {column_name} {column_type}"))
        logger.info(
            "Applied additive migration on documents table: added column %s",
            column_name,
        )


def _ensure_pending_changes_tables(sync_conn) -> None:
    sync_conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS pending_change_sets (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                source_message_id TEXT,
                superseded_by TEXT,
                bundle_summary TEXT NOT NULL,
                proposed_patch_json TEXT NOT NULL DEFAULT '{}',
                citations_json TEXT,
                reviewed_at TEXT,
                review_reason TEXT,
                rejection_reason TEXT,
                waf_delta_json TEXT,
                mindmap_delta_json TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
            """
        )
    )
    sync_conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS artifact_drafts (
                id TEXT PRIMARY KEY,
                change_set_id TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                artifact_id TEXT,
                content_json TEXT NOT NULL,
                citations_json TEXT,
                created_at TEXT,
                FOREIGN KEY(change_set_id) REFERENCES pending_change_sets(id) ON DELETE CASCADE
            )
            """
        )
    )


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_database() -> None:
    await engine.dispose()
    logger.info("Database connections closed")
