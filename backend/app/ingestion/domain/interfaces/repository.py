"""Repository protocol for job and queue persistence."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from app.ingestion.domain.models import IngestionState


class RepositoryProtocol(Protocol):
    """Interface for ingestion job and queue persistence operations."""

    def create_job(
        self,
        kb_id: str,
        source_type: str,
        source_config: Dict[str, Any],
        priority: int = 0,
    ) -> str:
        """Create a new ingestion job and return its ID."""
        ...

    def get_latest_job(self, kb_id: str) -> Optional[IngestionState]:
        """Get the most recent job for a knowledge base."""
        ...

    def update_job_status(self, job_id: str, status: str) -> None:
        """Update job status and timestamp."""
        ...

    def enqueue_chunks(self, job_id: str, chunks: List[Dict[str, Any]]) -> int:
        """Enqueue chunks for processing; return count inserted."""
        ...

    def dequeue_batch(self, job_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Dequeue and lock a batch of chunks for processing."""
        ...

    def commit_batch_success(self, job_id: str, item_ids: List[int]) -> None:
        """Mark batch as successfully processed."""
        ...

    def commit_batch_error(self, item_id: int, error_message: str) -> None:
        """Mark single item as failed with error message."""
        ...

    def get_queue_stats(self, job_id: str) -> Dict[str, int]:
        """Get queue statistics (pending, processing, done, error counts)."""
        ...

    def recover_inflight_jobs(self) -> None:
        """Reset processing items and mark running jobs as paused on startup."""
        ...
