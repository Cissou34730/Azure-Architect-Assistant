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

    # ---- Helpers expected by pipelines ----
    def has_phase_started(self, job_id: str, phase_name: str) -> bool:
        """Return True if phase status is not NOT_STARTED."""
        status = self._current_status(job_id, phase_name)
        return status != PhaseStatus.NOT_STARTED

    def is_phase_completed(self, job_id: str, phase_name: str) -> bool:
        """Return True if phase status is COMPLETED."""
        status = self._current_status(job_id, phase_name)
        return status == PhaseStatus.COMPLETED

    def get_overall_progress(self, job_id: str) -> int:
        """Compute a simple aggregate progress across phases from DB rows."""
        phases = self.repository.get_all_phase_statuses(job_id)
        if not phases:
            return 0
        # Average progress_percent across phases that have a value
        values = [p.progress for p in phases.values() if p.progress is not None]
        return int(sum(values) / len(values)) if values else 0

    def should_run_phase(self, job_id: str, phase_name: str) -> bool:
        """Return True if the phase is eligible to run (not completed/failed)."""
        status = self._current_status(job_id, phase_name)
        return status not in (PhaseStatus.COMPLETED, PhaseStatus.FAILED)

    def get_current_phase(self, job_id: str) -> Optional[str]:
        """Return the currently running phase name, if any."""
        phases = self.repository.get_all_phase_statuses(job_id)
        for name, state in phases.items():
            if state.status == PhaseStatus.RUNNING:
                return name
        return None
