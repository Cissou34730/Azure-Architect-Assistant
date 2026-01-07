"""
Migration script to add phase tracking columns to ingestion_jobs table.
Adds: current_phase (String) and phase_progress (JSON) columns.
"""

import sqlite3
import json
from pathlib import Path


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
        columns = [col[1] for col in cursor.fetchall()]

        print(f"\nExisting columns: {', '.join(columns)}")

        needs_migration = False

        # Check for current_phase column
        if "current_phase" not in columns:
            print("\n✓ Adding 'current_phase' column...")
            cursor.execute("""
                ALTER TABLE ingestion_jobs 
                ADD COLUMN current_phase VARCHAR(50) DEFAULT 'crawling'
            """)
            print("  Column added successfully")
            needs_migration = True
        else:
            print("\n✓ Column 'current_phase' already exists")

        # Check for phase_progress column
        if "phase_progress" not in columns:
            print("\n✓ Adding 'phase_progress' column...")
            cursor.execute("""
                ALTER TABLE ingestion_jobs 
                ADD COLUMN phase_progress TEXT DEFAULT '{}'
            """)
            print("  Column added successfully")
            needs_migration = True
        else:
            print("\n✓ Column 'phase_progress' already exists")

        if needs_migration:
            # Initialize phase_progress for existing rows
            print("\n✓ Initializing phase_progress for existing jobs...")

            cursor.execute("SELECT id, status FROM ingestion_jobs")
            jobs = cursor.fetchall()

            for job_id, status in jobs:
                # Set initial phase based on status
                if status == "completed":
                    current_phase = "indexing"
                    # Mark all phases as completed
                    phase_progress = {
                        "crawling": {
                            "status": "completed",
                            "progress": 100,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                        "cleaning": {
                            "status": "completed",
                            "progress": 100,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                        "chunking": {
                            "status": "completed",
                            "progress": 100,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                        "embedding": {
                            "status": "completed",
                            "progress": 100,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                        "indexing": {
                            "status": "completed",
                            "progress": 100,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                    }
                elif status == "failed":
                    current_phase = "crawling"
                    # Mark crawling as failed
                    phase_progress = {
                        "crawling": {
                            "status": "failed",
                            "progress": 0,
                            "items_processed": 0,
                            "items_total": 0,
                            "error": "Migration: Unknown error",
                        },
                        "cleaning": {
                            "status": "pending",
                            "progress": 0,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                        "chunking": {
                            "status": "pending",
                            "progress": 0,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                        "embedding": {
                            "status": "pending",
                            "progress": 0,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                        "indexing": {
                            "status": "pending",
                            "progress": 0,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                    }
                elif status in ["running", "paused"]:
                    current_phase = "crawling"
                    # Mark crawling as paused/running
                    phase_status = "paused" if status == "paused" else "running"
                    phase_progress = {
                        "crawling": {
                            "status": phase_status,
                            "progress": 0,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                        "cleaning": {
                            "status": "pending",
                            "progress": 0,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                        "chunking": {
                            "status": "pending",
                            "progress": 0,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                        "embedding": {
                            "status": "pending",
                            "progress": 0,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                        "indexing": {
                            "status": "pending",
                            "progress": 0,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                    }
                else:  # pending, cancelled
                    current_phase = "crawling"
                    phase_progress = {
                        "crawling": {
                            "status": "pending",
                            "progress": 0,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                        "cleaning": {
                            "status": "pending",
                            "progress": 0,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                        "chunking": {
                            "status": "pending",
                            "progress": 0,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                        "embedding": {
                            "status": "pending",
                            "progress": 0,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                        "indexing": {
                            "status": "pending",
                            "progress": 0,
                            "items_processed": 0,
                            "items_total": 0,
                        },
                    }

                cursor.execute(
                    "UPDATE ingestion_jobs SET current_phase = ?, phase_progress = ? WHERE id = ?",
                    (current_phase, json.dumps(phase_progress), job_id),
                )

            print(f"  Initialized {len(jobs)} existing jobs")

            # Commit changes
            conn.commit()
            print("\n✓ Migration completed successfully!")
        else:
            print("\n✓ No migration needed - columns already exist")

        # Verify migration
        print("\n" + "=" * 70)
        print("Verification:")
        cursor.execute("PRAGMA table_info(ingestion_jobs)")
        columns = cursor.fetchall()
        print("\nFinal table structure:")
        for col in columns:
            col_id, name, col_type, not_null, default_val, pk = col
            print(
                f"  {name:20} {col_type:15} {'NOT NULL' if not_null else ''} {f'DEFAULT {default_val}' if default_val else ''}"
            )

        print("\n" + "=" * 70)
        print("Migration Complete!")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_add_phase_columns()
