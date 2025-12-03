"""
Embedder Factory
Creates appropriate embedder based on type.
"""

import logging
from typing import Dict, Any

from .embedder_base import BaseEmbedder
from .openai_embedder import OpenAIEmbedder

logger = logging.getLogger(__name__)


class EmbedderFactory:
    """Factory to create appropriate embedder based on type"""
    
    # Embedder registry
    EMBEDDERS = {
        'openai': OpenAIEmbedder,
        'default': OpenAIEmbedder
    }
    
    @classmethod
    def create_embedder(
        cls,
        embedder_type: str = 'openai',
        model_name: str = "text-embedding-3-small",
        **kwargs
    ) -> BaseEmbedder:
        """
        Create embedder based on type.
        
        Args:
            embedder_type: Type of embedder (openai, azure, local, etc.)
            model_name: Embedding model name
            **kwargs: Additional embedder-specific parameters
            
        Returns:
            Appropriate embedder instance
            
        Raises:
            ValueError: If embedder_type is unknown
        """
        embedder_class = cls.EMBEDDERS.get(embedder_type.lower())
        
        if not embedder_class:
            available = ', '.join(cls.EMBEDDERS.keys())
            raise ValueError(
                f"Unknown embedder type: '{embedder_type}'. "
                f"Available types: {available}"
            )
        
        logger.info(f"Creating {embedder_class.__name__} with model: {model_name}")
        return embedder_class(model_name=model_name, **kwargs)
    
    @classmethod
    def register_embedder(cls, embedder_type: str, embedder_class: type):
        """
        Register custom embedder.
        
        Args:
            embedder_type: Type identifier
            embedder_class: Embedder class (must inherit from BaseEmbedder)
        """
        if not issubclass(embedder_class, BaseEmbedder):
            raise TypeError(f"{embedder_class} must inherit from BaseEmbedder")
        
        cls.EMBEDDERS[embedder_type.lower()] = embedder_class
        logger.info(f"Registered custom embedder: {embedder_type} -> {embedder_class.__name__}")
    
    @classmethod
    def list_types(cls) -> list:
        """Get list of available embedder types"""
        return list(cls.EMBEDDERS.keys())
