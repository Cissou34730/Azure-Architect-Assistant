"""
Source Handler Factory
Creates appropriate source handler based on type.
"""

import logging
from typing import Union

from .base import BaseSourceHandler
from .website import WebsiteSourceHandler
from .youtube import YouTubeSourceHandler
from .pdf import PDFSourceHandler
from .markdown import MarkdownSourceHandler

logger = logging.getLogger(__name__)


class SourceHandlerFactory:
    """Factory to create appropriate source handler based on type"""
    
    # Handler registry
    HANDLERS = {
        'website': WebsiteSourceHandler,
        'youtube': YouTubeSourceHandler,
        'pdf': PDFSourceHandler,
        'markdown': MarkdownSourceHandler
    }
    
    @classmethod
    def create_handler(cls, source_type: str, kb_id: str) -> BaseSourceHandler:
        """
        Create source handler based on type.
        
        Args:
            source_type: Type of source (website, youtube, pdf, markdown)
            kb_id: Knowledge base ID
            
        Returns:
            Appropriate source handler instance
            
        Raises:
            ValueError: If source_type is unknown
        """
        handler_class = cls.HANDLERS.get(source_type.lower())
        
        if not handler_class:
            available = ', '.join(cls.HANDLERS.keys())
            raise ValueError(
                f"Unknown source type: '{source_type}'. "
                f"Available types: {available}"
            )
        
        logger.info(f"Creating {handler_class.__name__} for KB: {kb_id}")
        return handler_class(kb_id)
    
    @classmethod
    def register_handler(cls, source_type: str, handler_class: type):
        """
        Register custom source handler.
        
        Args:
            source_type: Type identifier
            handler_class: Handler class (must inherit from BaseSourceHandler)
        """
        if not issubclass(handler_class, BaseSourceHandler):
            raise TypeError(f"{handler_class} must inherit from BaseSourceHandler")
        
        cls.HANDLERS[source_type.lower()] = handler_class
        logger.info(f"Registered custom handler: {source_type} -> {handler_class.__name__}")
    
    @classmethod
    def list_handlers(cls) -> list:
        """Get list of available handler types"""
        return list(cls.HANDLERS.keys())
