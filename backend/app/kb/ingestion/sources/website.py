"""
Website Source Handler
Handles website ingestion using Trafilatura.
"""

import logging
from typing import List, Dict, Any, Set
from datetime import datetime
from urllib.parse import urljoin, urlparse
import requests
import time
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from bs4 import BeautifulSoup

from llama_index.core import Document
import trafilatura
from trafilatura.sitemaps import sitemap_search

from .base import BaseSourceHandler

logger = logging.getLogger(__name__)


class WebsiteSourceHandler(BaseSourceHandler):
    """
    Handle website ingestion using TrafilaturaWebReader.
    Replaces BeautifulSoup + html2text + Readability.
    """
    
    def __init__(self, kb_id: str):
        super().__init__(kb_id)
        logger.info(f"WebsiteSourceHandler initialized for KB: {kb_id}")
    
    def ingest(self, config: Dict[str, Any]) -> List[Document]:
        """
        Ingest websites from config.
        
        Priority:
        1. Explicit sitemap_url → Use sitemap
        2. start_url → Try sitemap discovery → Fallback to BS4 crawling
        3. Direct urls → Ingest specific URLs
        
        Args:
            config: Must contain one of:
                   - 'sitemap_url': Parse sitemap.xml
                   - 'urls': List of specific URLs  
                   - 'start_url': Auto-discover sitemap or crawl
                   Optional:
                   - 'url_prefix': Filter/restrict URLs to this prefix
                   - 'max_pages': Maximum pages to crawl (default: 1000)
            
        Returns:
            List of Documents
        """
        logger.info("="*70)
        logger.info("WebsiteSourceHandler.ingest() called")
        logger.info(f"Config received: {config}")
        logger.info(f"  sitemap_url: {'sitemap_url' in config}")
        logger.info(f"  start_url: {'start_url' in config}")
        logger.info(f"  urls: {'urls' in config}")
        logger.info("="*70)
        
        url_prefix = config.get('url_prefix')
        max_pages = config.get('max_pages', 1000)
        
        # Mode 1: Explicit sitemap
        if 'sitemap_url' in config:
            logger.info(">>> MODE 1: Using explicit sitemap_url")
            return self.ingest_sitemap(config['sitemap_url'], url_prefix)
        
        # Mode 2: Auto-discover sitemap or crawl
        if 'start_url' in config:
            logger.info(">>> MODE 2: Using start_url (try sitemap discovery → fallback to BS4)")
            start_url = config['start_url']
            
            # Check if this is a known problematic domain for sitemap discovery
            parsed_url = urlparse(start_url)
            problematic_domains = [
                'learn.microsoft.com',
                'docs.microsoft.com',
                'developer.mozilla.org',
                'docs.aws.amazon.com'
            ]
            
            domain = parsed_url.netloc.lower()
            if any(prob_domain in domain for prob_domain in problematic_domains):
                logger.info(f"⚠ Domain '{domain}' has massive sitemaps")
                logger.info("  Skipping sitemap discovery, using BS4 crawler with url_prefix filter")
                return self.crawl_website_bs4(start_url, url_prefix, max_pages)
            
            # Try sitemap discovery for other domains
            logger.info(f"Attempting sitemap discovery for: {start_url}")
            try:
                sitemap_urls = sitemap_search(start_url, target_lang=None)
                
                if sitemap_urls:
                    logger.info(f"✓ Sitemap discovery successful! Found {len(sitemap_urls)} URLs")
                    logger.info(f"  Sample URLs: {list(sitemap_urls)[:3]}")
                    
                    # Convert generator/set to list and ingest
                    urls_list = list(sitemap_urls)
                    return self.ingest_urls(urls_list, url_prefix)
                else:
                    logger.info("✗ No sitemap found, falling back to BS4 crawler")
                    return self.crawl_website_bs4(start_url, url_prefix, max_pages)
                    
            except Exception as e:
                logger.warning(f"Sitemap discovery failed: {e}")
                logger.info("Falling back to BS4 crawler")
                return self.crawl_website_bs4(start_url, url_prefix, max_pages)
        
        # Mode 3: Direct URLs
        if 'urls' in config:
            logger.info(">>> MODE 3: Using direct URLs list (no crawling)")
            return self.ingest_urls(config['urls'], url_prefix)
        
        logger.error("No valid config found! Must have 'sitemap_url', 'start_url', or 'urls'")
        raise ValueError("Website config requires 'urls', 'sitemap_url', or 'start_url'")
    
    def ingest_urls(self, urls: List[str], url_prefix: str = None) -> List[Document]:
        """
        Ingest documents from URLs using Trafilatura.
        
        Args:
            urls: List of URLs to crawl
            url_prefix: Optional URL prefix filter (only ingest URLs starting with this)
            
        Returns:
            List of LlamaIndex Documents
        """
        documents = []
        filtered_urls = self._filter_urls(urls, url_prefix)
        
        logger.info(f"Ingesting {len(filtered_urls)} URLs (filtered from {len(urls)} total)")
        
        for url in filtered_urls:
            try:
                logger.info(f"Fetching URL: {url}")
                
                # Use trafilatura directly instead of TrafilaturaWebReader
                downloaded = trafilatura.fetch_url(url)
                if not downloaded:
                    logger.warning(f"Failed to download {url}")
                    continue
                
                text = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
                if not text:
                    logger.warning(f"Failed to extract content from {url}")
                    continue
                
                # Create LlamaIndex Document
                doc = Document(
                    text=text,
                    metadata={
                        'source_type': 'website',
                        'url': url,
                        'kb_id': self.kb_id,
                        'date_ingested': datetime.now().isoformat()
                    }
                )
                
                documents.append(doc)
                logger.info(f"Successfully ingested content from {url}")
                
            except Exception as e:
                logger.error(f"Failed to ingest {url}: {e}")
        
        return documents
    
    def ingest_sitemap(self, sitemap_url: str, url_prefix: str = None) -> List[Document]:
        """
        Parse sitemap and ingest URLs, optionally filtered by prefix.
        
        Args:
            sitemap_url: URL to sitemap.xml
            url_prefix: Optional URL prefix filter (only ingest URLs starting with this)
            
        Returns:
            List of LlamaIndex Documents
        """
        urls = self._parse_sitemap(sitemap_url)
        logger.info(f"Found {len(urls)} URLs in sitemap: {sitemap_url}")
        
        # Deduplicate URLs
        urls = list(set(urls))
        logger.info(f"After deduplication: {len(urls)} unique URLs")
        
        return self.ingest_urls(urls, url_prefix)
    
    def _parse_sitemap(self, sitemap_url: str) -> List[str]:
        """Extract URLs from sitemap.xml"""
        try:
            response = requests.get(sitemap_url, timeout=30)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            urls = []
            
            # Check for sitemap index
            if root.tag.endswith('sitemapindex'):
                for sitemap_elem in root.findall('.//ns:loc', namespace):
                    urls.extend(self._parse_sitemap(sitemap_elem.text))
            else:
                # Regular sitemap
                for url_elem in root.findall('.//ns:loc', namespace):
                    urls.append(url_elem.text)
            
            return urls
            
        except Exception as e:
            logger.error(f"Failed to parse sitemap {sitemap_url}: {e}")
            return []
    
    def _filter_urls(self, urls: List[str], url_prefix: str = None) -> List[str]:
        """
        Filter URLs by prefix if provided.
        
        Args:
            urls: List of URLs to filter
            url_prefix: URL prefix (only keep URLs starting with this)
            
        Returns:
            Filtered list of URLs
        """
        if not url_prefix:
            return urls
        
        filtered = [url for url in urls if url.startswith(url_prefix)]
        
        if filtered:
            logger.info(f"URL prefix filter: '{url_prefix}'")
            logger.info(f"  Kept {len(filtered)} URLs, filtered out {len(urls) - len(filtered)} URLs")
        else:
            logger.warning(f"URL prefix filter '{url_prefix}' matched 0 URLs out of {len(urls)}")
        
        return filtered
    
    def crawl_website_bs4(self, start_url: str, url_prefix: str = None, max_pages: int = 1000) -> List[Document]:
        """
        Crawl website using BeautifulSoup4 for link extraction.
        Checkpoints every 50 pages to track progress.
        Ingests content as it crawls (not after).
        
        Args:
            start_url: Starting URL to begin crawling
            url_prefix: Only crawl URLs starting with this prefix
            max_pages: Maximum number of pages to crawl
            
        Returns:
            List of LlamaIndex Documents
        """
        # Use start_url as prefix if no prefix provided
        if not url_prefix:
            url_prefix = start_url.rstrip('/')
        
        # Initialize crawl state
        visited: Set[str] = set()
        to_visit: List[str] = [start_url]
        checkpoint_interval = 50
        pages_since_checkpoint = 0
        all_documents = []
        
        # Setup checkpoint file
        checkpoint_path = self._get_checkpoint_path()
        
        logger.info("="*70)
        logger.info("BS4 CRAWLER STARTING")
        logger.info("="*70)
        logger.info(f"Start URL: {start_url}")
        logger.info(f"URL prefix filter: {url_prefix}")
        logger.info(f"Max pages: {max_pages}")
        logger.info(f"Checkpoint path: {checkpoint_path}")
        logger.info(f"Checkpoint interval: every {checkpoint_interval} pages")
        logger.info("="*70)
        
        while to_visit and len(visited) < max_pages:
            url = to_visit.pop(0)
            
            # Skip if already visited or doesn't match prefix
            if url in visited or not url.startswith(url_prefix):
                continue
            
            visited.add(url)
            logger.info(f"Crawling [{len(visited)}/{max_pages}]: {url}")
            
            # Ingest this URL immediately using requests + trafilatura
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"  → Ingesting content from {url} (attempt {attempt + 1}/{max_retries})")
                    
                    # Use requests instead of trafilatura.fetch_url() for better control
                    response = requests.get(
                        url,
                        timeout=15,
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    )
                    response.raise_for_status()
                    
                    # Use trafilatura to extract clean content from HTML
                    text = trafilatura.extract(response.content, include_comments=False, include_tables=True)
                    if not text:
                        logger.warning(f"  → Failed to extract content from {url}")
                        break
                    
                    # Create LlamaIndex Document
                    doc = Document(
                        text=text,
                        metadata={
                            'source_type': 'website',
                            'url': url,
                            'kb_id': self.kb_id,
                            'date_ingested': datetime.now().isoformat()
                        }
                    )
                    
                    all_documents.append(doc)
                    logger.info(f"  → Successfully ingested 1 document ({len(text)} chars)")
                    break  # Success, exit retry loop
                    
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"  → Request failed: {e}, retrying in 2 seconds...")
                        time.sleep(2)
                    else:
                        logger.error(f"  → Failed to download {url} after {max_retries} attempts: {e}")
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"  → Error ingesting {url}: {e}, retrying...")
                        time.sleep(2)
                    else:
                        logger.error(f"  → Failed to ingest {url} after {max_retries} attempts: {e}")
            
            # Extract links with BS4 (do this even if content extraction failed)
            try:
                logger.info(f"  → Extracting links from {url}...")
                links = self._extract_links_bs4(url, url_prefix)
                logger.info(f"  → Link extraction returned {len(links)} links")
                
                if len(links) > 0:
                    logger.info(f"  → Sample links: {links[:3]}")
                    new_links_added = 0
                    for link in links:
                        if link not in visited and link not in to_visit:
                            to_visit.append(link)
                            new_links_added += 1
                    logger.info(f"  → Added {new_links_added} new links to queue")
                else:
                    logger.warning(f"  → No links found on {url} - crawler will stop if queue is empty")
                    
                logger.info(f"  → Queue now has {len(to_visit)} URLs to visit, {len(visited)} already visited")
            except Exception as e:
                logger.error(f"  → Exception during link extraction from {url}: {e}", exc_info=True)
            
            # Checkpoint every 50 pages
            pages_since_checkpoint += 1
            if pages_since_checkpoint >= checkpoint_interval:
                self._save_checkpoint(checkpoint_path, visited, to_visit)
                pages_since_checkpoint = 0
            
            # Rate limiting
            time.sleep(0.5)
        
        # Final checkpoint
        self._save_checkpoint(checkpoint_path, visited, to_visit)
        
        logger.info("="*70)
        logger.info("BS4 CRAWLER COMPLETE")
        logger.info("="*70)
        logger.info(f"Total URLs visited: {len(visited)}")
        logger.info(f"Total documents ingested: {len(all_documents)}")
        logger.info(f"Documents sample: {[doc.metadata.get('url', 'unknown')[:50] for doc in all_documents[:3]]}")
        logger.info("="*70)
        
        return all_documents
    
    def _extract_links_bs4(self, url: str, url_prefix: str) -> List[str]:
        """
        Extract all links from a page using BeautifulSoup4.
        
        Args:
            url: URL to extract links from
            url_prefix: Only return links starting with this prefix
            
        Returns:
            List of absolute URLs
        """
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url, 
                    timeout=15, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                )
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'lxml')
                links = []
                
                for anchor in soup.find_all('a', href=True):
                    href = anchor['href']
                    
                    # Skip anchors, javascript, mailto, etc
                    if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                        continue
                    
                    # Convert relative URLs to absolute
                    absolute_url = urljoin(url, href)
                    
                    # Normalize URL
                    normalized_url = self._normalize_url(absolute_url)
                    
                    # Only include if matches prefix
                    if normalized_url and normalized_url.startswith(url_prefix):
                        links.append(normalized_url)
                
                unique_links = list(set(links))  # Deduplicate
                logger.info(f"Extracted {len(unique_links)} unique links from {url} (before dedup: {len(links)})")
                
                return unique_links
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Failed to extract links from {url} (attempt {attempt + 1}/{max_retries}): {e}")
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to extract links from {url} after {max_retries} attempts: {e}")
                    return []
            except Exception as e:
                logger.error(f"Unexpected error extracting links from {url}: {e}")
                return []
        
        return []
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL by removing fragments and trailing slashes.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL or empty string if invalid
        """
        try:
            # Remove fragment (#section)
            url = url.split('#')[0]
            
            # Remove trailing slash
            url = url.rstrip('/')
            
            # Basic validation
            if not url.startswith(('http://', 'https://')):
                return ''
            
            return url
        except Exception:
            return ''
    
    def _get_checkpoint_path(self) -> Path:
        """
        Get path for checkpoint file.
        
        Returns:
            Path to checkpoint file
        """
        backend_root = Path(__file__).parent.parent.parent.parent.parent
        checkpoint_dir = backend_root / "data" / "knowledge_bases" / self.kb_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        return checkpoint_dir / "crawl_checkpoint.json"
    
    def _save_checkpoint(self, checkpoint_path: Path, visited: Set[str], to_visit: List[str]):
        """
        Save crawl state to checkpoint file.
        
        Args:
            checkpoint_path: Path to checkpoint file
            visited: Set of visited URLs
            to_visit: List of URLs queued for crawling
        """
        try:
            data = {
                'kb_id': self.kb_id,
                'timestamp': datetime.now().isoformat(),
                'visited_count': len(visited),
                'queued_count': len(to_visit),
                'visited': list(visited),
                'to_visit': to_visit
            }
            
            with open(checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"✓ Checkpoint saved: {len(visited)} visited, {len(to_visit)} queued")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
