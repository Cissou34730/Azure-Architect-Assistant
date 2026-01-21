"""
Base Index Builder
Abstract base class for index building strategies.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, cast

from app.core.app_settings import get_openai_settings

logger = logging.getLogger(__name__)


class BaseIndexBuilder(ABC):
    """Abstract base class for index builders"""

    def __init__(
        self,
        kb_id: str,
        storage_dir: str,
        embedding_model: str | None = None,
        generation_model: str | None = None,
    ):
        """
        Initialize index builder.

        Args:
            kb_id: Knowledge base identifier
            storage_dir: Directory for index storage
            embedding_model: Model for embeddings (defaults to config setting)
            generation_model: Model for generation/LLM tasks (defaults to config setting)
        """
        openai_settings = get_openai_settings()

        self.kb_id = kb_id
        self.storage_dir = storage_dir
        self.embedding_model = embedding_model or openai_settings.embedding_model
        self.generation_model = generation_model or openai_settings.model
        self.logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')

    @abstractmethod
    def build_index(
        self,
        documents: Any,
        progress_callback: Callable[..., Any] | None = None,
    ) -> str:
        """
        Build index from documents.

        Args:
            documents: List of documents with 'content' and 'metadata' keys
            progress_callback: Optional callback(phase, progress, message, metrics)

        Returns:
            Path to the created index
        """
        pass

    def validate_documents(self, documents: list[dict[str, Any]]) -> bool:
        """
        Validate document structure.

        Args:
            documents: List of documents to validate

        Returns:
            True if valid, False otherwise
        """
        if not documents:
            self.logger.error('No documents provided')
            return False

        for i, doc in enumerate(documents):
            if 'content' not in doc:
                self.logger.error(f"Document {i} missing 'content' field")
                return False

            if not doc['content']:
                self.logger.warning(f'Document {i} has empty content')

        return True

    def _load_state(self) -> dict[str, Any]:
        """Load processing state from disk."""
        state_file = os.path.join(self.storage_dir, 'state.json')
        if not os.path.exists(state_file):
            return {}

        try:
            with open(state_file, encoding='utf-8') as f:
                state = json.load(f)
                return cast(dict[str, Any], state)
        except (OSError, json.JSONDecodeError) as e:
            self.logger.warning(f'Could not load state file {state_file}: {e}')
            return {}

    def _save_state(self, state: dict[str, Any]) -> None:
        """Save processing state to disk."""
        os.makedirs(self.storage_dir, exist_ok=True)
        state_file = os.path.join(self.storage_dir, 'state.json')

        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except OSError as e:
            self.logger.error(f'Could not save state file {state_file}: {e}')
