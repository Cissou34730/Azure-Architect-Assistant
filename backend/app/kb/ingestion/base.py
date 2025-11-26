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


class IngestionPipeline:
    """
    Generic ingestion pipeline that orchestrates crawling, cleaning, and indexing.
    """
    
    def __init__(
        self,
        crawler: DocumentCrawler,
        cleaner: DocumentCleaner,
        indexer: IndexBuilder
    ):
        """
        Initialize pipeline.
        
        Args:
            crawler: Document crawler instance
            cleaner: Document cleaner instance
            indexer: Index builder instance
        """
        self.crawler = crawler
        self.cleaner = cleaner
        self.indexer = indexer
        self.logger = logging.getLogger(__name__)
    
    def run(
        self,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Run complete ingestion pipeline.
        
        Args:
            progress_callback: Optional callback(phase, progress, message)
            
        Returns:
            Results dictionary with:
                - success: bool
                - index_path: str (if successful)
                - documents_processed: int
                - chunks_created: int
                - error: str (if failed)
        """
        try:
            # Phase 1: Crawl
            self.logger.info("=" * 80)
            self.logger.info("PHASE 1: CRAWLING")
            self.logger.info("=" * 80)
            if progress_callback:
                progress_callback(IngestionPhase.CRAWLING, 0, "Starting to crawl documents...", {})
            
            urls = self.crawler.crawl(progress_callback)
            self.logger.info(f"✓ Crawling complete: {len(urls)} URLs discovered")
            for i, url in enumerate(urls[:10]):  # Log first 10
                self.logger.info(f"  [{i+1}] {url}")
            if len(urls) > 10:
                self.logger.info(f"  ... and {len(urls) - 10} more")
            
            if not urls:
                raise ValueError("No URLs found during crawl")
            
            # Phase 2: Clean
            self.logger.info("=" * 80)
            self.logger.info("PHASE 2: CLEANING AND EXTRACTING CONTENT")
            self.logger.info("=" * 80)
            if progress_callback:
                progress_callback(IngestionPhase.CLEANING, 0, f"Cleaning {len(urls)} documents...", {})
            
            documents = []
            for i, url in enumerate(urls):
                try:
                    self.logger.info(f"Processing [{i+1}/{len(urls)}]: {url}")
                    raw_content = self.crawler.fetch_content(url)
                    
                    if not raw_content:
                        self.logger.warning(f"  ⚠ No content fetched from {url}")
                        continue
                    
                    self.logger.info(f"  Fetched {len(raw_content)} bytes")
                    
                    cleaned_doc = self.cleaner.clean(
                        raw_content,
                        {"url": url},
                        progress_callback
                    )
                    
                    if cleaned_doc.get('status') == 'success':
                        content_length = len(cleaned_doc.get('content', ''))
                        self.logger.info(f"  ✓ Cleaned successfully ({content_length} chars)")
                        documents.append(cleaned_doc)
                        
                        # Save document to file
                        from pathlib import Path
                        backend_root = Path(__file__).parent.parent.parent.parent
                        kb_dir = backend_root / "data" / "knowledge_bases" / self.crawler.kb_id
                        doc_dir = kb_dir / "documents"
                        doc_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Create safe filename from URL
                        safe_name = url.replace('https://', '').replace('http://', '').replace('/', '_')
                        if len(safe_name) > 200:
                            safe_name = safe_name[:200]
                        doc_path = doc_dir / f"{safe_name}.txt"
                        
                        with open(doc_path, 'w', encoding='utf-8') as f:
                            f.write(f"URL: {url}\n")
                            f.write(f"Title: {cleaned_doc.get('metadata', {}).get('title', 'N/A')}\n")
                            f.write(f"Content Length: {content_length}\n")
                            f.write("=" * 80 + "\n\n")
                            f.write(cleaned_doc.get('content', ''))
                        
                        self.logger.info(f"  Saved to: {doc_path}")
                    else:
                        self.logger.warning(f"  ⚠ Cleaning failed: {cleaned_doc.get('error', 'Unknown error')}")
                    
                    if progress_callback:
                        progress = int(((i + 1) / len(urls)) * 100)
                        progress_callback(
                            IngestionPhase.CLEANING,
                            progress,
                            f"Cleaned {i+1}/{len(urls)} documents",
                            {"documents_cleaned": len(documents)}
                        )
                        
                except Exception as e:
                    self.logger.error(f"  ✗ Failed to clean {url}: {e}", exc_info=True)
            
            self.logger.info(f"✓ Cleaning complete: {len(documents)}/{len(urls)} documents successfully processed")
            
            if not documents:
                raise ValueError(f"No documents successfully cleaned from {len(urls)} URLs")
            
            # Phase 3: Build Index
            self.logger.info("=" * 80)
            self.logger.info("PHASE 3: BUILDING INDEX")
            self.logger.info("=" * 80)
            if progress_callback:
                progress_callback(IngestionPhase.INDEXING, 0, f"Building index from {len(documents)} documents...", {})
            
            self.logger.info(f"Starting indexing of {len(documents)} documents...")
            index_path = self.indexer.build_index(documents, progress_callback)
            self.logger.info(f"✓ Index built at: {index_path}")
            
            # Get chunk count
            chunks = self.indexer.chunk_documents(documents)
            self.logger.info(f"✓ Created {len(chunks)} chunks from {len(documents)} documents")
            
            self.logger.info("=" * 80)
            self.logger.info("INGESTION COMPLETE")
            self.logger.info("=" * 80)
            self.logger.info(f"  URLs crawled: {len(urls)}")
            self.logger.info(f"  Documents processed: {len(documents)}")
            self.logger.info(f"  Chunks created: {len(chunks)}")
            self.logger.info(f"  Index location: {index_path}")
            self.logger.info("=" * 80)
            
            if progress_callback:
                progress_callback(
                    IngestionPhase.COMPLETED,
                    100,
                    "Ingestion completed successfully",
                    {
                        "urls_crawled": len(urls),
                        "documents_processed": len(documents),
                        "chunks_created": len(chunks)
                    }
                )
            
            return {
                'success': True,
                'index_path': index_path,
                'documents_processed': len(documents),
                'chunks_created': len(chunks),
                'urls_crawled': len(urls)
            }
            
        except Exception as e:
            self.logger.error(f"Ingestion pipeline failed: {e}", exc_info=True)
            if progress_callback:
                progress_callback(IngestionPhase.FAILED, 0, f"Ingestion failed: {str(e)}", {})
            return {
                'success': False,
                'error': str(e)
            }
