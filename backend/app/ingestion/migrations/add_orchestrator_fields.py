"""
Schema migration: Add orchestrator fields to ingestion_jobs table.
Adds: checkpoint, counters, heartbeat_at, finished_at, last_error
"""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def migrate():
    """Add orchestrator-specific columns to ingestion_jobs table."""
    
    # Locate database
    db_path = Path(__file__).parent.parent.parent / "data" / "ingestion.db"
    
    if not db_path.exists():
        logger.warning(f"Database not found at {db_path}, skipping migration")
        return
    
    logger.info(f"Running migration on {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(ingestion_jobs)")
        columns = {row[1] for row in cursor.fetchall()}
        
        migrations = []
        
        if 'checkpoint' not in columns:
            migrations.append("ALTER TABLE ingestion_jobs ADD COLUMN checkpoint TEXT")
        
        if 'counters' not in columns:
            migrations.append("ALTER TABLE ingestion_jobs ADD COLUMN counters TEXT")
        
        if 'heartbeat_at' not in columns:
            migrations.append("ALTER TABLE ingestion_jobs ADD COLUMN heartbeat_at TIMESTAMP")
        
        if 'finished_at' not in columns:
            migrations.append("ALTER TABLE ingestion_jobs ADD COLUMN finished_at TIMESTAMP")
        
        if 'last_error' not in columns:
            migrations.append("ALTER TABLE ingestion_jobs ADD COLUMN last_error TEXT")
        
        if not migrations:
            logger.info("All columns already exist, migration not needed")
            return
        
        # Execute migrations
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate()
