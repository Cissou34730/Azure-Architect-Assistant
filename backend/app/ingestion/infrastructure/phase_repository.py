"""
Phase status repository.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy import select

from app.ingestion.ingestion_database import get_session
from app.ingestion.models import IngestionPhaseStatus, PhaseStatusDB
from app.ingestion.domain.models import PhaseState
from app.ingestion.domain.enums import PhaseStatus


class PhaseRepository:
    """Persisted phase tracking."""

    def get_phase_status(self, job_id: str, phase_name: str) -> Optional[PhaseState]:
        with get_session() as session:
            result = session.execute(
                select(IngestionPhaseStatus).where(
                    IngestionPhaseStatus.job_id == job_id, IngestionPhaseStatus.phase_name == phase_name
                )
            )
            db_phase = result.scalars().first()
            if not db_phase:
                return None
            return self._db_phase_to_domain(db_phase)

    def get_all_phase_statuses(self, job_id: str) -> Dict[str, PhaseState]:
        with get_session() as session:
            result = session.execute(
                select(IngestionPhaseStatus).where(IngestionPhaseStatus.job_id == job_id)
            )
            phases = result.scalars().all()
            return {p.phase_name: self._db_phase_to_domain(p) for p in phases}

    def start_phase(self, job_id: str, phase_name: str) -> None:
        with get_session() as session:
            phase = session.execute(
                select(IngestionPhaseStatus).where(
                    IngestionPhaseStatus.job_id == job_id, IngestionPhaseStatus.phase_name == phase_name
                )
            ).scalars().first()
            if phase:
                phase.status = PhaseStatusDB.RUNNING.value
                phase.started_at = datetime.now(timezone.utc)

    def complete_phase(self, job_id: str, phase_name: str) -> None:
        with get_session() as session:
            phase = session.execute(
                select(IngestionPhaseStatus).where(
                    IngestionPhaseStatus.job_id == job_id, IngestionPhaseStatus.phase_name == phase_name
                )
            ).scalars().first()
            if phase:
                phase.status = PhaseStatusDB.COMPLETED.value
                phase.completed_at = datetime.now(timezone.utc)
                phase.progress_percent = 100

    def update_progress(
        self,
        job_id: str,
        phase_name: str,
        *,
        progress: Optional[int] = None,
        items_processed: Optional[int] = None,
        items_total: Optional[int] = None,
    ) -> None:
        """
        Update phase progress and mark status as running.
        """
        with get_session() as session:
            phase = session.execute(
                select(IngestionPhaseStatus).where(
                    IngestionPhaseStatus.job_id == job_id, IngestionPhaseStatus.phase_name == phase_name
                )
            ).scalars().first()
            if not phase:
                return

            phase.status = PhaseStatusDB.RUNNING.value
            if progress is not None:
                phase.progress_percent = progress
            if items_processed is not None:
                phase.items_processed = items_processed
            if items_total is not None:
                phase.items_total = items_total
            if phase.started_at is None:
                phase.started_at = datetime.now(timezone.utc)

    def fail_phase(self, job_id: str, phase_name: str, error_message: str) -> None:
        with get_session() as session:
            phase = session.execute(
                select(IngestionPhaseStatus).where(
                    IngestionPhaseStatus.job_id == job_id, IngestionPhaseStatus.phase_name == phase_name
                )
            ).scalars().first()
            if phase:
                phase.status = PhaseStatusDB.FAILED.value
                phase.error_message = error_message
                phase.completed_at = datetime.now(timezone.utc)

    def _db_phase_to_domain(self, db_phase: IngestionPhaseStatus) -> PhaseState:
        return PhaseState(
            phase_name=db_phase.phase_name,
            status=PhaseStatus(db_phase.status),
            progress=db_phase.progress_percent,
            items_processed=db_phase.items_processed,
            items_total=db_phase.items_total,
            started_at=db_phase.started_at,
            completed_at=db_phase.completed_at,
            error=db_phase.error_message,
        )


def create_phase_repository() -> PhaseRepository:
    return PhaseRepository()
