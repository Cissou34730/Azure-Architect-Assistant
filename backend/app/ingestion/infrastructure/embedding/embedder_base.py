"""
Base Embedder
Abstract base class for embedding strategies.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
from app.core.config import get_openai_settings

logger = logging.getLogger(__name__)


class BaseEmbedder(ABC):
    """Abstract base class for document embedders"""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize embedder.
        
        Args:
            model_name: Name of the embedding model (defaults to config setting)
        """
        if model_name is None:
            model_name = get_openai_settings().embedding_model
        self.model_name = model_name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def embed_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for documents.
        
        Args:
            documents: List of documents with 'content' and 'metadata' keys
            
        Returns:
            List of documents with 'embedding' field added to each
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
            if 'content' not in doc:
                self.logger.error(f"Document {i} missing 'content' field")
                return False
            
            if not doc['content']:
                self.logger.warning(f"Document {i} has empty content")
        
        return True
