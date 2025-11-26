"""
Web Documentation Crawler - Generic implementation for documentation sites
Handles structured documentation like Microsoft Learn, ReadTheDocs, etc.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque
from typing import Set, List, Dict, Any, Optional
import time
import logging

from ..base import DocumentCrawler

logger = logging.getLogger(__name__)


class WebDocumentationCrawler(DocumentCrawler):
    """
    Generic crawler for documentation websites.
    Supports configurable path filtering and domain restrictions.
    """
    
    def __init__(self, kb_id: str, config: Dict[str, Any]):
        """
        Initialize crawler.
        
        Args:
            kb_id: Knowledge base ID
            config: Configuration with:
                - start_url: Starting URL for crawling
                - max_depth: Maximum depth for BFS (default: 3)
                - max_pages: Maximum pages to crawl (default: 500)
                - delay: Delay between requests in seconds (default: 0.5)
                - allowed_paths: List of path prefixes to include (optional)
                - excluded_extensions: List of file extensions to exclude (optional)
                - allowed_domains: List of domains to include (optional, default: start_url domain)
        """
        super().__init__(kb_id, config)
        
        self.start_url = config['start_url']
        self.max_depth = config.get('max_depth', 3)
        self.max_pages = config.get('max_pages', 500)
        self.delay = config.get('delay', 0.5)
        
        # Parse base domain
        parsed = urlparse(self.start_url)
        self.base_domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # Configuration
        self.allowed_paths = config.get('allowed_paths', [parsed.path.rstrip('/')])
        self.excluded_extensions = config.get('excluded_extensions', [
            '.pdf', '.zip', '.png', '.jpg', '.gif', '.svg', '.mp4', '.mp3'
        ])
        self.allowed_domains = config.get('allowed_domains', [parsed.netloc])
        
        # Tracking
        self.visited: Set[str] = set()
        self.urls: List[Dict[str, Any]] = []
        
        self.logger.info(f"Initialized for {self.start_url}")
        self.logger.info(f"  Max depth: {self.max_depth}, Max pages: {self.max_pages}")
        self.logger.info(f"  Allowed paths: {self.allowed_paths}")
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for crawling."""
        parsed = urlparse(url)
        
        # Skip common media file extensions
        skip_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico',  # Images
            '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',  # Videos
            '.mp3', '.wav', '.ogg', '.flac',  # Audio
            '.zip', '.tar', '.gz', '.rar',  # Archives
            '.exe', '.dmg', '.pkg', '.deb'  # Executables
        ]
        url_lower = url.lower()
        if any(url_lower.endswith(ext) for ext in skip_extensions):
            return False
        
        # Check domain
        if not any(parsed.netloc.endswith(domain) for domain in self.allowed_domains):
            return False
        
        # Check path - must start with one of the allowed paths
        if self.allowed_paths:
            path_valid = any(parsed.path.startswith(path) for path in self.allowed_paths)
            if not path_valid:
                return False
        
        # Exclude media and downloads
        if any(parsed.path.lower().endswith(ext) for ext in self.excluded_extensions):
            return False
        
        return True
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and query parameters."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    def extract_links(self, html: str, current_url: str) -> List[str]:
        """Extract all valid links from HTML content."""
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(current_url, href)
            normalized = self.normalize_url(absolute_url)
            
            if self.is_valid_url(normalized):
                links.append(normalized)
        
        return links
    
    def fetch_content(self, url: str) -> str:
        """Fetch HTML content from URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return ""
    
    def crawl(self, progress_callback: Optional[callable] = None) -> List[str]:
        """
        Perform BFS crawl starting from start_url.
        
        Args:
            progress_callback: Optional callback(current, total, message)
            
        Returns:
            List of discovered URLs
        """
        # Initialize queue with (url, depth)
        queue = deque([(self.start_url, 0)])
        self.visited.add(self.start_url)
        
        self.logger.info(f"Starting crawl from {self.start_url}")
        
        while queue and len(self.visited) < self.max_pages:
            url, depth = queue.popleft()
            
            # Check depth limit
            if depth > self.max_depth:
                continue
            
            # Fetch page
            html = self.fetch_content(url)
            if not html:
                continue
            
            # Store URL
            self.urls.append({
                'url': url,
                'depth': depth
            })
            
            # Progress callback - skip, handled at pipeline level
            # if progress_callback and len(self.visited) % 10 == 0:
            #     progress_callback(...)
            
            # Extract and queue links
            if depth < self.max_depth:
                links = self.extract_links(html, url)
                for link in links:
                    if link not in self.visited:
                        self.visited.add(link)
                        queue.append((link, depth + 1))
            
            # Rate limiting
            time.sleep(self.delay)
            
            # Log progress
            if len(self.visited) % 50 == 0:
                self.logger.info(f"Crawled {len(self.visited)} pages, queue size: {len(queue)}")
        
        self.logger.info(f"Crawl complete: {len(self.urls)} pages discovered")
        
        return [item['url'] for item in self.urls]
    
    def save_urls(self, output_file: str):
        """Save crawled URLs to file."""
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in self.urls:
                f.write(f"{item['url']}\n")
        
        self.logger.info(f"Saved {len(self.urls)} URLs to {output_file}")
