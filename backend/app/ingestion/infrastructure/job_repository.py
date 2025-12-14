"""
Job repository for orchestrator-based ingestion.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import select, update

from app.ingestion.ingestion_database import get_session
from app.ingestion.models import (
    IngestionJob,
    IngestionPhaseStatus,
    JobStatus as DBJobStatus,
)
from app.ingestion.domain.models import IngestionState, PhaseState
from app.ingestion.domain.enums import JobPhase, PhaseStatus
from app.ingestion.domain.errors import JobNotFoundError


class JobRepository:
    """SQLAlchemy-based repository for job persistence."""

    def create_job(
        self,
        kb_id: str,
        source_type: str,
        source_config: Dict[str, Any],
        priority: int = 0,
    ) -> str:
        """Create a new ingestion job and return its ID."""
        now = datetime.utcnow()
        with get_session() as session:
            job = IngestionJob(
                kb_id=kb_id,
                status=DBJobStatus.RUNNING.value,
                source_type=source_type,
                source_config=source_config,
                created_at=now,
                updated_at=now,
                total_items=0,
                processed_items=0,
                priority=priority,
                current_phase="loading",
                phase_progress={},
            )
            session.add(job)
            session.flush()
            job_id = job.id

        self.initialize_phase_statuses(job_id)
        return job_id

    def get_latest_job(self, kb_id: str) -> Optional[IngestionState]:
        """Get the most recent job for a knowledge base."""
        with get_session() as session:
            result = session.execute(
                select(IngestionJob)
                .where(IngestionJob.kb_id == kb_id)
                .order_by(IngestionJob.created_at.desc())
                .limit(1)
            )
            job = result.scalars().first()
            if not job:
                return None
            return self._job_to_state(job)

    def get_latest_job_record(self, kb_id: str) -> Optional[IngestionJob]:
        """Return the latest ORM job record for a KB (raw DB model)."""
        with get_session() as session:
            result = session.execute(
                select(IngestionJob)
                .where(IngestionJob.kb_id == kb_id)
                .order_by(IngestionJob.created_at.desc())
                .limit(1)
            )
            return result.scalars().first()

    def get_latest_job_id(self, kb_id: str) -> Optional[str]:
        """Return the latest job_id (UUID) for a KB."""
        with get_session() as session:
            result = session.execute(
                select(IngestionJob.id)
                .where(IngestionJob.kb_id == kb_id)
                .order_by(IngestionJob.created_at.desc())
                .limit(1)
            )
            row = result.first()
            return row[0] if row else None

    def update_job_status(self, job_id: str, status: str) -> None:
        """Update job status and timestamp (expects canonical job statuses)."""
        status_map = {
            "not_started": DBJobStatus.NOT_STARTED.value,
            "running": DBJobStatus.RUNNING.value,
            "paused": DBJobStatus.PAUSED.value,
            "completed": DBJobStatus.COMPLETED.value,
            "failed": DBJobStatus.FAILED.value,
            "canceled": DBJobStatus.CANCELED.value,
        }
        db_status = status_map.get(status, DBJobStatus.NOT_STARTED.value)

        with get_session() as session:
            session.execute(
                update(IngestionJob)
                .where(IngestionJob.id == job_id)
                .values(status=db_status, updated_at=datetime.utcnow())
            )

    def initialize_phase_statuses(self, job_id: str) -> None:
        """Initialize phase status records for all phases (idempotent)."""
        with get_session() as session:
            existing = session.execute(
                select(IngestionPhaseStatus.phase_name).where(IngestionPhaseStatus.job_id == job_id)
            ).scalars().all()
            existing_set = set(existing)
            for phase in JobPhase:
                if phase.value in existing_set:
                    continue
                phase_status = IngestionPhaseStatus(
                    job_id=job_id,
                    phase_name=phase.value,
                    status=PhaseStatus.NOT_STARTED.value,
                )
                session.add(phase_status)

    def set_job_status(
        self,
        job_id: str,
        status: str,
        finished_at: datetime | None = None,
        last_error: str | None = None,
    ) -> None:
        """Set job status and optional completion info."""
        with get_session() as session:
            job = session.get(IngestionJob, job_id)
            if not job:
                raise JobNotFoundError(f"Job not found: {job_id}")
            job.status = status
            job.finished_at = finished_at
            job.last_error = last_error
            job.updated_at = datetime.utcnow()

    def update_job(
        self,
        job_id: str,
        *,
        status: Optional[str] = None,
        checkpoint: Optional[Dict[str, Any]] = None,
        counters: Optional[Dict[str, Any]] = None,
        finished_at: Optional[datetime] = None,
        last_error: Optional[str] = None,
    ) -> None:
        """Update job fields."""
        with get_session() as session:
            job = session.get(IngestionJob, job_id)
            if not job:
                raise JobNotFoundError(f"Job not found: {job_id}")

            if status is not None:
                job.status = status
            if checkpoint is not None:
                job.checkpoint = checkpoint
            if counters is not None:
                job.counters = counters
            if finished_at is not None:
                job.finished_at = finished_at
            if last_error is not None:
                job.last_error = last_error
            job.updated_at = datetime.utcnow()

    def update_heartbeat(self, job_id: str) -> None:
        """Update job heartbeat timestamp."""
        with get_session() as session:
            session.execute(
                update(IngestionJob)
                .where(IngestionJob.id == job_id)
                .values(heartbeat_at=datetime.utcnow())
            )

    def get_job(self, job_id: str) -> IngestionJob:
        """Fetch job by id."""
        with get_session() as session:
            job = session.get(IngestionJob, job_id)
            if not job:
                raise JobNotFoundError(f"Job not found: {job_id}")
            return job

    def _job_to_state(self, job: IngestionJob) -> IngestionState:
        """Convert ORM job to domain state."""
        return IngestionState(
            job_id=job.id,
            kb_id=job.kb_id,
            status=job.status.lower(),
            created_at=job.created_at,
            updated_at=job.updated_at,
            phase=job.current_phase,
            progress=job.processed_items,
        )


def create_job_repository() -> JobRepository:
    return JobRepository()
