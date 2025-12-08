from __future__ import annotations

from typing import Dict, Any, List
from dataclasses import dataclass

from app.ingestion.infrastructure.repository import create_database_repository
from app.ingestion.domain.models import PhaseState


CANONICAL_PHASES = ["loading", "chunking", "embedding", "indexing"]


@dataclass
class KBPersistedStatus:
    kb_id: str
    status: str  # ready | pending | not_ready
    current_phase: str | None
    overall_progress: int
    phase_details: List[Dict[str, Any]]


class StatusQueryService:
    """Persisted-only KB status derivation (no runtime, no index_ready)."""

    def __init__(self):
        self.repo = create_database_repository()

    def get_status(self, kb_id: str) -> KBPersistedStatus:
        # Resolve latest job to obtain job_id
        state = self.repo.get_latest_job(kb_id)
        job_id = state.job_id if state else None

        # Load phases by job_id
        phase_map: Dict[str, PhaseState] = {}
        if job_id:
            phase_map = self.repo.get_all_phase_statuses(job_id)

        # Build phase_details in canonical order
        phase_details: List[Dict[str, Any]] = []
        for name in CANONICAL_PHASES:
            ps = phase_map.get(name)
            if ps:
                phase_details.append({
                    'name': name,
                    'status': ps.status.value,
                    'progress': ps.progress,
                    'items_processed': ps.items_processed,
                    'items_total': ps.items_total or 0,
                    'started_at': ps.started_at,
                    'completed_at': ps.completed_at,
                    'error': ps.error,
                })
            else:
                phase_details.append({
                    'name': name,
                    'status': 'not_started',
                    'progress': 0,
                    'items_processed': 0,
                    'items_total': 0,
                    'started_at': None,
                    'completed_at': None,
                    'error': None,
                })

        statuses = [pd['status'] for pd in phase_details]
        if job_id is None or all(s == 'not_started' for s in statuses):
            derived = 'not_ready'
        elif all(s == 'completed' for s in statuses):
            derived = 'ready'
        elif any(s in ('running', 'paused') for s in statuses):
            derived = 'pending'
        else:
            # Mixed completed/not_started without active phases still indicates pending work
            derived = 'pending'

        # Current phase: first non-completed canonical, else last
        current_phase = None
        for name in CANONICAL_PHASES:
            pd = next((p for p in phase_details if p['name'] == name), None)
            if pd and pd['status'] != 'completed':
                current_phase = name
                break
        if not current_phase:
            current_phase = CANONICAL_PHASES[-1]

        # Overall progress: average of phase progress; 100 if ready
        overall_progress = 100 if derived == 'ready' else int(
            sum(p['progress'] for p in phase_details) / len(phase_details)
        )

        return KBPersistedStatus(
            kb_id=kb_id,
            status=derived,
            current_phase=current_phase,
            overall_progress=overall_progress,
            phase_details=phase_details,
        )
