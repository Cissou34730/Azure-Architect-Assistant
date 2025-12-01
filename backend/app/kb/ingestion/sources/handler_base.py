"""
Base Source Handler
Abstract base class for all source handlers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from llama_index.core import Document


class BaseSourceHandler(ABC):
    """Abstract base class for source handlers"""
    
    def __init__(self, kb_id: str, job=None, state=None):
        self.kb_id = kb_id
        self.job = job  # Optional job reference for cancellation checks
        self.state = state  # Optional IngestionState for cooperative pause/cancel
    
    @abstractmethod
    def ingest(self, config: Dict[str, Any]) -> List[Document]:
        """
        Ingest documents from source.
        
        Args:
            config: Source-specific configuration
            
        Returns:
            List of LlamaIndex Documents
        """
        pass