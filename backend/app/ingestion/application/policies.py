"""
Policy utilities for the ingestion orchestrator.
"""

from enum import Enum
from typing import List, Optional


class StepName(str, Enum):
    """Pipeline step identifiers."""

    LOAD = "load"
    CHUNK = "chunk"
    EMBED = "embed"
    INDEX = "index"


class WorkflowDefinition:
    """Defines pipeline step order and transitions."""

    ORDER: List[StepName] = [StepName.LOAD, StepName.CHUNK, StepName.EMBED, StepName.INDEX]

    @classmethod
    def get_first_step(cls) -> StepName:
        return cls.ORDER[0]

    @classmethod
    def get_next_step(cls, current: StepName) -> Optional[StepName]:
        try:
            idx = cls.ORDER.index(current)
            return cls.ORDER[idx + 1] if idx + 1 < len(cls.ORDER) else None
        except ValueError:
            return None


class RetryPolicy:
    """Configurable retry policy with exponential backoff."""

    def __init__(self, max_attempts: int = 3, backoff_multiplier: float = 2.0):
        self.max_attempts = max_attempts
        self.backoff_multiplier = backoff_multiplier

    def should_retry(self, attempt: int, error: Exception) -> bool:
        return attempt < self.max_attempts

    def get_backoff_delay(self, attempt: int) -> float:
        return min(2 ** attempt * self.backoff_multiplier, 60.0)
