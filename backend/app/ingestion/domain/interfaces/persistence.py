"""Persistence store protocol for state checkpoint management."""

from __future__ import annotations

from typing import Dict, Protocol

from app.ingestion.domain.models import IngestionState


class PersistenceStoreProtocol(Protocol):
    """Interface for ingestion state persistence (disk, blob, etc.)."""

    def save_state(self, state: IngestionState) -> None:
        """Persist ingestion state to storage."""
        ...

    def load_state(self, kb_id: str) -> IngestionState | None:
        """Load state for a specific knowledge base."""
        ...

    def load_all_states(self) -> Dict[str, IngestionState]:
        """Load all persisted states from storage."""
        ...

    def delete_state(self, kb_id: str) -> None:
        """Remove persisted state for a knowledge base."""
        ...
