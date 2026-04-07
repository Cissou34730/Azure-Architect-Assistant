"""
Source Handler Factory
Creates appropriate source handler based on type.
Uses lazy imports to avoid loading all handlers at startup.
"""

import logging
from typing import Any, ClassVar

from .handler_base import BaseSourceHandler

logger = logging.getLogger(__name__)


class SourceHandlerFactory:
    """Factory to create appropriate source handler based on type"""

    HANDLERS: ClassVar[dict[str, type[BaseSourceHandler]]] = {}

    @classmethod
    def create_handler(
        cls, source_type: str, kb_id: str, job: Any = None, state: Any = None
    ) -> BaseSourceHandler:
        """
        Create source handler based on type.
        Uses lazy imports to avoid loading all handlers at startup.

        Args:
            source_type: Type of source (website, youtube, pdf, markdown)
            kb_id: Knowledge base ID
            job: Optional ingestion job (for cancellation support)
            state: Optional IngestionState for thread-safe pause/cancel checking

        Returns:
            Appropriate source handler instance

        Raises:
            ValueError: If source_type is unknown
        """
        source_type = source_type.lower()
        handler_class: type[BaseSourceHandler]

        # Check registry first
        if source_type in cls.HANDLERS:
            handler_class = cls.HANDLERS[source_type]
        # Fallback to standard lazy-loaded types
        elif source_type == 'website':
            from .website.handler import WebsiteSourceHandler  # noqa: PLC0415

            handler_class = WebsiteSourceHandler
        elif source_type == 'youtube':
            from .youtube import YouTubeSourceHandler  # noqa: PLC0415

            handler_class = YouTubeSourceHandler
        elif source_type == 'pdf':
            from .pdf import PDFSourceHandler  # noqa: PLC0415

            handler_class = PDFSourceHandler
        elif source_type == 'markdown':
            from .markdown import MarkdownSourceHandler  # noqa: PLC0415

            handler_class = MarkdownSourceHandler
        else:
            raise ValueError(
                f"Unknown source type: '{source_type}'. "
                f'Available types: website, youtube, pdf, markdown'
            )

        logger.info(f'Creating {handler_class.__name__} for KB: {kb_id}')

        # Pass both job and state to all handlers
        return handler_class(kb_id, job=job, state=state)

    @classmethod
    def register_handler(cls, source_type: str, handler_class: type[BaseSourceHandler]) -> None:
        """
        Register custom source handler.

        Args:
            source_type: Type identifier
            handler_class: Handler class (must inherit from BaseSourceHandler)
        """
        if not issubclass(handler_class, BaseSourceHandler):
            raise TypeError(f'{handler_class} must inherit from BaseSourceHandler')

        cls.HANDLERS[source_type.lower()] = handler_class
        logger.info(f'Registered custom handler: {source_type} -> {handler_class.__name__}')

    @classmethod
    def list_handlers(cls) -> list[str]:
        """Get list of available handler types"""
        # Combine registered and standard
        standard = ['website', 'youtube', 'pdf', 'markdown']
        return list(set(standard) | set(cls.HANDLERS.keys()))
