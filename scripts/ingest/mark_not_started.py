#!/usr/bin/env python3
"""
Quick helper to mark ingestion status as NOT STARTED (pending/loading) for specified KBs.
Usage:
  python scripts/ingest/mark_not_started.py caf nist-sp
"""
import sys
from pathlib import Path

# Ensure backend is on sys.path
ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.ingestion.infrastructure.repository import DatabaseRepository
from app.ingestion.infrastructure.persistence import LocalDiskPersistenceStore
from app.ingestion.domain.enums import JobStatus


def mark_kb_not_started(kb_id: str) -> None:
    repo = DatabaseRepository()
    store = LocalDiskPersistenceStore()

    state = store.load(kb_id)
    if state is None:
        # Try repo latest
        state = repo.get_latest_job(kb_id)
        if state is None:
            print(f"[WARN] No state found for KB '{kb_id}'. Skipping.")
            return

    # Reset state to not-started
    state.status = JobStatus.PENDING.value
    state.phase = "loading"
    state.progress = 0
    state.message = "KB created; ingestion not started yet"
    state.error = None
    state.metrics = {}
    state.started_at = None
    state.completed_at = None
    state.phase_status = {}

    # Persist
    store.save_state(state)
    if getattr(state, 'job_id', None):
        try:
            # Map to DB status if necessary; pending is usually stored
            repo.update_job_status(state.job_id, JobStatus.PENDING.value)
        except Exception as e:
            print(f"[WARN] Repo update failed for job {state.job_id}: {e}")

    print(f"[OK] KB '{kb_id}' marked as not-started.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/ingest/mark_not_started.py <kb_id> [<kb_id> ...]")
        sys.exit(1)
    for kb in sys.argv[1:]:
        mark_kb_not_started(kb)


if __name__ == "__main__":
    main()
