"""Worker protocols for producer and consumer threads."""

from __future__ import annotations

from typing import Protocol

from app.ingestion.domain.models import JobRuntime


class ProducerWorkerProtocol(Protocol):
    """Interface for producer worker thread execution."""

    @staticmethod
    def run(_runtime: JobRuntime) -> None:
        """Execute producer pipeline (crawl, chunk, enqueue)."""
        ...


class ConsumerWorkerProtocol(Protocol):
    """Interface for consumer worker thread execution."""

    @staticmethod
    def run(_runtime: JobRuntime) -> None:
        """Execute consumer pipeline (dequeue, embed, index)."""
        ...
