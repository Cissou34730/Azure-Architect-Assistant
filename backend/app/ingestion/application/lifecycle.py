"""Lifecycle manager for thread coordination and shutdown."""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Tuple

from app.ingestion.domain.models import JobRuntime, IngestionState
from config import get_settings

logger = logging.getLogger(__name__)


class LifecycleManager:
    """Manages thread lifecycle with cooperative shutdown."""

    def __init__(self):
        self.settings = get_settings()

    def create_runtime(
        self,
        job_id: str,
        kb_id: str,
        state: IngestionState,
        producer_target: Callable[..., Any],
        producer_args: Tuple[Any, ...],
        producer_kwargs: dict,
    ) -> JobRuntime:
        """Create a new job runtime with configuration."""
        runtime = JobRuntime(
            job_id=job_id,
            kb_id=kb_id,
            state=state,
        )
        runtime.producer_target = producer_target
        runtime.producer_args = producer_args
        runtime.producer_kwargs = producer_kwargs
        return runtime

    def start_threads(
        self,
        runtime: JobRuntime,
        producer_worker_fn: Callable[[JobRuntime], None],
        consumer_worker_fn: Callable[[JobRuntime], None],
    ) -> None:
        """Start producer and consumer threads."""
        producer_thread = threading.Thread(
            target=producer_worker_fn,
            args=(runtime,),
            name=f"ingest:{runtime.kb_id}:producer",
            daemon=True,
        )
        consumer_thread = threading.Thread(
            target=consumer_worker_fn,
            args=(runtime,),
            name=f"ingest:{runtime.kb_id}:consumer",
            daemon=True,
        )

        runtime.producer_thread = producer_thread
        runtime.consumer_thread = consumer_thread

        logger.info(f"[LifecycleManager] Starting threads for KB {runtime.kb_id}")
        producer_thread.start()
        consumer_thread.start()

    def stop_threads(self, runtime: JobRuntime, timeout: Optional[float] = None) -> None:
        """Gracefully stop threads and wait for exit."""
        if timeout is None:
            timeout = self.settings.thread_join_timeout

        logger.info(f"[LifecycleManager] Stopping threads for KB {runtime.kb_id}")
        runtime.stop_event.set()

        if runtime.producer_thread and runtime.producer_thread.is_alive():
            runtime.producer_thread.join(timeout=timeout)
            if runtime.producer_thread.is_alive():
                logger.warning(f"Producer thread for KB {runtime.kb_id} did not exit in {timeout}s")

        if runtime.consumer_thread and runtime.consumer_thread.is_alive():
            runtime.consumer_thread.join(timeout=timeout)
            if runtime.consumer_thread.is_alive():
                logger.warning(f"Consumer thread for KB {runtime.kb_id} did not exit in {timeout}s")

    def is_running(self, runtime: JobRuntime) -> bool:
        """Check if producer thread is alive."""
        return runtime.producer_thread is not None and runtime.producer_thread.is_alive()

    def check_queue_drained(self, runtime: JobRuntime, repository) -> bool:
        """Check if work queue is empty for cooperative shutdown."""
        try:
            stats = repository.get_queue_stats(runtime.job_id)
            pending = stats.get('pending', 0)
            processing = stats.get('processing', 0)
            return pending == 0 and processing == 0
        except Exception as exc:
            logger.warning(f"Failed to check queue stats for KB {runtime.kb_id}: {exc}")
            return False


# Factory function
def create_lifecycle_manager() -> LifecycleManager:
    """Factory to create lifecycle manager."""
    return LifecycleManager()
