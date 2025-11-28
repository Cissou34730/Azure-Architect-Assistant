"""
Website Crawler - Orchestrate crawling with checkpointing
"""

import logging
import time
import json
import requests
from typing import List, Set, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from llama_index.core import Document
import trafilatura

logger = logging.getLogger(__name__)


class WebsiteCrawler:
    """
    Orchestrates website crawling with link discovery and checkpointing.
    Makes single HTTP request per URL to extract both content and links.
    """
    
    def __init__(self, kb_id: str, job=None):
        self.kb_id = kb_id
        self.job = job  # Optional: for cancellation support
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.timeout = 15
        self.max_retries = 3
    
    def crawl(
        self,
        start_url: str,
        url_prefix: str = None,
        max_pages: int = 1000,
        checkpoint_interval: int = 50,
        batch_size: int = 10
    ):
        """
        Crawl a website starting from start_url, yielding batches of documents.
        
        Args:
            start_url: Starting URL
            url_prefix: Only crawl URLs starting with this prefix (defaults to start_url)
            max_pages: Maximum pages to crawl
            checkpoint_interval: Save checkpoint every N pages
            batch_size: Number of documents to yield per batch
            
        Yields:
            Batches of Documents (list of up to batch_size documents)
        """
        # Use start_url as prefix if not provided
        if not url_prefix:
            url_prefix = start_url.rstrip('/')
        
        # Extract semantic path (handles language codes like /en-us/)
        self.semantic_path = self._extract_semantic_path(url_prefix)
        self.base_domain = urlparse(url_prefix).netloc
        
        logger.info(f"Semantic path extracted: {self.semantic_path}")
        logger.info(f"Base domain: {self.base_domain}")
        
        # Initialize state with ID tracking
        url_id_map: Dict[str, int] = {}  # url -> sequential ID
        last_id = 0
        visited: Set[str] = set()
        to_visit: List[str] = [start_url]
        current_batch: List[Document] = []
        total_documents = 0
        pages_since_checkpoint = 0
        
        checkpoint_path = self._get_checkpoint_path()
        
        # Try to load existing checkpoint
        if checkpoint_path.exists():
            try:
                with open(checkpoint_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    url_id_map = data.get('url_id_map', {})
                    last_id = data.get('last_id', 0)
                    visited = set(data.get('visited', []))
                    to_visit = data.get('to_visit', [start_url])
                    logger.info(f"Resuming from checkpoint: ID={last_id}, visited={len(visited)}, queued={len(to_visit)}")
            except Exception as e:
                logger.warning(f"Could not load checkpoint: {e}, starting fresh")
        
        logger.info("="*70)
        logger.info("CRAWLER STARTING")
        logger.info("="*70)
        logger.info(f"Start URL: {start_url}")
        logger.info(f"URL prefix: {url_prefix}")
        logger.info(f"Max pages: {max_pages}")
        logger.info(f"Checkpoint: every {checkpoint_interval} pages at {checkpoint_path}")
        logger.info("="*70)
        
        while to_visit and len(visited) < max_pages:
            # Check for cancellation or pause
            if self.job:
                logger.debug(f"CRAWLER CHECK: job.status = {self.job.status}, job.status.value = {self.job.status.value}")
            
            if self.job and self.job.status.value == 'cancelled':
                logger.info(f"Crawl cancelled by user at {len(visited)} pages")
                # Save checkpoint before exiting
                self._save_checkpoint(checkpoint_path, visited, to_visit, url_id_map, last_id)
                # Yield any remaining documents
                if current_batch:
                    logger.info(f"Yielding final batch of {len(current_batch)} documents before cancellation")
                    yield current_batch
                return
            
            if self.job and self.job.status.value == 'paused':
                logger.info(f"Crawl paused by user at {len(visited)} pages")
                # Save checkpoint before pausing
                self._save_checkpoint(checkpoint_path, visited, to_visit, url_id_map, last_id)
                # Yield any remaining documents
                if current_batch:
                    logger.info(f"Yielding final batch of {len(current_batch)} documents before pause")
                    yield current_batch
                return
            
            url = to_visit.pop(0)
            
            # Skip if already visited or doesn't match semantic path
            if url in visited or not self._is_valid_url(url):
                continue
            
            # Assign sequential ID if not already assigned
            if url not in url_id_map:
                last_id += 1
                url_id_map[url] = last_id
            
            url_id = url_id_map[url]
            visited.add(url)
            logger.info(f"[{len(visited)}/{max_pages}] ID={url_id}: {url}")
            
            # Fetch page once and extract both content and links
            html_content, final_url = self._fetch_html_with_redirect(url)
            
            if not html_content:
                logger.warning(f"  ✗ Failed to fetch page")
                # Still increment checkpoint counter but skip processing
                pages_since_checkpoint += 1
                if pages_since_checkpoint >= checkpoint_interval:
                    self._save_checkpoint(checkpoint_path, visited, to_visit, url_id_map, last_id)
                    pages_since_checkpoint = 0
                time.sleep(0.5)
                continue
            
            # If redirected, mark final URL as visited too
            if final_url and final_url != url:
                logger.info(f"  → Redirected to: {final_url}")
                visited.add(final_url)
            
            # Extract clean text content using trafilatura
            content = trafilatura.extract(html_content, include_comments=False, include_tables=True)
            if content:
                doc = Document(
                    text=content,
                    metadata={
                        'doc_id': url_id,
                        'source_type': 'website',
                        'url': final_url or url,  # Use final URL after redirect
                        'original_url': url if final_url and final_url != url else None,
                        'kb_id': self.kb_id,
                        'date_ingested': datetime.now().isoformat()
                    }
                )
                current_batch.append(doc)
                total_documents += 1
                logger.info(f"  ✓ Ingested ({len(content)} chars)")
                
                # Yield batch when it reaches batch_size
                if len(current_batch) >= batch_size:
                    logger.info(f"✓ Yielding batch of {len(current_batch)} documents")
                    yield current_batch
                    current_batch = []
            else:
                logger.warning(f"  ✗ Failed to extract content")
            
            # Extract links from same HTML
            logger.info(f"  → Extracting links...")
            links = self._extract_links(html_content, final_url or url)  # Use final URL for relative links
            logger.info(f"  → Found {len(links)} valid links")
            
            if links:
                new_count = 0
                for link in links:
                    if link not in visited and link not in to_visit:
                        to_visit.append(link)
                        new_count += 1
                
                logger.info(f"  → Added {new_count} new links to queue")
                if new_count > 0 and len(links) <= 5:
                    for link in links[:5]:
                        logger.info(f"     • {link}")
            
            logger.info(f"  → Queue: {len(to_visit)} to visit, {len(visited)} visited")
            
            # Checkpoint
            pages_since_checkpoint += 1
            if pages_since_checkpoint >= checkpoint_interval:
                self._save_checkpoint(checkpoint_path, visited, to_visit, url_id_map, last_id)
                pages_since_checkpoint = 0
            
            # Rate limiting
            time.sleep(0.5)
        
        # Yield any remaining documents in final batch
        if current_batch:
            logger.info(f"✓ Yielding final batch of {len(current_batch)} documents")
            yield current_batch
        
        # Final checkpoint
        self._save_checkpoint(checkpoint_path, visited, to_visit, url_id_map, last_id)
        
        logger.info("="*70)
        logger.info("CRAWLER COMPLETE")
        logger.info("="*70)
        logger.info(f"Visited: {len(visited)} pages")
        logger.info(f"Ingested: {total_documents} documents")
        logger.info("="*70)
    
    def _extract_semantic_path(self, url: str) -> str:
        """
        Extract semantic path from URL, removing language codes.
        
        Examples:
            https://learn.microsoft.com/en-us/azure/caf/ -> /azure/caf/
            https://learn.microsoft.com/azure/caf/ -> /azure/caf/
            https://learn.microsoft.com/fr-fr/azure/caf/ -> /azure/caf/
        """
        parsed = urlparse(url)
        path = parsed.path
        
        # Remove language codes (e.g., /en-us/, /fr-fr/, /ja-jp/)
        # Pattern: /xx-xx/ at the start of path
        import re
        path = re.sub(r'^/[a-z]{2}-[a-z]{2}/', '/', path)
        
        return path.rstrip('/')
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Check if URL matches the semantic path (ignoring language codes).
        """
        parsed = urlparse(url)
        
        # Must be same domain
        if parsed.netloc != self.base_domain:
            return False
        
        # Extract semantic path from this URL
        url_semantic_path = self._extract_semantic_path(url)
        
        # Check if it starts with our target semantic path
        if not url_semantic_path.startswith(self.semantic_path):
            return False
        
        # Exclude media files
        excluded_extensions = ('.pdf', '.zip', '.png', '.jpg', '.gif', '.svg', '.mp4', '.exe')
        if url.lower().endswith(excluded_extensions):
            return False
        
        return True
    
    def _fetch_html_with_redirect(self, url: str):
        """
        Fetch HTML content from URL with retries.
        Follows redirects automatically and returns final URL.
        
        Returns:
            Tuple of (html_content, final_url) or (None, None) on failure
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url, 
                    timeout=self.timeout, 
                    headers=self.headers,
                    allow_redirects=True  # Follow redirects
                )
                response.raise_for_status()
                
                # Get final URL after redirects
                final_url = response.url if response.history else url
                
                return response.text, final_url
            except requests.exceptions.HTTPError as e:
                # Don't retry on 4xx client errors (404, 403, etc.)
                if 400 <= e.response.status_code < 500:
                    logger.warning(f"  ✗ Client error {e.response.status_code}: {url} (skipping)")
                    return None, None
                # Retry on 5xx server errors
                if attempt < self.max_retries - 1:
                    logger.warning(f"  Server error: {e}, retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    logger.error(f"  Failed after {self.max_retries} attempts: {e}")
                    return None, None
            except requests.exceptions.RequestException as e:
                # Retry on network errors
                if attempt < self.max_retries - 1:
                    logger.warning(f"  Request failed: {e}, retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    logger.error(f"  Failed after {self.max_retries} attempts: {e}")
                    return None, None
        return None, None
    
    def _extract_links(self, html: str, current_url: str) -> List[str]:
        """
        Extract all valid links from HTML content.
        """
        try:
            soup = BeautifulSoup(html, 'lxml')
            links = []
            
            for anchor in soup.find_all('a', href=True):
                href = anchor['href']
                
                # Skip fragments, javascript, mailto
                if href.startswith(('#', 'javascript:', 'mailto:')):
                    continue
                
                # Convert to absolute URL
                absolute_url = urljoin(current_url, href)
                
                # Normalize (remove fragment and trailing slash)
                normalized_url = self._normalize_url(absolute_url)
                
                # Validate against semantic path
                if normalized_url and self._is_valid_url(normalized_url):
                    links.append(normalized_url)
            
            # Deduplicate
            return list(set(links))
            
        except Exception as e:
            logger.error(f"  Error extracting links: {e}")
            return []
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL by removing fragments and trailing slashes.
        """
        try:
            # Remove fragment
            url = url.split('#')[0]
            # Remove trailing slash
            url = url.rstrip('/')
            # Validate
            if not url.startswith(('http://', 'https://')):
                return ''
            return url
        except Exception:
            return ''
    
    def _get_checkpoint_path(self) -> Path:
        """Get path for checkpoint file."""
        backend_root = Path(__file__).parent.parent.parent.parent.parent.parent
        checkpoint_dir = backend_root / "data" / "knowledge_bases" / self.kb_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        return checkpoint_dir / "crawl_checkpoint.json"
    
    def _save_checkpoint(self, checkpoint_path: Path, visited: Set[str], to_visit: List[str], url_id_map: Dict[str, int], last_id: int):
        """Save crawl state to checkpoint file with ID tracking."""
        try:
            data = {
                'kb_id': self.kb_id,
                'timestamp': datetime.now().isoformat(),
                'last_id': last_id,
                'pages_total': len(url_id_map),
                'pages_crawled': len(visited),
                'visited_count': len(visited),
                'queued_count': len(to_visit),
                'url_id_map': url_id_map,
                'visited': list(visited),
                'to_visit': to_visit
            }
            
            with open(checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"✓ Checkpoint saved: ID={last_id}, {len(visited)} visited, {len(to_visit)} queued")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
