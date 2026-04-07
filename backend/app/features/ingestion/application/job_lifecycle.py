from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.features.ingestion.domain.indexing import Indexer
from app.features.ingestion.infrastructure.job_repository import JobRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatchProgress:
    batch_id: int
    document_count: int
    chunk_count: int


class JobLifecycleManager:
    """Centralizes ingestion job state transitions and checkpoint persistence."""

    ACTIVE_BATCH_ID = 'active_batch_id'
    ACTIVE_BATCH_DOCS = 'active_batch_docs'
    ACTIVE_BATCH_CHUNKS = 'active_batch_chunks'
    RESUME_CHUNK_INDEX = 'resume_chunk_index'

    def __init__(self, repo: JobRepository) -> None:
        self._repo = repo

    def is_resuming_batch(self, checkpoint: dict[str, Any], batch_id: int) -> bool:
        active_batch_id = checkpoint.get(self.ACTIVE_BATCH_ID, -1)
        return int(active_batch_id if active_batch_id is not None else -1) == batch_id

    def get_resume_chunk_index(self, checkpoint: dict[str, Any], batch_id: int) -> int:
        if not self.is_resuming_batch(checkpoint, batch_id):
            return -1
        chunk_index = checkpoint.get(self.RESUME_CHUNK_INDEX, -1)
        return int(chunk_index if chunk_index is not None else -1)

    def mark_running(self, job_id: str) -> None:
        self._repo.set_job_status(job_id, status='running')

    def mark_failed(self, job_id: str, error_message: str) -> None:
        self._repo.set_job_status(
            job_id,
            status='failed',
            finished_at=datetime.now(timezone.utc),
            last_error=error_message,
        )

    def mark_completed(self, job_id: str) -> None:
        self._repo.set_job_status(
            job_id,
            status='completed',
            finished_at=datetime.now(timezone.utc),
            last_error=None,
        )

    def request_cancel(self, job_id: str) -> None:
        self._repo.set_job_status(job_id, status='canceled')

    def persist_progress(
        self,
        job_id: str,
        checkpoint: dict[str, Any] | None,
        counters: dict[str, Any] | None,
        *,
        heartbeat: bool = False,
    ) -> None:
        if checkpoint is not None or counters is not None:
            self._repo.update_job(job_id, checkpoint=checkpoint, counters=counters)
        if heartbeat:
            self._repo.update_heartbeat(job_id)

    def pause(
        self,
        job_id: str,
        checkpoint: dict[str, Any] | None = None,
        counters: dict[str, Any] | None = None,
    ) -> None:
        self.persist_progress(job_id, checkpoint, counters)
        self._repo.set_job_status(job_id, status='paused')

    def mark_batch_started(
        self,
        job_id: str,
        checkpoint: dict[str, Any],
        counters: dict[str, Any],
        *,
        batch: BatchProgress,
    ) -> None:
        checkpoint[self.ACTIVE_BATCH_ID] = batch.batch_id
        checkpoint[self.ACTIVE_BATCH_DOCS] = batch.document_count
        checkpoint[self.ACTIVE_BATCH_CHUNKS] = batch.chunk_count
        checkpoint[self.RESUME_CHUNK_INDEX] = -1
        self.persist_progress(job_id, checkpoint, counters)

    def record_chunk_progress(
        self,
        job_id: str,
        checkpoint: dict[str, Any],
        counters: dict[str, Any],
        *,
        batch_id: int,
        chunk_index: int,
    ) -> None:
        checkpoint[self.ACTIVE_BATCH_ID] = batch_id
        checkpoint[self.RESUME_CHUNK_INDEX] = chunk_index
        self.persist_progress(job_id, checkpoint, counters)

    def mark_batch_completed(
        self,
        job_id: str,
        checkpoint: dict[str, Any],
        counters: dict[str, Any],
        *,
        batch_id: int,
        heartbeat: bool = True,
    ) -> None:
        checkpoint['last_batch_id'] = batch_id
        checkpoint.pop(self.ACTIVE_BATCH_ID, None)
        checkpoint.pop(self.ACTIVE_BATCH_DOCS, None)
        checkpoint.pop(self.ACTIVE_BATCH_CHUNKS, None)
        checkpoint.pop(self.RESUME_CHUNK_INDEX, None)
        self.persist_progress(job_id, checkpoint, counters, heartbeat=heartbeat)

    def cleanup_canceled_job(
        self,
        job_id: str,
        kb_id: str,
        indexer: Indexer,
        *,
        reason: str = 'Canceled by user',
    ) -> None:
        indexer.delete_by_job(job_id, kb_id)
        logger.info('Deleted indexed data for canceled job', extra={'job_id': job_id})
        self._repo.set_job_status(
            job_id,
            status='not_started',
            finished_at=datetime.now(timezone.utc),
            last_error=reason,
        )
        self._repo.update_job(job_id, checkpoint=None, counters=None)

