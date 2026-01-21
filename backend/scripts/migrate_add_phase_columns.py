"""
Migration script to add phase tracking columns to ingestion_jobs table.
Adds: current_phase (String) and phase_progress (JSON) columns.
"""

import json
import sqlite3
from pathlib import Path


def _get_default_progress(status: str, current_phase: str) -> dict:
    """Get the initial progress payload for a job status."""
    phases = ["crawling", "cleaning", "chunking", "embedding", "indexing"]
    progress = {}

    for phase in phases:
        if status == "completed":
            progress[phase] = {
                "status": "completed",
                "progress": 100,
                "items_processed": 0,
                "items_total": 0,
            }
        elif status == "failed" and phase == "crawling":
            progress[phase] = {
                "status": "failed",
                "progress": 0,
                "items_processed": 0,
                "items_total": 0,
                "error": "Migration: Unknown error",
            }
        elif status in ["running", "paused"] and phase == "crawling":
            progress[phase] = {
                "status": "paused" if status == "paused" else "running",
                "progress": 0,
                "items_processed": 0,
                "items_total": 0,
            }
        else:
            progress[phase] = {
                "status": "pending",
                "progress": 0,
                "items_processed": 0,
                "items_total": 0,
            }

    return progress


def _add_columns(cursor: sqlite3.Cursor, columns: list[str]) -> bool:
    """Add missing columns to the table."""
    needs_migration = False

    if "current_phase" not in columns:
        print("\n✓ Adding 'current_phase' column...")
        cursor.execute("ALTER TABLE ingestion_jobs ADD COLUMN current_phase VARCHAR(50) DEFAULT 'crawling'")
        print("  Column added successfully")
        needs_migration = True
    else:
        print("\n✓ Column 'current_phase' already exists")

    if "phase_progress" not in columns:
        print("\n✓ Adding 'phase_progress' column...")
        cursor.execute("ALTER TABLE ingestion_jobs ADD COLUMN phase_progress TEXT DEFAULT '{}'")
        print("  Column added successfully")
        needs_migration = True
    else:
        print("\n✓ Column 'phase_progress' already exists")

    return needs_migration


def _initialize_job_data(cursor: sqlite3.Cursor):
    """Initialize phase data for existing jobs."""
    print("\n✓ Initializing phase_progress for existing jobs...")
    cursor.execute("SELECT id, status FROM ingestion_jobs")
    jobs = cursor.fetchall()

    for job_id, status in jobs:
        current_phase = "indexing" if status == "completed" else "crawling"
        phase_progress = _get_default_progress(status, current_phase)

        cursor.execute(
            "UPDATE ingestion_jobs SET current_phase = ?, phase_progress = ? WHERE id = ?",
            (current_phase, json.dumps(phase_progress), job_id),
        )

    print(f"  Initialized {len(jobs)} existing jobs")


def migrate_add_phase_columns():
    """Add phase tracking columns to existing ingestion_jobs table."""

    # Database path
    backend_root = Path(__file__).parent.parent
    db_path = backend_root / "data" / "ingestion.db"

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        print("No migration needed - database will be created with new schema.")
        return

    print("=" * 70)
    print("Migration: Add Phase Tracking Columns")
    print("=" * 70)
    print(f"Database: {db_path}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(ingestion_jobs)")
        columns_info = cursor.fetchall()
        columns = [col[1] for col in columns_info]

        print(f"\nExisting columns: {', '.join(columns)}")

        if _add_columns(cursor, columns):
            _initialize_job_data(cursor)
            conn.commit()
            print("\n✓ Migration completed successfully!")
        else:
            print("\n✓ No migration needed - columns already exist")

        # Verify migration
        print("\n" + "=" * 70)
        print("Verification:")
        cursor.execute("PRAGMA table_info(ingestion_jobs)")
        final_columns = cursor.fetchall()
        print("\nFinal table structure:")
        for col in final_columns:
            _, name, col_type, not_null, default_val, _ = col
            print(
                f"  {name:20} {col_type:15} {'NOT NULL' if not_null else ''} "
                f"{f'DEFAULT {default_val}' if default_val else ''}"
            )

        print("\n" + "=" * 70)
        print("Migration Complete!")
        print("=" * 70)

    except sqlite3.Error as e:
        print(f"\n✗ Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_add_phase_columns()

