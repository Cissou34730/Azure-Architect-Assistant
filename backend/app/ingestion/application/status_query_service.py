from __future__ import annotations

from typing import Dict, Any, List
from dataclasses import dataclass

from app.kb.knowledge_base_manager import KBManager
from app.ingestion.infrastructure.repository import create_database_repository


CANONICAL_PHASES = ["loading", "chunking", "embedding", "indexing"]


@dataclass
class PersistedStatus:
    kb_id: str
    status: str
    current_phase: str | None
    overall_progress: int
    phase_details: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    index_ready: bool


class StatusQueryService:
    def __init__(self, kb_manager: KBManager):
        self.kb_manager = kb_manager
        self.repo = create_database_repository()

    def get_status(self, kb_id: str) -> PersistedStatus:
        index_ready = False
        try:
            index_ready = self.kb_manager.is_index_ready(kb_id)
        except Exception:
            index_ready = False

        # Queue metrics (persisted)
        metrics: Dict[str, Any] = {}
        try:
            qs = self.repo.get_queue_stats(job_id=kb_id)
            metrics = {
                'chunks_pending': qs.get('pending', 0),
                'chunks_processing': qs.get('processing', 0),
                'chunks_done': qs.get('done', 0),
                'chunks_error': qs.get('error', 0),
                'chunks_queued': sum(qs.values()) if qs else 0,
            }
        except Exception:
            metrics = {}

        # Phase rows from DB
        phase_rows: Dict[str, Dict[str, Any]] = {}
        try:
            rows = self.repo.get_all_phase_statuses(job_id=kb_id)
            for r in rows:
                phase_rows[r['phase_name']] = r
        except Exception:
            phase_rows = {}

        # Build phase_details (default missing phases)
        phase_details: List[Dict[str, Any]] = []
        for name in CANONICAL_PHASES:
            pr = phase_rows.get(name)
            if pr:
                phase_details.append({
                    'name': name,
                    'status': pr.get('status', 'not_started'),
                    'progress': pr.get('progress_percent', 0),
                    'items_processed': pr.get('items_processed', 0),
                    'items_total': pr.get('items_total', 0) or 0,
                    'started_at': pr.get('started_at'),
                    'completed_at': pr.get('completed_at'),
                    'error': pr.get('error_message'),
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

        # Derive overall status
        statuses = [pd['status'] for pd in phase_details]
        if index_ready or (statuses and all(s == 'completed' for s in statuses)):
            status = 'completed'
        elif any(s == 'failed' for s in statuses):
            status = 'failed'
        elif any(s == 'paused' for s in statuses):
            status = 'paused'
        elif any(s == 'running' for s in statuses):
            status = 'running'
        elif any(s != 'not_started' for s in statuses):
            status = 'pending'
        else:
            status = 'pending'

        # Current phase: first non-completed canonical, else last
        current_phase = None
        for name in CANONICAL_PHASES:
            pd = next((p for p in phase_details if p['name'] == name), None)
            if pd and pd['status'] != 'completed':
                current_phase = name
                break
        if not current_phase:
            current_phase = CANONICAL_PHASES[-1]

        # Overall progress: average of phase progress
        overall_progress = 100 if status == 'completed' else int(
            sum(p['progress'] for p in phase_details) / len(phase_details)
        )

        return PersistedStatus(
            kb_id=kb_id,
            status=status,
            current_phase=current_phase,
            overall_progress=overall_progress,
            phase_details=phase_details,
            metrics=metrics,
            index_ready=index_ready,
        )
