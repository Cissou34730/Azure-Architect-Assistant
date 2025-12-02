"""Database helpers for ingestion job persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import select, update

from app.ingestion.db import get_session
from app.ingestion.models import (
    IngestionJob,
    IngestionQueueItem,
    JobStatus,
    QueueStatus,
)
from .state import IngestionState


def create_job_record(
    kb_id: str,
    source_type: str,
    source_config: Dict[str, Any],
    priority: int,
) -> str:
    """Persist a new ingestion job and return its identifier."""

    now = datetime.utcnow()
    with get_session() as session:
        job = IngestionJob(
            kb_id=kb_id,
            status=JobStatus.RUNNING.value,
            source_type=source_type,
            source_config=source_config,
            created_at=now,
            updated_at=now,
            total_items=0,
            processed_items=0,
            priority=priority,
        )
        session.add(job)
        session.flush()
        return job.id


def update_job_status(job_id: str, status: JobStatus) -> None:
    """Update job status and touch the updated timestamp."""

    with get_session() as session:
        session.execute(
            update(IngestionJob)
            .where(IngestionJob.id == job_id)
            .values(status=status.value, updated_at=datetime.utcnow())
        )


def get_latest_job_record(kb_id: str) -> Optional[IngestionJob]:
    """Return the most recent job for the given knowledge base."""

    with get_session() as session:
        result = session.execute(
            select(IngestionJob)
            .where(IngestionJob.kb_id == kb_id)
            .order_by(IngestionJob.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()


def job_to_state(job: IngestionJob) -> IngestionState:
    """Convert a persisted job record to an in-memory state."""

    status_map = {
        JobStatus.PENDING.value: "pending",
        JobStatus.RUNNING.value: "running",
        JobStatus.PAUSED.value: "paused",
        JobStatus.COMPLETED.value: "completed",
        JobStatus.FAILED.value: "failed",
        JobStatus.CANCELED.value: "cancelled",
    }
    status = status_map.get(job.status, "pending")
    completed_at = (
        job.updated_at
        if job.status
        in {JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELED.value}
        else None
    )
    return IngestionState(
        kb_id=job.kb_id,
        job_id=job.id,
        status=status,
        phase="crawling",
        progress=0,
        metrics={},
        message="Recovered job",
        error=None,
        paused=job.status == JobStatus.PAUSED.value,
        cancel_requested=job.status == JobStatus.CANCELED.value,
        created_at=job.created_at,
        started_at=job.updated_at,
        completed_at=completed_at,
    )


def recover_inflight_jobs() -> None:
    """Reset any processing queue items and mark inflight jobs as paused on startup."""

    now = datetime.utcnow()
    with get_session() as session:
        session.execute(
            update(IngestionQueueItem)
            .where(IngestionQueueItem.status == QueueStatus.PROCESSING.value)
            .values(status=QueueStatus.PENDING.value, updated_at=now)
        )
        session.execute(
            update(IngestionJob)
            .where(IngestionJob.status == JobStatus.RUNNING.value)
            .values(status=JobStatus.PAUSED.value, updated_at=now)
        )


def enqueue_chunks(job_id: str, chunks: list[Dict[str, Any]]) -> int:
    """Insert chunks into ingestion_queue as PENDING; deduplicate by (job_id, doc_hash).

    Returns number of rows inserted (skips duplicates).
    """
    inserted = 0
    now = datetime.utcnow()
    with get_session() as session:
        for ch in chunks:
            try:
                item = IngestionQueueItem(
                    job_id=job_id,
                    doc_hash=ch["doc_hash"],
                    content=ch["content"],
                    item_metadata=ch.get("metadata", {}),
                    status=QueueStatus.PENDING.value,
                    created_at=now,
                    updated_at=now,
                    available_at=now,
                )
                session.add(item)
                session.flush()
                inserted += 1
            except Exception:
                session.rollback()
                # Likely duplicate doc_hash for this job; skip
                continue
        # Update job totals
        session.execute(
            update(IngestionJob)
            .where(IngestionJob.id == job_id)
            .values(total_items=IngestionJob.total_items + inserted, updated_at=now)
        )
    return inserted


def dequeue_batch(job_id: str, limit: int = 10) -> list[IngestionQueueItem]:
    """Atomically select next PENDING items for a job and mark them PROCESSING."""
    with get_session() as session:
        items = (
            session.execute(
                select(IngestionQueueItem)
                .where(
                    IngestionQueueItem.job_id == job_id,
                    IngestionQueueItem.status == QueueStatus.PENDING.value,
                )
                .order_by(IngestionQueueItem.id.asc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
        for it in items:
            it.mark_processing()
        session.flush()
        return items


def commit_batch_success(job_id: str, item_ids: list[int]) -> None:
    """Mark items DONE and increment processed_items on job."""
    now = datetime.utcnow()
    with get_session() as session:
        session.execute(
            update(IngestionQueueItem)
            .where(IngestionQueueItem.id.in_(item_ids))
            .values(status=QueueStatus.DONE.value, updated_at=now)
        )
        session.execute(
            update(IngestionJob)
            .where(IngestionJob.id == job_id)
            .values(processed_items=IngestionJob.processed_items + len(item_ids), updated_at=now)
        )


def commit_batch_error(item_id: int, message: str) -> None:
    """Mark single item ERROR and increment attempts with error_log."""
    with get_session() as session:
        session.execute(
            update(IngestionQueueItem)
            .where(IngestionQueueItem.id == item_id)
            .values(
                status=QueueStatus.ERROR.value,
                error_log=message,
                attempts=IngestionQueueItem.attempts + 1,
                updated_at=datetime.utcnow(),
            )
        )
