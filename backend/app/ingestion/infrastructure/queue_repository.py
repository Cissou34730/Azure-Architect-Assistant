"""
Queue repository for chunk-level work items.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from sqlalchemy import delete, func, select

from app.ingestion.domain.errors import DuplicateChunkError
from app.ingestion.ingestion_database import get_session
from app.ingestion.models import (
    IngestionJob,
    IngestionQueueItem,
    QueueStatus,
)


class QueueRepository:
    """SQLAlchemy-based repository for queue persistence."""

    def enqueue_chunks(self, job_id: str, chunks: list[dict[str, Any]]) -> None:
        """Enqueue chunks for processing."""
        with get_session() as session:
            for chunk in chunks:
                item = IngestionQueueItem(
                    job_id=job_id,
                    doc_hash=chunk['doc_hash'],
                    content=chunk['content'],
                    item_metadata=chunk.get('metadata', {}),
                )
                session.add(item)

    def dequeue_batch(self, batch_size: int = 50) -> list[IngestionQueueItem]:
        """Fetch a batch of pending items and mark them processing."""
        with get_session() as session:
            stmt = (
                select(IngestionQueueItem)
                .where(IngestionQueueItem.status == QueueStatus.PENDING.value)
                .order_by(IngestionQueueItem.available_at)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )
            result = session.execute(stmt)
            pending = result.scalars().all()
            for item in pending:
                item.mark_processing()
            return cast(list[IngestionQueueItem], pending)

    def mark_done(self, item_id: int) -> None:
        with get_session() as session:
            item = session.get(IngestionQueueItem, item_id)
            if item:
                item.mark_done()

    def mark_error(self, item_id: int, message: str) -> None:
        with get_session() as session:
            item = session.get(IngestionQueueItem, item_id)
            if item:
                item.mark_error(message)

    def get_queue_stats(self, job_id: str) -> dict[str, int]:
        """Return counts per status for a job."""
        with get_session() as session:
            result = session.execute(
                select(IngestionQueueItem.status, func.count())
                .where(IngestionQueueItem.job_id == job_id)
                .group_by(IngestionQueueItem.status)
            )
            stats = {row[0].lower(): row[1] for row in result.all()}
            stats.setdefault('pending', 0)
            stats.setdefault('processing', 0)
            stats.setdefault('done', 0)
            stats.setdefault('error', 0)
            return stats

    def pause_current_phase(self, kb_id: str) -> None:
        """Mark current phase paused for latest job."""
        with get_session() as session:
            stmt = (
                select(IngestionJob)
                .where(IngestionJob.kb_id == kb_id)
                .order_by(IngestionJob.created_at.desc())
                .limit(1)
            )
            result = session.execute(stmt)
            job = result.scalar_one_or_none()
            if not job:
                return
            job.status = QueueStatus.PAUSED.value if hasattr(QueueStatus, 'PAUSED') else job.status
            job.updated_at = datetime.now(timezone.utc)

    def resume_current_phase(self, kb_id: str) -> None:
        """Mark current phase running for latest job."""
        with get_session() as session:
            stmt = (
                select(IngestionJob)
                .where(IngestionJob.kb_id == kb_id)
                .order_by(IngestionJob.created_at.desc())
                .limit(1)
            )
            result = session.execute(stmt)
            job = result.scalar_one_or_none()
            if not job:
                return
            job.status = QueueStatus.PROCESSING.value
            job.updated_at = datetime.now(timezone.utc)

    def cancel_job_and_reset(self, kb_id: str) -> None:
        """Cancel latest job for KB and reset queue."""
        with get_session() as session:
            stmt = (
                select(IngestionJob)
                .where(IngestionJob.kb_id == kb_id)
                .order_by(IngestionJob.created_at.desc())
                .limit(1)
            )
            result = session.execute(stmt)
            job = result.scalar_one_or_none()
            if not job:
                return
            job.status = QueueStatus.DONE.value if hasattr(QueueStatus, 'DONE') else job.status
            job.updated_at = datetime.now(timezone.utc)
            delete_stmt = delete(IngestionQueueItem).where(IngestionQueueItem.job_id == job.id)
            session.execute(delete_stmt)

    def recover_inflight_jobs(self) -> None:
        """Recover jobs stuck in RUNNING state by marking them paused."""
        with get_session() as session:
            stmt = select(IngestionJob).where(IngestionJob.status == QueueStatus.PROCESSING.value)
            result = session.execute(stmt)
            jobs = result.scalars().all()
            for job in jobs:
                job.status = (
                    QueueStatus.PAUSED.value if hasattr(QueueStatus, 'PAUSED') else job.status
                )
                job.updated_at = datetime.now(timezone.utc)

    def add_queue_item(
        self,
        job_id: str,
        doc_hash: str,
        content: str,
        item_metadata: dict[str, Any],
        status: str = QueueStatus.PENDING.value,
    ) -> int:
        """Add a queue item; raises DuplicateChunkError on constraint violation."""
        with get_session() as session:
            item = IngestionQueueItem(
                job_id=job_id,
                doc_hash=doc_hash,
                content=content,
                item_metadata=item_metadata,
                status=status,
                attempts=0,
            )
            session.add(item)
            try:
                session.flush()
            except Exception as exc:
                raise DuplicateChunkError(
                    f'Duplicate chunk for job_id={job_id}, doc_hash={doc_hash}'
                ) from exc
            return cast(int, item.id)


def create_queue_repository() -> QueueRepository:
    return QueueRepository()
