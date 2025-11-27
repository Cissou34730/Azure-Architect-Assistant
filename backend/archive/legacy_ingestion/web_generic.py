"""
Generic Web Crawler - Simple scraper for any website
Less structured than documentation crawler, works with any website.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Any, Optional
import time
import logging

from ..base import DocumentCrawler

logger = logging.getLogger(__name__)


class GenericWebCrawler(DocumentCrawler):
    """
    Simple generic web crawler for any website.
    More permissive than WebDocumentationCrawler.
    """
    
    def __init__(self, kb_id: str, config: Dict[str, Any]):
        """
        Initialize crawler.
        
        Args:
            kb_id: Knowledge base ID
            config: Configuration with:
                - urls: List of URLs to crawl (no automatic discovery)
                OR
                - start_url: Single URL to start from
                - follow_links: Whether to follow links (default: False)
                - max_pages: Max pages if following links (default: 100)
                - delay: Delay between requests (default: 1.0)
        """
        super().__init__(kb_id, config)
        
        # Single URL mode or list mode
        self.urls_to_crawl = config.get('urls', [])
        if not self.urls_to_crawl and 'start_url' in config:
            self.urls_to_crawl = [config['start_url']]
        
        self.follow_links = config.get('follow_links', False)
        self.max_pages = config.get('max_pages', 100)
        self.delay = config.get('delay', 1.0)
        
        self.logger.info("=" * 80)
        self.logger.info(f"GenericWebCrawler initialized for KB: {kb_id}")
        self.logger.info(f"  URLs to crawl: {len(self.urls_to_crawl)}")
        for url in self.urls_to_crawl:
            self.logger.info(f"    - {url}")
        self.logger.info(f"  Follow links: {self.follow_links}")
        self.logger.info(f"  Max pages: {self.max_pages}")
        self.logger.info(f"  Delay: {self.delay}s")
        self.logger.info("=" * 80)
    
    def fetch_content(self, url: str) -> str:
        """Fetch HTML content from URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return ""
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL should be crawled (exclude images, videos, etc.)."""
        # Skip common media file extensions
        skip_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico',  # Images
            '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',  # Videos
            '.mp3', '.wav', '.ogg', '.flac',  # Audio
            '.zip', '.tar', '.gz', '.rar',  # Archives
            '.exe', '.dmg', '.pkg', '.deb'  # Executables
        ]
        url_lower = url.lower()
        return not any(url_lower.endswith(ext) for ext in skip_extensions)
    
    def extract_links(self, html: str, current_url: str) -> List[str]:
        """Extract all links from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        parsed_current = urlparse(current_url)
        current_domain = parsed_current.netloc
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(current_url, href)
            parsed = urlparse(absolute_url)
            
            # Same domain only
            if parsed.netloc == current_domain:
                # Remove fragment
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if parsed.query:
                    clean_url += f"?{parsed.query}"
                
                # Skip invalid URLs (images, etc.)
                if self.is_valid_url(clean_url):
                    links.append(clean_url)
        
        return links
    
    def crawl(self, progress_callback: Optional[callable] = None) -> List[str]:
        """
        Crawl configured URLs.
        
        Args:
            progress_callback: Optional callback(current, total, message)
            
        Returns:
            List of URLs
        """
        self.logger.info("Starting crawl...")
        self.logger.info(f"Initial URLs: {self.urls_to_crawl}")
        
        visited = set()
        urls_to_process = list(self.urls_to_crawl)
        discovered_urls = []
        
        while urls_to_process and len(visited) < self.max_pages:
            url = urls_to_process.pop(0)
            
            if url in visited:
                continue
            
            self.logger.info(f"Crawling [{len(visited)+1}]: {url}")
            visited.add(url)
            discovered_urls.append(url)
            
            # Fetch content
            html = self.fetch_content(url)
            if not html:
                self.logger.warning(f"  ⚠ No content fetched from {url}")
                continue
            
            self.logger.info(f"  ✓ Fetched {len(html)} bytes")
            
            # Progress callback
            if progress_callback:
                # Crawler callback has different signature - just pass counts and message
                # Don't pass phase enum here as crawler doesn't know about ingestion phases
                pass
            
            # Follow links if enabled
            if self.follow_links and len(visited) < self.max_pages:
                new_links = self.extract_links(html, url)
                self.logger.info(f"  Found {len(new_links)} links")
                for link in new_links:
                    if link not in visited and link not in urls_to_process:
                        urls_to_process.append(link)
                        self.logger.info(f"    + Added to queue: {link}")
            
            # Rate limiting
            if self.delay > 0:
                self.logger.info(f"  Waiting {self.delay}s...")
                time.sleep(self.delay)
        
        self.logger.info(f"✓ Crawl complete: {len(discovered_urls)} URLs discovered")
        
        return discovered_urls
