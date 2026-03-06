from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineContext:
    """Shared context across pipeline stages."""

    kb_id: str
    job_id: str
    config: dict[str, Any]
    checkpoint: dict[str, Any]
    counters: dict[str, int]
    results: dict[str, Any] = field(default_factory=dict)

    def set_batch_state(
        self,
        *,
        batch: list[Any],
        batch_id: int,
        resume_active_batch: bool,
        resume_chunk_index: int,
    ) -> None:
        self.results['batch'] = batch
        self.results['batch_id'] = batch_id
        self.results['resume_active_batch'] = resume_active_batch
        self.results['resume_chunk_index'] = resume_chunk_index

    def require_batch(self) -> list[Any]:
        batch = self.results.get('batch')
        if not isinstance(batch, list):
            raise TypeError('PipelineContext requires a list batch in results["batch"]')
        return batch

    def set_chunks(self, chunks: list[Any]) -> None:
        self.results['chunks'] = chunks

    def require_chunks(self) -> list[Any]:
        chunks = self.results.get('chunks')
        if not isinstance(chunks, list):
            raise TypeError('PipelineContext requires a list of chunks in results["chunks"]')
        return chunks

    def get_batch_id(self) -> int:
        batch_id = self.results.get('batch_id', 0)
        return int(batch_id if batch_id is not None else 0)

    def is_resuming_batch(self) -> bool:
        return bool(self.results.get('resume_active_batch'))

    def get_resume_chunk_index(self) -> int:
        chunk_index = self.results.get('resume_chunk_index', -1)
        return int(chunk_index if chunk_index is not None else -1)

    def phases_started(self) -> dict[str, bool]:
        phases_started = self.results.get('phases_started')
        if not isinstance(phases_started, dict):
            phases_started = {'chunking': False, 'embedding': False, 'indexing': False}
            self.results['phases_started'] = phases_started
        return phases_started

    def mark_should_continue(self, should_continue: bool) -> None:
        self.results['continue'] = should_continue

    def should_continue(self) -> bool:
        return self.results.get('continue') is not False


class PipelineStage(ABC):
    """Base class for pipeline stages."""

    @abstractmethod
    async def execute(self, context: PipelineContext) -> None:
        """Execute this stage of the pipeline."""

    @abstractmethod
    def get_stage_name(self) -> str:
        """Return human-readable stage name."""
