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


class PipelineStage(ABC):
    """Base class for pipeline stages."""

    @abstractmethod
    async def execute(self, context: PipelineContext) -> None:
        """Execute this stage of the pipeline."""

    @abstractmethod
    def get_stage_name(self) -> str:
        """Return human-readable stage name."""
