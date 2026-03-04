"""Read-side ingestion service used by router endpoints.

Keeps repository/status orchestration out of transport handlers.
"""

from __future__ import annotations

import logging
from typing import Any

from app.ingestion.application.status_query_service import StatusQueryService
from app.ingestion.infrastructure import create_job_repository, create_queue_repository
from app.services.ingestion_metrics_service import (
    IngestionMetrics,
    QueueMetrics,
    derive_job_status,
    get_job_counters,
    get_status_message,
    normalize_job_metrics,
)

logger = logging.getLogger(__name__)


class IngestionReadService:
    """Query-only ingestion orchestration for API read endpoints."""

    def __init__(self) -> None:
        self._status_service = StatusQueryService()
        self._job_repo = create_job_repository()
        self._queue_repo = create_queue_repository()

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Return raw job status dict; raises ValueError if job not found."""
        job = self._job_repo.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        status = self._job_repo.get_job_status(job_id)
        return {
            "job_id": job.id,
            "kb_id": job.kb_id,
            "status": status,
            "counters": job.counters,
            "checkpoint": job.checkpoint,
            "last_error": job.last_error,
            "started_at": job.created_at,
            "finished_at": job.finished_at,
        }

    def get_kb_ingestion_details(self, kb_id: str) -> dict[str, Any]:
        status = self._status_service.get_status(kb_id)
        counters: dict[str, Any] = {}

        try:
            job_id = self._job_repo.get_latest_job_id(kb_id)
            if job_id:
                job = self._job_repo.get_job(job_id)
                if job and job.counters:
                    counters = dict(job.counters)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Unable to fetch ingestion counters for kb_id=%s: %s",
                kb_id,
                exc,
                exc_info=True,
            )

        return {
            "kb_id": kb_id,
            "status": status.status,
            "current_phase": status.current_phase,
            "overall_progress": status.overall_progress,
            "phase_details": status.phase_details,
            "counters": counters,
        }

    def get_kb_job_view(self, kb_id: str) -> dict[str, Any]:
        kb_status = self._status_service.get_status(kb_id)
        latest_job_state = self._job_repo.get_latest_job(kb_id)

        if not latest_job_state:
            return {
                "job_id": f"{kb_id}-job",
                "kb_id": kb_id,
                "status": "not_started",
                "phase": "loading",
                "progress": kb_status.overall_progress,
                "message": "Waiting to start",
                "error": None,
                "metrics": IngestionMetrics(),
                "started_at": None,
                "completed_at": None,
                "phase_details": kb_status.phase_details,
            }

        job_id = latest_job_state.job_id
        latest_job_view = self._job_repo.get_job(job_id) if job_id else None

        raw_metrics = QueueMetrics()
        if job_id:
            try:
                stats = self._queue_repo.get_queue_stats(job_id)
                raw_metrics = QueueMetrics(
                    pending=stats.get("pending", 0),
                    processing=stats.get("processing", 0),
                    done=stats.get("done", 0),
                    error=stats.get("error", 0),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Unable to fetch queue metrics for job_id=%s: %s",
                    job_id,
                    exc,
                    exc_info=True,
                )

        counters = get_job_counters(latest_job_view)
        metrics = normalize_job_metrics(kb_status, raw_metrics, counters)
        job_status = derive_job_status(latest_job_state, kb_status)
        message = get_status_message(job_status)

        return {
            "job_id": job_id,
            "kb_id": kb_id,
            "status": job_status,
            "phase": kb_status.current_phase or "loading",
            "progress": kb_status.overall_progress,
            "message": message,
            "error": latest_job_view.last_error if latest_job_view else None,
            "metrics": metrics,
            "started_at": latest_job_state.created_at,
            "completed_at": latest_job_view.finished_at if latest_job_view else None,
            "phase_details": kb_status.phase_details,
        }


_ingestion_read_service = IngestionReadService()


def get_ingestion_read_service() -> IngestionReadService:
    """Get shared ingestion read service."""
    return _ingestion_read_service
