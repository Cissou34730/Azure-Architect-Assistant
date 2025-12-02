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
    
    def __init__(self, kb_id: str, job=None, state=None):
        self.kb_id = kb_id
        self.job = job  # Optional: for cancellation support
        self.state = state  # Thread-safe state checking
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
        
        # Reduced verbose logging: keep only high-level start/end and cancellations
        
        # Store start_url and url_prefix for state saving
        self.start_url = start_url
        self.url_prefix = url_prefix
        
        # Initialize state - MUST track visited URLs to prevent infinite loops
        last_id = 0
        visited: Set[str] = set()  # Critical: prevents re-crawling and infinite loops
        to_visit: List[str] = [start_url]
        current_batch: List[Document] = []
        total_documents = 0
        pages_since_checkpoint = 0
        failed_count = 0
        
        state_path = self._get_state_path()
        
        # Try to load existing state
        if state_path.exists():
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    crawl_state = data.get('crawl', {})
                    last_id = crawl_state.get('last_doc_id', 0)
                    visited = set(crawl_state.get('visited_urls', []))  # Restore visited URLs
                    failed_count = crawl_state.get('pages_failed', 0)
                    to_visit = crawl_state.get('pending_urls', [start_url])
                    # Resume summary only (verbosity reduced)
                    logger.info(f"Resuming crawl: visited={len(visited)}, queued={len(to_visit)}")
            except Exception as e:
                logger.warning(f"Could not load state: {e}, starting fresh")
        
        logger.info(f"Crawler start: {start_url} (limit={max_pages})")
        
        while to_visit and len(visited) < max_pages:
            # Cooperative pause/cancel check using shared state
            if self.state:
                if self.state.cancel_requested:
                    logger.info(f"Crawler cancelled at {len(visited)} pages")
                    # Save state before exiting
                    self._save_state(visited, failed_count, to_visit, last_id)
                    if current_batch:
                        yield current_batch
                    return
                
                # Return immediately on pause - pipeline will handle resume from state
                if self.state.paused:
                    logger.info(f"Crawler paused at {len(visited)} pages")
                    # Save state before pausing
                    self._save_state(visited, failed_count, to_visit, last_id)
                    if current_batch:
                        yield current_batch
                    return
            
            url = to_visit.pop(0)
            
            # Skip if already visited or doesn't match semantic path
            if url in visited or not self._is_valid_url(url):
                continue
            
            # Assign sequential ID and mark as visited
            last_id += 1
            visited.add(url)
            
            # Removed per-URL progress log
            
            # Fetch page once and extract both content and links
            html_content, final_url = self._fetch_html_with_redirect(url)
            
            if not html_content:
                logger.warning(f"  ✗ Failed to fetch page")
                failed_count += 1
                # Still save state periodically
                pages_since_checkpoint += 1
                if pages_since_checkpoint >= checkpoint_interval:
                    self._save_state(visited, failed_count, to_visit, last_id)
                    pages_since_checkpoint = 0
                time.sleep(0.2)
                continue
            
            # If redirected, mark final URL as visited too
            if final_url and final_url != url:
                # Suppress redirect detail log
                visited.add(final_url)
            
            # Extract clean text content using trafilatura
            content = trafilatura.extract(html_content, include_comments=False, include_tables=True)
            if content:
                doc = Document(
                    text=content,
                    metadata={
                        'doc_id': last_id,
                        'source_type': 'website',
                        'url': final_url or url,  # Use final URL after redirect
                        'original_url': url if final_url and final_url != url else None,
                        'kb_id': self.kb_id,
                        'date_ingested': datetime.now().isoformat()
                    }
                )
                current_batch.append(doc)
                total_documents += 1
                # Suppress per-document ingestion log
                
                # Yield batch when it reaches batch_size
                if len(current_batch) >= batch_size:
                    # Batch yield (log removed for verbosity reduction)
                    yield current_batch
                    current_batch = []
            else:
                logger.warning(f"  ✗ Failed to extract content")
            
            # Extract links from same HTML
            # Link extraction (details suppressed)
            links = self._extract_links(html_content, final_url or url)
            
            if links:
                new_count = 0
                for link in links:
                    if link not in visited and link not in to_visit:
                        to_visit.append(link)
                        new_count += 1
                
                # Queue growth summary omitted for verbosity reduction
            
            # Per-iteration queue status suppressed
            
            # Save state periodically
            pages_since_checkpoint += 1
            if pages_since_checkpoint >= checkpoint_interval:
                self._save_state(visited, failed_count, to_visit, last_id)
                pages_since_checkpoint = 0
            
            # Rate limiting
            time.sleep(0.5)
        
        # Yield any remaining documents in final batch
        if current_batch:
            yield current_batch
        
        # Final state save
        self._save_state(visited, failed_count, to_visit, last_id)
        
        logger.info("="*70)
        logger.info("CRAWLER COMPLETE")
        logger.info("="*70)
        logger.info(f"Visited: {len(visited)} pages")
        logger.info(f"Ingested: {total_documents} documents")
        logger.info(f"Failed: {failed_count} pages")
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
    
    def _get_state_path(self) -> Path:
        """Get path to unified state file."""
        backend_root = Path(__file__).parent.parent.parent.parent.parent.parent
        state_dir = backend_root / "data" / "knowledge_bases" / self.kb_id
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir / "state.json"
    
    def _save_state(self, visited: Set[str], failed_count: int, to_visit: List[str], last_id: int):
        """Save crawler state to unified state.json."""
        try:
            state_path = self._get_state_path()
            
            # Load existing state (preserve other sections like job, processing)
            state = {}
            if state_path.exists():
                try:
                    with open(state_path, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                except Exception:
                    state = {}
            
            # Update only crawl section
            state['kb_id'] = self.kb_id
            state['version'] = 1
            state['updated_at'] = datetime.now().isoformat()
            state['crawl'] = {
                'last_doc_id': last_id,
                'pages_crawled': len(visited),
                'pages_queued': len(to_visit),
                'pages_failed': failed_count,
                'visited_urls': list(visited),  # Critical: prevents infinite loops
                'pending_urls': to_visit[:200],  # Only first 200 URLs for resume
                'start_url': getattr(self, 'start_url', ''),
                'url_prefix': getattr(self, 'url_prefix', '')
            }
            
            # Atomic write using tempfile
            import tempfile
            import os
            tmp_fd, tmp_name = tempfile.mkstemp(dir=str(state_path.parent), suffix='.tmp')
            with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
            os.replace(tmp_name, str(state_path))
            
            logger.info(f"✓ State saved: {len(visited)} visited, {len(to_visit)} queued, {failed_count} failed")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
