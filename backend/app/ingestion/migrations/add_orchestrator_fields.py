"""
Schema migration: Add orchestrator fields to ingestion_jobs table.
Adds: checkpoint, counters, heartbeat_at, finished_at, last_error
"""

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_missing_columns(cursor: sqlite3.Cursor) -> list[str]:
    """Identify which required columns are missing in ingestion_jobs table."""
    cursor.execute("PRAGMA table_info(ingestion_jobs)")
    columns = {row[1] for row in cursor.fetchall()}

    needed = [
        ("checkpoint", "TEXT"),
        ("counters", "TEXT"),
        ("heartbeat_at", "TIMESTAMP"),
        ("finished_at", "TIMESTAMP"),
        ("last_error", "TEXT"),
    ]

    return [
        f"ALTER TABLE ingestion_jobs ADD COLUMN {col} {dtype}"
        for col, dtype in needed
        if col not in columns
    ]


def migrate() -> None:
    """Add orchestrator-specific columns to ingestion_jobs table."""
    # Locate database - go up from migrations to app to backend to root
    db_path = (
        Path(__file__).parent.parent.parent.parent.parent
        / "backend"
        / "data"
        / "ingestion.db"
    )

    if not db_path.exists():
        logger.warning(f"Database not found at {db_path}, skipping migration")
        return

    logger.info(f"Running migration on {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        migrations = _get_missing_columns(cursor)

        if not migrations:
            logger.info("All columns already exist, migration not needed")
            return

        for sql in migrations:
            logger.info(f"Executing: {sql}")
            cursor.execute(sql)

        conn.commit()
        logger.info(f"Migration complete: added {len(migrations)} columns")

    except Exception as e:
        conn.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    migrate()
