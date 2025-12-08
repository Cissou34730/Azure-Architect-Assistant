"""Database repository implementation for ingestion jobs and queue."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update, func

from app.ingestion.ingestion_database import get_session
from app.ingestion.models import (
    IngestionJob,
    IngestionQueueItem,
    IngestionPhaseStatus,
    JobStatus as DBJobStatus,
    QueueStatus,
    PhaseStatusDB,
)
from app.ingestion.domain.models import IngestionState, PhaseState
from app.ingestion.domain.enums import JobPhase, PhaseStatus
from app.ingestion.domain.errors import DuplicateChunkError, JobNotFoundError


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
                current_phase="loading",
                phase_progress={},
            )
            session.add(job)
            session.flush()
            job_id = job.id
        
        # Initialize phase status records
        self.initialize_phase_statuses(job_id)
        
        return job_id

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

    def get_latest_job_record(self, kb_id: str) -> Optional[IngestionJob]:
        """Return the latest ORM job record for a KB (raw DB model)."""
        with get_session() as session:
            result = session.execute(
                select(IngestionJob)
                .where(IngestionJob.kb_id == kb_id)
                .order_by(IngestionJob.created_at.desc())
                .limit(1)
            )
            return result.scalars().first()

    def get_latest_job_id(self, kb_id: str) -> Optional[str]:
        """Return the latest job_id (UUID) for a KB."""
        with get_session() as session:
            result = session.execute(
                select(IngestionJob.id)
                .where(IngestionJob.kb_id == kb_id)
                .order_by(IngestionJob.created_at.desc())
                .limit(1)
            )
            row = result.first()
            return row[0] if row else None

    def update_job_status(self, job_id: str, status: str) -> None:
        """Update job status and timestamp."""
        # TODO: Rebuild status mapping logic after PhaseStatus aggregation is implemented
        # For now, use direct string values
        status_map = {
            "pending": DBJobStatus.PENDING.value,
            "running": DBJobStatus.RUNNING.value,
            "completed": DBJobStatus.COMPLETED.value,
            "failed": DBJobStatus.FAILED.value,
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

    def initialize_phase_statuses(self, job_id: str) -> None:
        """Initialize phase status records for all phases (idempotent)."""
        with get_session() as session:
            existing = session.execute(
                select(IngestionPhaseStatus.phase_name)
                .where(IngestionPhaseStatus.job_id == job_id)
            ).scalars().all()
            existing_set = set(existing)
            for phase in JobPhase:
                if phase.value in existing_set:
                    continue
                phase_status = IngestionPhaseStatus(
                    job_id=job_id,
                    phase_name=phase.value,
                    status=PhaseStatusDB.NOT_STARTED.value,
                )
                session.add(phase_status)
            # After initialization, persist job.status to PENDING (not started)
            session.execute(
                update(IngestionJob)
                .where(IngestionJob.id == job_id)
                .values(status=DBJobStatus.PENDING.value, updated_at=datetime.utcnow())
            )

    def get_phase_status(self, job_id: str, phase_name: str) -> Optional[PhaseState]:
        """Get status for a specific phase."""
        with get_session() as session:
            result = session.execute(
                select(IngestionPhaseStatus)
                .where(
                    IngestionPhaseStatus.job_id == job_id,
                    IngestionPhaseStatus.phase_name == phase_name,
                )
            )
            db_phase = result.scalars().first()
            if not db_phase:
                return None
            return self._db_phase_to_domain(db_phase)

    def get_all_phase_statuses(self, job_id: str) -> Dict[str, PhaseState]:
        """Get all phase statuses for a job."""
        with get_session() as session:
            result = session.execute(
                select(IngestionPhaseStatus)
                .where(IngestionPhaseStatus.job_id == job_id)
                .order_by(IngestionPhaseStatus.phase_name)
            )
            db_phases = result.scalars().all()
            return {
                db_phase.phase_name: self._db_phase_to_domain(db_phase)
                for db_phase in db_phases
            }

    def update_phase_status(
        self,
        job_id: str,
        phase_name: str,
        status: str,
        progress_percent: int = None,
        items_processed: int = None,
        items_total: int = None,
        error_message: str = None,
    ) -> None:
        """Update phase status and progress."""
        values = {"status": status, "updated_at": datetime.utcnow()}
        
        if progress_percent is not None:
            values["progress_percent"] = progress_percent
        if items_processed is not None:
            values["items_processed"] = items_processed
        if items_total is not None:
            values["items_total"] = items_total
        if error_message is not None:
            values["error_message"] = error_message
        
        # Set timestamps based on status
        if status == PhaseStatusDB.RUNNING.value:
            # Only set started_at if it's not already set (first time entering RUNNING)
            with get_session() as check_session:
                result = check_session.execute(
                    select(IngestionPhaseStatus.started_at)
                    .where(
                        IngestionPhaseStatus.job_id == job_id,
                        IngestionPhaseStatus.phase_name == phase_name,
                    )
                )
                existing_started_at = result.scalar_one_or_none()
                if existing_started_at is None:
                    values["started_at"] = datetime.utcnow()
        elif status in (PhaseStatusDB.COMPLETED.value, PhaseStatusDB.FAILED.value):
            values["completed_at"] = datetime.utcnow()
        
        with get_session() as session:
            session.execute(
                update(IngestionPhaseStatus)
                .where(
                    IngestionPhaseStatus.job_id == job_id,
                    IngestionPhaseStatus.phase_name == phase_name,
                )
                .values(**values)
            )
            # Recompute and persist job.status based on all phase rows
            self._recompute_and_persist_job_status(session, job_id)

    def save_phase_state(self, job_id: str, phase_name: str, phase_state: PhaseState) -> None:
        """Save a phase state to the database."""
        self.update_phase_status(
            job_id=job_id,
            phase_name=phase_name,
            status=phase_state.status.value,
            progress_percent=phase_state.progress,
            items_processed=phase_state.items_processed,
            items_total=phase_state.items_total,
            error_message=phase_state.error,
        )

    def _db_phase_to_domain(self, db_phase: IngestionPhaseStatus) -> PhaseState:
        """Convert database phase record to domain PhaseState."""
        return PhaseState(
            phase_name=db_phase.phase_name,
            status=PhaseStatus(db_phase.status),
            progress=db_phase.progress_percent,
            items_processed=db_phase.items_processed,
            items_total=db_phase.items_total,
            started_at=db_phase.started_at,
            completed_at=db_phase.completed_at,
            error=db_phase.error_message,
        )

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
        """Reset processing items and mark running jobs as failed on startup."""
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
                .values(status=DBJobStatus.FAILED.value, updated_at=now)
            )

    def _job_to_state(self, job: IngestionJob) -> IngestionState:
        """Convert persisted job record to domain state."""
        status_map = {
            DBJobStatus.PENDING.value: "pending",
            DBJobStatus.RUNNING.value: "running",
            DBJobStatus.COMPLETED.value: "completed",
            DBJobStatus.FAILED.value: "failed",
        }
        status = status_map.get(job.status, "pending")
        completed_at = (
            job.updated_at
            if job.status in {
                DBJobStatus.COMPLETED.value,
                DBJobStatus.FAILED.value,
            }
            else None
        )
        
        # Load phase statuses from database
        phase_states = self.get_all_phase_statuses(job.id)
        
        return IngestionState(
            kb_id=job.kb_id,
            job_id=job.id,
            status=status,
            phase=job.current_phase or "loading",
            progress=0,
            metrics={},
            message="Recovered job",
            error=None,
            created_at=job.created_at,
            started_at=job.updated_at,
            completed_at=completed_at,
            phases=phase_states,  # Add loaded phase states
        )

    # =============================================================================
    # Phase 6: Persistence on Actions
    # =============================================================================
    def pause_current_phase(self, kb_id: str) -> None:
        """Mark current phase as paused for latest job and update timestamps."""
        with get_session() as session:
            job = session.execute(
                select(IngestionJob)
                .where(IngestionJob.kb_id == kb_id)
                .order_by(IngestionJob.created_at.desc())
                .limit(1)
            ).scalars().first()
            if not job:
                return
            current = job.current_phase or "loading"
            session.execute(
                update(IngestionPhaseStatus)
                .where(
                    IngestionPhaseStatus.job_id == job.id,
                    IngestionPhaseStatus.phase_name == current,
                )
                .values(status=PhaseStatusDB.PAUSED.value, updated_at=datetime.utcnow())
            )
            # Also persist job.status = PAUSED at job level
            session.execute(
                update(IngestionJob)
                .where(IngestionJob.id == job.id)
                .values(status=DBJobStatus.PENDING.value, updated_at=datetime.utcnow())
            )

    def resume_current_phase(self, kb_id: str) -> None:
        """Mark current phase as running for latest job; set started_at if missing."""
        with get_session() as session:
            job = session.execute(
                select(IngestionJob)
                .where(IngestionJob.kb_id == kb_id)
                .order_by(IngestionJob.created_at.desc())
                .limit(1)
            ).scalars().first()
            if not job:
                return
            current = job.current_phase or "loading"
            now = datetime.utcnow()
            # Ensure started_at populated
            ps = session.execute(
                select(IngestionPhaseStatus)
                .where(
                    IngestionPhaseStatus.job_id == job.id,
                    IngestionPhaseStatus.phase_name == current,
                )
            ).scalars().first()
            started_at = ps.started_at if ps else None
            session.execute(
                update(IngestionPhaseStatus)
                .where(
                    IngestionPhaseStatus.job_id == job.id,
                    IngestionPhaseStatus.phase_name == current,
                )
                .values(
                    status=PhaseStatusDB.RUNNING.value,
                    started_at=started_at or now,
                    updated_at=now,
                )
            )
            # Also persist job.status = RUNNING at job level
            session.execute(
                update(IngestionJob)
                .where(IngestionJob.id == job.id)
                .values(status=DBJobStatus.RUNNING.value, updated_at=now)
            )

    def cancel_job_and_reset(self, kb_id: str) -> None:
        """Cancel latest job: reset phases to not_started and clear queue items."""
        with get_session() as session:
            job = session.execute(
                select(IngestionJob)
                .where(IngestionJob.kb_id == kb_id)
                .order_by(IngestionJob.created_at.desc())
                .limit(1)
            ).scalars().first()
            if not job:
                return
            now = datetime.utcnow()
            # Reset phases
            session.execute(
                update(IngestionPhaseStatus)
                .where(IngestionPhaseStatus.job_id == job.id)
                .values(
                    status=PhaseStatusDB.NOT_STARTED.value,
                    progress_percent=0,
                    items_processed=0,
                    error_message=None,
                    started_at=None,
                    completed_at=None,
                    updated_at=now,
                )
            )
            # Reset job
            session.execute(
                update(IngestionJob)
                .where(IngestionJob.id == job.id)
                .values(
                    status=DBJobStatus.PENDING.value,
                    current_phase="loading",
                    phase_progress={},
                    updated_at=now,
                )
            )
            # Clear queue items
            session.execute(
                update(IngestionQueueItem)
                .where(IngestionQueueItem.job_id == job.id)
                .values(status=QueueStatus.DONE.value, updated_at=now)
            )
            # Persist job.status after reset
            self._recompute_and_persist_job_status(session, job.id)

    def clear_index_and_reset(self, kb_id: str) -> None:
        """Reset phases and job to not_started; index deletion handled at service layer."""
        # This mirrors cancel but semantically for clear action
        self.cancel_job_and_reset(kb_id)

    # =============================================================================
    # Job status recomputation
    # =============================================================================
    def _recompute_and_persist_job_status(self, session, job_id: str) -> None:
        """Aggregate phase rows and set `ingestion_jobs.status` deterministically.

        Rules:
        - COMPLETED if all phases are completed
        - FAILED if any phase is failed
        - RUNNING if any phase is running
        - PENDING if all phases are not_started
        - Otherwise PENDING (covers paused/mixed states as pending at KB level)
        """
        phases = session.execute(
            select(IngestionPhaseStatus.status)
            .where(IngestionPhaseStatus.job_id == job_id)
        ).scalars().all()
        if not phases:
            new_status = DBJobStatus.PENDING.value
        elif all(s == PhaseStatusDB.COMPLETED.value for s in phases):
            new_status = DBJobStatus.COMPLETED.value
        elif any(s == PhaseStatusDB.FAILED.value for s in phases):
            new_status = DBJobStatus.FAILED.value
        elif any(s == PhaseStatusDB.RUNNING.value for s in phases):
            new_status = DBJobStatus.RUNNING.value
        elif all(s == PhaseStatusDB.NOT_STARTED.value for s in phases):
            new_status = DBJobStatus.PENDING.value
        else:
            # paused or mixed completed/not_started defaults to PENDING
            new_status = DBJobStatus.PENDING.value

        session.execute(
            update(IngestionJob)
            .where(IngestionJob.id == job_id)
            .values(status=new_status, updated_at=datetime.utcnow())
        )


# Factory function for dependency injection
def create_database_repository() -> DatabaseRepository:
    """Factory to create database repository instance."""
    return DatabaseRepository()
