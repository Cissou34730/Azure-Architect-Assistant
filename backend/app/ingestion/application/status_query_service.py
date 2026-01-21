from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ingestion.domain.models import PhaseState
from app.ingestion.infrastructure import create_job_repository, create_phase_repository

CANONICAL_PHASES = ['loading', 'chunking', 'embedding', 'indexing']


@dataclass
class KBPersistedStatus:
    kb_id: str
    status: str  # ready | pending | not_ready
    current_phase: str | None
    overall_progress: int
    phase_details: list[dict[str, Any]]


class StatusQueryService:
    """Persisted-only KB status derivation (no runtime, no index_ready)."""

    def __init__(self) -> None:
        self.job_repo = create_job_repository()
        self.phase_repo = create_phase_repository()

    def _build_phase_details(self, phase_map: dict[str, PhaseState]) -> list[dict[str, Any]]:
        """Construct phase_details in canonical order."""
        phase_details: list[dict[str, Any]] = []
        for name in CANONICAL_PHASES:
            ps = phase_map.get(name)
            if ps:
                phase_details.append(
                    {
                        'name': name,
                        'status': ps.status.value,
                        'progress': ps.progress,
                        'items_processed': ps.items_processed,
                        'items_total': ps.items_total or 0,
                        'started_at': ps.started_at,
                        'completed_at': ps.completed_at,
                        'error': ps.error,
                    }
                )
            else:
                phase_details.append(
                    {
                        'name': name,
                        'status': 'not_started',
                        'progress': 0,
                        'items_processed': 0,
                        'items_total': 0,
                        'started_at': None,
                        'completed_at': None,
                        'error': None,
                    }
                )
        return phase_details

    def _derive_kb_status(self, job_status: str | None) -> str:
        """Map job status to KB-level derived status."""
        if job_status is None:
            return 'not_ready'

        mapping = {
            'completed': 'ready',
            'running': 'pending',
            'paused': 'paused',
            'not_started': 'not_ready',
            'canceled': 'not_ready',
            'failed': 'not_ready',
        }
        return mapping.get(job_status, 'not_ready')

    def _find_current_phase(self, phase_details: list[dict[str, Any]]) -> str:
        """Determine current active phase from phase details or default to last."""
        for name in CANONICAL_PHASES:
            pd = next((p for p in phase_details if p["name"] == name), None)
            if pd and pd["status"] != "completed":
                return name
        return CANONICAL_PHASES[-1]

    def _calculate_overall_progress(
        self, derived_status: str, phase_details: list[dict[str, Any]]
    ) -> int:
        """Calculate average progress across canonical phases."""
        if derived_status == "ready":
            return 100
        if not phase_details:
            return 0
        return int(sum(p["progress"] for p in phase_details) / len(phase_details))

    def get_status(self, kb_id: str) -> KBPersistedStatus:
        """Retrieve persisted knowledge base status and phase progress."""
        # Resolve latest job record to obtain job_id and DB job.status
        latest = self.job_repo.get_latest_job(kb_id)
        job_id = latest.job_id if latest else None

        # Load phases by job_id
        phase_map: dict[str, PhaseState] = {}
        if job_id:
            phase_map = self.phase_repo.get_all_phase_statuses(job_id)

        # Build phase_details in canonical order
        phase_details = self._build_phase_details(phase_map)

        # Use persisted job.status mapped to KB-level (ready|pending|not_ready)
        derived = self._derive_kb_status(latest.status if latest else None)

        return KBPersistedStatus(
            kb_id=kb_id,
            status=derived,
            current_phase=self._find_current_phase(phase_details),
            overall_progress=self._calculate_overall_progress(derived, phase_details),
            phase_details=phase_details,
        )
