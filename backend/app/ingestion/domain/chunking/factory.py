"""
Chunker Factory
Creates appropriate chunker based on strategy.
"""

import logging
from typing import Any, ClassVar

from .chunker_base import BaseChunker
from .semantic import SemanticChunker

logger = logging.getLogger(__name__)


class ChunkerFactory:
    """Factory to create appropriate chunker based on strategy"""

    # Chunker registry
    CHUNKERS: ClassVar[dict[str, type[BaseChunker]]] = {
        'semantic': SemanticChunker,
        'sentence': SemanticChunker,  # Alias
        'default': SemanticChunker,
    }

    @classmethod
    def create_chunker(
        cls,
        strategy: str = 'semantic',
        chunk_size: int = 1024,
        chunk_overlap: int = 200,
        **kwargs: Any,
    ) -> BaseChunker:
        """
        Create chunker based on strategy.

        Args:
            strategy: Chunking strategy (semantic, fixed, recursive, etc.)
            chunk_size: Target chunk size
            chunk_overlap: Overlap between chunks
            **kwargs: Additional strategy-specific parameters

        Returns:
            Appropriate chunker instance

        Raises:
            ValueError: If strategy is unknown
        """
        chunker_class = cls.CHUNKERS.get(strategy.lower())

        if not chunker_class:
            available = ', '.join(cls.CHUNKERS.keys())
            raise ValueError(
                f"Unknown chunking strategy: '{strategy}'. Available strategies: {available}"
            )

        logger.info(
            f'Creating {chunker_class.__name__}: size={chunk_size}, overlap={chunk_overlap}'
        )
        return chunker_class(chunk_size=chunk_size, chunk_overlap=chunk_overlap, **kwargs)

    @classmethod
    def register_chunker(cls, strategy: str, chunker_class: type[BaseChunker]) -> None:
        """
        Register custom chunker.

        Args:
            strategy: Strategy identifier
            chunker_class: Chunker class (must inherit from BaseChunker)
        """
        if not issubclass(chunker_class, BaseChunker):
            raise TypeError(f'{chunker_class} must inherit from BaseChunker')

        cls.CHUNKERS[strategy.lower()] = chunker_class
        logger.info(f'Registered custom chunker: {strategy} -> {chunker_class.__name__}')

    @classmethod
    def list_strategies(cls) -> list[str]:
        """Get list of available chunking strategies"""
        return list(cls.CHUNKERS.keys())
