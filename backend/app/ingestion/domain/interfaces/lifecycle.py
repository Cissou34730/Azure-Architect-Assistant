"""Lifecycle manager protocol for thread management."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from app.ingestion.domain.models import JobRuntime


@dataclass
class ProducerConfig:
    """Configuration for producer thread."""

    target: Callable[..., Any]
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] | None = None


class LifecycleManagerProtocol(Protocol):
    """Interface for managing thread lifecycle and coordination."""

    def create_runtime(
        self,
        job_id: str,
        kb_id: str,
        state: Any,
        producer_config: ProducerConfig,
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
