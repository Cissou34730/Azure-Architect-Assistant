"""
Base Index Builder
Abstract base class for index building strategies.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from app.core.config import get_openai_settings

logger = logging.getLogger(__name__)


class BaseIndexBuilder(ABC):
    """Abstract base class for index builders"""

    def __init__(
        self,
        kb_id: str,
        storage_dir: str,
        embedding_model: Optional[str] = None,
        generation_model: Optional[str] = None,
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
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def build_index(
        self,
        documents: List[Dict[str, Any]],
        progress_callback: Optional[Callable] = None,
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

    def validate_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """
        Validate document structure.

        Args:
            documents: List of documents to validate

        Returns:
            True if valid, False otherwise
        """
        if not documents:
            self.logger.error("No documents provided")
            return False

        for i, doc in enumerate(documents):
            if "content" not in doc:
                self.logger.error(f"Document {i} missing 'content' field")
                return False

            if not doc["content"]:
                self.logger.warning(f"Document {i} has empty content")

        return True
