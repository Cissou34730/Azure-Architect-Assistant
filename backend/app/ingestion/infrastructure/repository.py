"""Database repository implementation for ingestion jobs and queue."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update, func

from app.ingestion.ingestion_database import get_session
from app.ingestion.models import (
    IngestionJob,
    IngestionQueueItem,
    JobStatus as DBJobStatus,
    QueueStatus,
)
from app.ingestion.domain.models import IngestionState
from app.ingestion.domain.errors import DuplicateChunkError, JobNotFoundError
from app.ingestion.domain.enums import JobStatus


class DatabaseRepository:
    """SQLAlchemy-based repository for job and queue persistence."""

    def create_job(
        self,
        kb_id: str,
        source_type: str,
        source_config: Dict[str, Any],
        priority: int = 0,
    ) -> str:
        """Create a new ingestion job and return its ID."""
        now = datetime.utcnow()
        with get_session() as session:
            job = IngestionJob(
                kb_id=kb_id,
                status=DBJobStatus.RUNNING.value,
                source_type=source_type,
                source_config=source_config,
                created_at=now,
                updated_at=now,
                total_items=0,
                processed_items=0,
                priority=priority,
                current_phase="crawling",
                phase_progress={},
            )
            session.add(job)
            session.flush()
            return job.id

    def get_latest_job(self, kb_id: str) -> Optional[IngestionState]:
        """Get the most recent job for a knowledge base."""
        with get_session() as session:
            result = session.execute(
                select(IngestionJob)
                .where(IngestionJob.kb_id == kb_id)
                .order_by(IngestionJob.created_at.desc())
                .limit(1)
            )
            job = result.scalars().first()
            if not job:
                return None
            return self._job_to_state(job)

    def update_job_status(self, job_id: str, status: str) -> None:
        """Update job status and timestamp."""
        # Map domain status to DB enum
        status_map = {
                JobStatus.NOT_STARTED.value: DBJobStatus.PENDING.value,
                JobStatus.PENDING.value: DBJobStatus.PENDING.value,
                JobStatus.RUNNING.value: DBJobStatus.RUNNING.value,
                JobStatus.COMPLETED.value: DBJobStatus.COMPLETED.value,
                JobStatus.FAILED.value: DBJobStatus.FAILED.value,
        }
        db_status = status_map.get(status, DBJobStatus.PENDING.value)
        
        with get_session() as session:
            session.execute(
                update(IngestionJob)
                .where(IngestionJob.id == job_id)
                .values(status=db_status, updated_at=datetime.utcnow())
            )
    
    def update_phase_progress(self, job_id: str, current_phase: str, phase_progress: Dict[str, Any]) -> None:
        """Update phase progress for a job."""
        with get_session() as session:
            session.execute(
                update(IngestionJob)
                .where(IngestionJob.id == job_id)
                .values(
                    current_phase=current_phase,
                    phase_progress=phase_progress,
                    updated_at=datetime.utcnow()
                )
            )
    
    def get_phase_progress(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get phase progress for a job."""
        with get_session() as session:
            result = session.execute(
                select(IngestionJob.phase_progress)
                .where(IngestionJob.id == job_id)
            )
            row = result.first()
            return row[0] if row else None

    def enqueue_chunks(self, job_id: str, chunks: List[Dict[str, Any]]) -> int:
        """Enqueue chunks for processing; return count inserted."""
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
                    # Duplicate doc_hash for this job; skip silently or raise
                    continue
            # Update job totals
            session.execute(
                update(IngestionJob)
                .where(IngestionJob.id == job_id)
                .values(total_items=IngestionJob.total_items + inserted, updated_at=now)
            )
        return inserted

    def dequeue_batch(self, job_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Dequeue and lock a batch of chunks for processing."""
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
            result = []
            for it in items:
                it.mark_processing()
                result.append({
                    'id': it.id,
                    'content': it.content,
                    'item_metadata': it.item_metadata,
                    'doc_hash': it.doc_hash,
                })
            session.flush()
            return result

    def commit_batch_success(self, job_id: str, item_ids: List[int]) -> None:
        """Mark batch as successfully processed."""
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

    def commit_batch_error(self, item_id: int, error_message: str) -> None:
        """Mark single item as failed with error message."""
        with get_session() as session:
            session.execute(
                update(IngestionQueueItem)
                .where(IngestionQueueItem.id == item_id)
                .values(
                    status=QueueStatus.ERROR.value,
                    error_log=error_message,
                    attempts=IngestionQueueItem.attempts + 1,
                    updated_at=datetime.utcnow(),
                )
            )

    def get_queue_stats(self, job_id: str) -> Dict[str, int]:
        """Get queue statistics (pending, processing, done, error counts)."""
        with get_session() as session:
            results = session.execute(
                select(IngestionQueueItem.status, func.count(IngestionQueueItem.id))
                .where(IngestionQueueItem.job_id == job_id)
                .group_by(IngestionQueueItem.status)
            ).all()
            stats = {status: count for status, count in results}
            return {
                'pending': stats.get(QueueStatus.PENDING.value, 0),
                'processing': stats.get(QueueStatus.PROCESSING.value, 0),
                'done': stats.get(QueueStatus.DONE.value, 0),
                'error': stats.get(QueueStatus.ERROR.value, 0),
            }

    def recover_inflight_jobs(self) -> None:
        """Reset processing items and mark running jobs as paused on startup."""
        now = datetime.utcnow()
        with get_session() as session:
            session.execute(
                update(IngestionQueueItem)
                .where(IngestionQueueItem.status == QueueStatus.PROCESSING.value)
                .values(status=QueueStatus.PENDING.value, updated_at=now)
            )
            session.execute(
                update(IngestionJob)
                .where(IngestionJob.status == DBJobStatus.RUNNING.value)
                .values(status=DBJobStatus.PAUSED.value, updated_at=now)
            )

    def _job_to_state(self, job: IngestionJob) -> IngestionState:
        """Convert persisted job record to domain state."""
        status_map = {
            DBJobStatus.PENDING.value: JobStatus.PENDING.value,
            DBJobStatus.RUNNING.value: JobStatus.RUNNING.value,
            DBJobStatus.PAUSED.value: JobStatus.PAUSED.value,
            DBJobStatus.COMPLETED.value: JobStatus.COMPLETED.value,
            DBJobStatus.FAILED.value: JobStatus.FAILED.value,
              DBJobStatus.CANCELLED.value: JobStatus.CANCELLED.value,
        }
        status = status_map.get(job.status, JobStatus.PENDING.value)
        completed_at = (
            job.updated_at
            if job.status in {
                DBJobStatus.COMPLETED.value,
                DBJobStatus.FAILED.value,
                DBJobStatus.CANCELLED.value,
            }
            else None
        )
        return IngestionState(
            kb_id=job.kb_id,
            job_id=job.id,
            status=status,
            phase=job.current_phase or "crawling",
            progress=0,
            metrics={},
            message="Recovered job",
            error=None,
            paused=job.status == DBJobStatus.PAUSED.value,
            cancel_requested=job.status == DBJobStatus.CANCELLED.value,
            created_at=job.created_at,
            started_at=job.updated_at,
            completed_at=completed_at,
            phase_status=job.phase_progress if job.phase_progress else None,
        )


# Factory function for dependency injection
def create_database_repository() -> DatabaseRepository:
    """Factory to create database repository instance."""
    return DatabaseRepository()
