"""
Base Source Handler
Abstract base class for all source handlers.
"""

from abc import ABC, abstractmethod
from collections.abc import Generator
from typing import Any

from llama_index.core import Document


class BaseSourceHandler(ABC):
    """Abstract base class for source handlers"""

    def __init__(self, kb_id: str, job: Any | None = None, state: Any | None = None) -> None:
        self.kb_id = kb_id
        self.job = job  # Optional job reference for cancellation checks
        self.state = state  # Optional IngestionState for cooperative pause/cancel

    @abstractmethod
    def ingest(self, config: dict[str, Any]) -> list[Document] | Generator[list[Document], None, None]:
        """
        Ingest documents from source.

        Args:
            config: Source-specific configuration

        Returns:
            List of LlamaIndex Documents
        """
        pass
