"""
Backfill script to recompute and persist canonical ingestion job statuses.

Usage (Windows PowerShell):
  $env:PYTHONPATH = "."; & .venv\Scripts\python.exe backend\scripts\recompute_job_statuses.py --dry-run

Notes:
- Reads all ingestion jobs and phase rows, then applies the same deterministic
  aggregation rules used by the repository to set `job.status`.
- Supports `--dry-run` to preview changes without persisting.
- Logs a concise summary of updates for auditing.
"""

from __future__ import annotations

import argparse
import logging
from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config.settings import get_engine
from backend.app.ingestion.models import IngestionJob
from backend.app.ingestion.infrastructure import repository as ingestion_repo


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def recompute_all_jobs(dry_run: bool = False, verbose: bool = False) -> Tuple[int, List[str]]:
    """Recompute job.status for all jobs using repository canonical rules.

    Returns a tuple of (updated_count, messages).
    """
    setup_logging(verbose)
    engine = get_engine()
    messages: List[str] = []
    updated_count = 0

    with Session(engine) as session:
        jobs: List[IngestionJob] = session.execute(select(IngestionJob)).scalars().all()
        logging.info("Found %d ingestion jobs to evaluate", len(jobs))

        for job in jobs:
            # Compute new canonical status without mutating first (dry-run support)
            new_status = ingestion_repo.recompute_job_status_preview(session, job)
            old_status = job.status

            if new_status != old_status:
                msg = f"job_id={job.id} kb_id={job.kb_id} status {old_status} -> {new_status}"
                messages.append(msg)
                logging.info(msg)

                if not dry_run:
                    # Persist via repository helper to ensure consistent side-effects if any
                    ingestion_repo.update_job_status(session, job.id, new_status)
                    updated_count += 1
            else:
                logging.debug(
                    "job_id=%s kb_id=%s status unchanged: %s", job.id, job.kb_id, old_status
                )

        if not dry_run:
            session.commit()

    return updated_count, messages


def main() -> None:
    parser = argparse.ArgumentParser(description="Recompute and persist ingestion job statuses")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without persisting",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    updated, messages = recompute_all_jobs(dry_run=args.dry_run, verbose=args.verbose)
    summary = f"Updated {updated} jobs" if not args.dry_run else "Dry-run completed"
    print(summary)
    if messages:
        print("Changes:")
        for m in messages:
            print(f"- {m}")


if __name__ == "__main__":
    main()
