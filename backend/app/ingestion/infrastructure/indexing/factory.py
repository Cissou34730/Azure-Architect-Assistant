"""
Index Builder Factory
Creates appropriate index builder based on type.
"""

import logging
from typing import Any, ClassVar

from .builder_base import BaseIndexBuilder
from .vector import VectorIndexBuilder

logger = logging.getLogger(__name__)


class IndexBuilderFactory:
    """Factory to create appropriate index builder based on type"""

    # Builder registry
    BUILDERS: ClassVar[dict[str, type[BaseIndexBuilder]]] = {
        'vector': VectorIndexBuilder,
        'default': VectorIndexBuilder,
    }

    @classmethod
    def create_builder(
        cls,
        index_type: str = 'vector',
        kb_id: str | None = None,
        storage_dir: str | None = None,
        embedding_model: str | None = None,
        generation_model: str | None = None,
        **kwargs: Any,
    ) -> BaseIndexBuilder:
        """
        Create index builder based on type.

        Args:
            index_type: Type of index (vector, graph, hybrid, etc.)
            kb_id: Knowledge base identifier
            storage_dir: Directory for index storage
            embedding_model: Model for embeddings (defaults to config setting)
            generation_model: Model for generation (defaults to config setting)
            **kwargs: Additional type-specific parameters

        Returns:
            Appropriate index builder instance

        Raises:
            ValueError: If index_type is unknown or required params missing
        """
        if not kb_id or not storage_dir:
            raise ValueError('kb_id and storage_dir are required')

        builder_class = cls.BUILDERS.get(index_type.lower())

        if not builder_class:
            available = ', '.join(cls.BUILDERS.keys())
            raise ValueError(f"Unknown index type: '{index_type}'. Available types: {available}")

        logger.info(f'Creating {builder_class.__name__} for KB: {kb_id}')
        return builder_class(
            kb_id=kb_id,
            storage_dir=storage_dir,
            embedding_model=embedding_model,
            generation_model=generation_model,
            **kwargs,
        )

    @classmethod
    def register_builder(cls, index_type: str, builder_class: type[BaseIndexBuilder]) -> None:
        """
        Register custom index builder.

        Args:
            index_type: Type identifier
            builder_class: Builder class (must inherit from BaseIndexBuilder)
        """
        if not issubclass(builder_class, BaseIndexBuilder):
            raise TypeError(f'{builder_class} must inherit from BaseIndexBuilder')

        cls.BUILDERS[index_type.lower()] = builder_class
        logger.info(f'Registered custom builder: {index_type} -> {builder_class.__name__}')

    @classmethod
    def list_types(cls) -> list[str]:
        """Get list of available index types"""
        return list(cls.BUILDERS.keys())
