"""
Website Source Handler - Main orchestrator
Uses modular components for crawling, parsing, and content fetching.
"""

import logging
from typing import List, Dict, Any
from urllib.parse import urlparse

from llama_index.core import Document
from trafilatura.sitemaps import sitemap_search

from ..base import BaseSourceHandler
from .crawler import WebsiteCrawler
from .content_fetcher import ContentFetcher
from .sitemap_parser import SitemapParser

logger = logging.getLogger(__name__)


class WebsiteSourceHandler(BaseSourceHandler):
    """
    Handle website ingestion with multiple modes:
    1. Explicit sitemap_url → Parse sitemap
    2. start_url → Try sitemap discovery → Fallback to crawling
    3. Direct urls → Ingest specific URLs
    """
    
    # Domains with massive sitemaps - skip auto-discovery
    PROBLEMATIC_DOMAINS = [
        'learn.microsoft.com',
        'docs.microsoft.com',
        'developer.mozilla.org',
        'docs.aws.amazon.com'
    ]
    
    def __init__(self, kb_id: str, job=None):
        super().__init__(kb_id)
        self.job = job  # For cancellation support
        self.crawler = WebsiteCrawler(kb_id, job=job)
        self.content_fetcher = ContentFetcher()
        self.sitemap_parser = SitemapParser()
        logger.info(f"WebsiteSourceHandler initialized for KB: {kb_id}")
    
    def ingest(self, config: Dict[str, Any]) -> List[Document]:
        """
        Ingest websites based on config.
        
        Args:
            config: Must contain one of:
                   - 'sitemap_url': Parse sitemap.xml
                   - 'start_url': Auto-discover sitemap or crawl
                   - 'urls': List of specific URLs
                   Optional:
                   - 'url_prefix': Filter/restrict URLs to this prefix
                   - 'max_pages': Maximum pages to crawl (default: 1000)
            
        Returns:
            List of Documents
        """
        logger.info("="*70)
        logger.info("WebsiteSourceHandler.ingest() called")
        logger.info(f"Config: {config}")
        logger.info("="*70)
        
        url_prefix = config.get('url_prefix')
        max_pages = config.get('max_pages', 1000)
        
        # Mode 1: Explicit sitemap
        if 'sitemap_url' in config:
            logger.info("MODE 1: Explicit sitemap_url")
            return self._ingest_from_sitemap(config['sitemap_url'], url_prefix)
        
        # Mode 2: start_url (try sitemap → fallback to crawl)
        if 'start_url' in config:
            logger.info("MODE 2: start_url (sitemap discovery → crawl fallback)")
            start_url = config['start_url']
            
            # Check if domain has massive sitemaps
            domain = urlparse(start_url).netloc.lower()
            if any(prob in domain for prob in self.PROBLEMATIC_DOMAINS):
                logger.info(f"⚠ Domain '{domain}' has massive sitemaps - skipping discovery")
                logger.info("Using crawler directly")
                return self.crawler.crawl(start_url, url_prefix, max_pages)
            
            # Try sitemap discovery
            logger.info(f"Attempting sitemap discovery for: {start_url}")
            try:
                sitemap_urls = sitemap_search(start_url, target_lang=None)
                
                if sitemap_urls:
                    logger.info(f"✓ Found sitemap with {len(sitemap_urls)} URLs")
                    urls_list = list(sitemap_urls)
                    return self._ingest_urls(urls_list, url_prefix)
                else:
                    logger.info("✗ No sitemap found - using crawler")
                    return self.crawler.crawl(start_url, url_prefix, max_pages, batch_size=10)
                    
            except Exception as e:
                logger.warning(f"Sitemap discovery failed: {e}")
                logger.info("Falling back to crawler")
                return self.crawler.crawl(start_url, url_prefix, max_pages, batch_size=10)
        
        # Mode 3: Direct URLs
        if 'urls' in config:
            logger.info("MODE 3: Direct URLs list")
            return self._ingest_urls(config['urls'], url_prefix)
        
        raise ValueError("Config must have 'sitemap_url', 'start_url', or 'urls'")
    
    def _ingest_from_sitemap(self, sitemap_url: str, url_prefix: str = None) -> List[Document]:
        """Parse sitemap and ingest URLs."""
        urls = self.sitemap_parser.parse_sitemap(sitemap_url)
        logger.info(f"Sitemap contains {len(urls)} URLs")
        
        # Deduplicate
        urls = list(set(urls))
        logger.info(f"After deduplication: {len(urls)} unique URLs")
        
        return self._ingest_urls(urls, url_prefix)
    
    def _ingest_urls(self, urls: List[str], url_prefix: str = None) -> List[Document]:
        """Ingest specific list of URLs."""
        # Filter by prefix
        if url_prefix:
            filtered = [url for url in urls if url.startswith(url_prefix)]
            logger.info(f"URL prefix filter: '{url_prefix}'")
            logger.info(f"  Kept {len(filtered)}/{len(urls)} URLs")
            urls = filtered
        
        documents = []
        logger.info(f"Ingesting {len(urls)} URLs...")
        
        for i, url in enumerate(urls, 1):
            logger.info(f"[{i}/{len(urls)}] Fetching: {url}")
            
            content = self.content_fetcher.fetch_content(url)
            if content:
                from datetime import datetime
                doc = Document(
                    text=content,
                    metadata={
                        'source_type': 'website',
                        'url': url,
                        'kb_id': self.kb_id,
                        'date_ingested': datetime.now().isoformat()
                    }
                )
                documents.append(doc)
                logger.info(f"  ✓ Ingested ({len(content)} chars)")
            else:
                logger.warning(f"  ✗ Failed to fetch content")
        
        logger.info(f"Ingestion complete: {len(documents)}/{len(urls)} successful")
        return documents
