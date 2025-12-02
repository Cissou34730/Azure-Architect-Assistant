"""Lifecycle manager protocol for thread management."""

from __future__ import annotations

from typing import Any, Callable, Protocol, Tuple

from app.ingestion.domain.models import JobRuntime


class LifecycleManagerProtocol(Protocol):
    """Interface for managing thread lifecycle and coordination."""

    def create_runtime(
        self,
        job_id: str,
        kb_id: str,
        state: Any,
        producer_target: Callable[..., Any],
        producer_args: Tuple[Any, ...],
        producer_kwargs: dict,
    ) -> JobRuntime:
        """Create a new job runtime with threads."""
        ...

    def start_threads(self, runtime: JobRuntime) -> None:
        """Start producer and consumer threads."""
        ...

    def stop_threads(self, runtime: JobRuntime, timeout: float = 5.0) -> None:
        """Gracefully stop threads and wait for exit."""
        ...

    def is_running(self, runtime: JobRuntime) -> bool:
        """Check if producer thread is alive."""
        ...

    def check_queue_drained(self, runtime: JobRuntime) -> bool:
        """Check if work queue is empty for cooperative shutdown."""
        ...
