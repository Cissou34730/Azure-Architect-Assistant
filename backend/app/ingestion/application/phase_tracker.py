from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from app.ingestion.domain.enums import JobPhase, PhaseStatus
from app.ingestion.domain.models import PhaseState
from app.ingestion.infrastructure.repository import DatabaseRepository


class PhaseTracker:
    """Service to manage per-phase lifecycle and persistence."""

    def __init__(self, repository: DatabaseRepository) -> None:
        self.repository = repository

    def initialize_phases(self, job_id: str) -> None:
        self.repository.initialize_phase_statuses(job_id)

    def start_phase(self, job_id: str, phase_name: str) -> None:
        self.repository.update_phase_status(
            job_id=job_id,
            phase_name=phase_name,
            status=PhaseStatus.RUNNING.value,
        )

    def pause_phase(self, job_id: str, phase_name: str) -> None:
        self.repository.update_phase_status(
            job_id=job_id,
            phase_name=phase_name,
            status=PhaseStatus.PAUSED.value,
        )

    def complete_phase(self, job_id: str, phase_name: str) -> None:
        self.repository.update_phase_status(
            job_id=job_id,
            phase_name=phase_name,
            status=PhaseStatus.COMPLETED.value,
            progress_percent=100,
        )

    def fail_phase(self, job_id: str, phase_name: str, error: str) -> None:
        self.repository.update_phase_status(
            job_id=job_id,
            phase_name=phase_name,
            status=PhaseStatus.FAILED.value,
            error_message=error,
        )

    def update_progress(
        self,
        job_id: str,
        phase_name: str,
        progress: Optional[int] = None,
        items_processed: Optional[int] = None,
        items_total: Optional[int] = None,
    ) -> None:
        self.repository.update_phase_status(
            job_id=job_id,
            phase_name=phase_name,
            status=self._current_status(job_id, phase_name).value,
            progress_percent=progress if progress is not None else None,
            items_processed=items_processed if items_processed is not None else None,
            items_total=items_total if items_total is not None else None,
        )

    def get_consolidated_status(self, job_id: str) -> Dict[str, PhaseState]:
        return self.repository.get_all_phase_statuses(job_id)

    def _current_status(self, job_id: str, phase_name: str) -> PhaseStatus:
        phase = self.repository.get_phase_status(job_id, phase_name)
        return phase.status if phase else PhaseStatus.NOT_STARTED
