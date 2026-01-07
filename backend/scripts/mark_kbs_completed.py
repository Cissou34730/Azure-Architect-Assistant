"""Utility script to retroactively mark specific KB ingestion jobs as completed.

Usage:
  - Run from repo root with activated venv.
  - Optionally pass KB IDs via args; defaults to ["waf", "nist-sp"].
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List
from datetime import datetime, timezone

# Ensure backend package is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select  # noqa: E402

from app.ingestion.ingestion_database import get_session, init_ingestion_database  # noqa: E402
from app.ingestion.models import (  # noqa: E402
    IngestionJob,
    IngestionPhaseStatus,
    JobStatus,
    PhaseStatusDB,
)


def mark_completed(kb_ids: List[str]) -> None:
    init_ingestion_database()
    with get_session() as session:
        jobs = (
            session.execute(select(IngestionJob).where(IngestionJob.kb_id.in_(kb_ids)))
            .scalars()
            .all()
        )

        if not jobs:
            # Create jobs if they do not exist
            for kb_id in kb_ids:
                job = IngestionJob(
                    kb_id=kb_id,
                    status=JobStatus.COMPLETED.value,
                    source_type="manual",
                    source_config={},
                    priority=0,
                    total_items=0,
                    processed_items=0,
                    current_phase="indexing",
                )
                session.add(job)
                jobs.append(job)
            # Ensure IDs are generated
            session.flush()

        for job in jobs:
            job.status = JobStatus.COMPLETED.value
            job.current_phase = "indexing"
            job.updated_at = datetime.now(timezone.utc)

            phases = (
                session.execute(
                    select(IngestionPhaseStatus).where(
                        IngestionPhaseStatus.job_id == job.id
                    )
                )
                .scalars()
                .all()
            )

            # Ensure all canonical phases exist and are completed
            canonical = ["loading", "chunking", "embedding", "indexing"]
            existing = {p.phase_name: p for p in phases}
            for name in canonical:
                phase = existing.get(name)
                if not phase:
                    phase = IngestionPhaseStatus(job_id=job.id, phase_name=name)
                    session.add(phase)
                phase.status = PhaseStatusDB.COMPLETED.value
                phase.progress_percent = 100
                phase.completed_at = datetime.now(timezone.utc)
                phase.updated_at = datetime.now(timezone.utc)

        session.commit()
        print(f"Marked {len(jobs)} job(s) as COMPLETED: {[j.kb_id for j in jobs]}")


if __name__ == "__main__":
    kb_ids = sys.argv[1:] if len(sys.argv) > 1 else ["waf", "nist-sp"]
    mark_completed(kb_ids)
