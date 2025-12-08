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
        # Resolve latest job record to obtain job_id and DB job.status
        latest = self.repo.get_latest_job(kb_id)
        job_id = latest.job_id if latest else None

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

        # Use persisted job.status mapped to KB-level (ready|pending|not_ready)
        if latest is None:
            derived = 'not_ready'
        else:
            job_status = latest.status  # domain mapping: 'pending'|'running'|'completed'|'failed'
            if job_status == 'completed':
                derived = 'ready'
            elif job_status in ('pending', 'running'):
                derived = 'pending'
            else:
                # 'failed' or any unknown maps to not_ready for KB-level readiness
                derived = 'not_ready'

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
