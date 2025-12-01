"""
Generic Ingestion Base Classes
Provides abstract interfaces for document crawling, cleaning, and indexing.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class IngestionPhase(str, Enum):
    """Phases of the ingestion process."""
    CRAWLING = "crawling"
    CLEANING = "cleaning"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentCrawler(ABC):
    """
    Base class for document crawlers.
    Implementations should crawl documents from various sources (web, files, APIs).
    """
    
    def __init__(self, kb_id: str, config: Dict[str, Any]):
        """
        Initialize crawler.
        
        Args:
            kb_id: Knowledge base identifier
            config: Source-specific configuration (e.g., start_url, max_depth)
        """
        self.kb_id = kb_id
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def crawl(self, progress_callback: Optional[callable] = None) -> List[str]:
        """
        Crawl and return list of document URLs or file paths.
        
        Args:
            progress_callback: Optional callback(current, total, message) for progress updates
            
        Returns:
            List of URLs or file paths to documents
        """
        pass
    
    @abstractmethod
    def fetch_content(self, url: str) -> str:
        """
        Fetch raw content from a URL or file path.
        
        Args:
            url: Document URL or file path
            
        Returns:
            Raw document content (HTML, text, etc.)
        """
        pass
    
    def validate_config(self) -> bool:
        """
        Validate crawler configuration.
        
        Returns:
            True if configuration is valid
        """
        return True


class DocumentCleaner(ABC):
    """
    Base class for document cleaners.
    Implementations should clean and structure raw content into usable documents.
    """
    
    def __init__(self, kb_id: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize cleaner.
        
        Args:
            kb_id: Knowledge base identifier
            config: Cleaner-specific configuration
        """
        self.kb_id = kb_id
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def clean(
        self,
        raw_content: str,
        metadata: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Clean and structure document content.
        
        Args:
            raw_content: Raw document content
            metadata: Document metadata (url, title, etc.)
            progress_callback: Optional callback for progress updates
            
        Returns:
            Structured document with:
                - content: Cleaned text content
                - metadata: Enhanced metadata
                - status: 'success' or 'failed'
                - error: Error message if failed
        """
        pass
    
    def extract_metadata(self, raw_content: str, url: str) -> Dict[str, Any]:
        """
        Extract metadata from raw content.
        
        Args:
            raw_content: Raw document content
            url: Document URL
            
        Returns:
            Metadata dictionary
        """
        return {"url": url}


class IndexBuilder(ABC):
    """
    Base class for index builders.
    Implementations should chunk documents, generate embeddings, and build vector indexes.
    """
    
    def __init__(self, kb_config: Dict[str, Any]):
        """
        Initialize index builder.
        
        Args:
            kb_config: Knowledge base configuration (chunk_size, embedding_model, etc.)
        """
        self.kb_config = kb_config
        self.kb_id = kb_config.get('id')
        self.chunk_size = kb_config.get('chunk_size', 800)
        self.chunk_overlap = kb_config.get('chunk_overlap', 120)
        self.embedding_model = kb_config.get('embedding_model', 'text-embedding-3-small')
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def build_index(
        self,
        documents: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> str:
        """
        Build vector index from documents.
        
        Args:
            documents: List of cleaned documents
            progress_callback: Optional callback(phase, current, total, message)
            
        Returns:
            Path to the created index
        """
        pass
    
    @abstractmethod
    def chunk_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Chunk documents into smaller pieces.
        
        Args:
            documents: List of documents to chunk
            
        Returns:
            List of chunks with metadata
        """
        pass
    
    def validate_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """
        Validate documents before indexing.
        
        Args:
            documents: Documents to validate
            
        Returns:
            True if all documents are valid
        """
        for doc in documents:
            if not doc.get('content'):
                self.logger.warning(f"Document missing content: {doc.get('metadata', {}).get('url', 'unknown')}")
                return False
        return True
