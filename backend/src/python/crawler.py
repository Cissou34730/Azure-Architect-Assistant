"""
WAF Documentation Crawler
Implements BFS crawling with deduplication, domain restriction, and depth control.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque
from typing import Set, List, Dict, Any
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WAFCrawler:
    """Crawler for Azure Well-Architected Framework documentation."""
    
    def __init__(
        self,
        start_url: str = "https://learn.microsoft.com/azure/well-architected/",
        max_depth: int = 3,
        max_pages: int = 500,
        delay: float = 0.5
    ):
        """
        Initialize the crawler.
        
        Args:
            start_url: Starting URL for crawling
            max_depth: Maximum depth for BFS traversal
            max_pages: Maximum number of pages to crawl
            delay: Delay between requests (seconds)
        """
        self.start_url = start_url
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.delay = delay
        
        # Parse the base domain
        parsed = urlparse(start_url)
        self.base_domain = f"{parsed.scheme}://{parsed.netloc}"
        self.allowed_path = "/azure/well-architected/"
        
        # Tracking
        self.visited: Set[str] = set()
        self.urls: List[Dict[str, Any]] = []
        
    def is_valid_url(self, url: str) -> bool:
        """
        Check if URL is valid for crawling.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid, False otherwise
        """
        parsed = urlparse(url)
        
        # Check domain
        if not parsed.netloc.endswith("learn.microsoft.com"):
            return False
            
        # Check path
        if not parsed.path.startswith(self.allowed_path):
            return False
            
        # Exclude media, downloads, etc.
        excluded_extensions = ('.pdf', '.zip', '.png', '.jpg', '.gif', '.svg')
        if parsed.path.lower().endswith(excluded_extensions):
            return False
            
        return True
    
    def normalize_url(self, url: str) -> str:
        """
        Normalize URL by removing fragments and query parameters.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL
        """
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    def extract_links(self, html: str, current_url: str) -> List[str]:
        """
        Extract all valid links from HTML content.
        
        Args:
            html: HTML content
            current_url: Current page URL (for resolving relative URLs)
            
        Returns:
            List of absolute URLs
        """
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(current_url, href)
            normalized = self.normalize_url(absolute_url)
            
            if self.is_valid_url(normalized):
                links.append(normalized)
                
        return links
    
    def fetch_page(self, url: str) -> str:
        """
        Fetch HTML content from URL.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content or empty string on error
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return ""
    
    def crawl(self) -> List[Dict[str, Any]]:
        """
        Perform BFS crawl starting from start_url.
        
        Returns:
            List of discovered URLs with metadata
        """
        # Initialize queue with (url, depth)
        queue = deque([(self.start_url, 0)])
        self.visited.add(self.start_url)
        
        logger.info(f"Starting crawl from {self.start_url}")
        logger.info(f"Max depth: {self.max_depth}, Max pages: {self.max_pages}")
        
        while queue and len(self.urls) < self.max_pages:
            url, depth = queue.popleft()
            
            logger.info(f"Crawling [{len(self.urls)+1}/{self.max_pages}] depth={depth}: {url}")
            
            # Fetch page
            html = self.fetch_page(url)
            if not html:
                continue
            
            # Store URL info
            self.urls.append({
                'url': url,
                'depth': depth,
                'status': 'discovered'
            })
            
            # Extract links if not at max depth
            if depth < self.max_depth:
                links = self.extract_links(html, url)
                
                for link in links:
                    if link not in self.visited and len(self.visited) < self.max_pages:
                        self.visited.add(link)
                        queue.append((link, depth + 1))
            
            # Be nice to the server
            time.sleep(self.delay)
        
        logger.info(f"Crawl complete. Discovered {len(self.urls)} URLs")
        return self.urls
    
    def save_urls(self, output_file: str = "waf_urls.txt"):
        """
        Save discovered URLs to a file.
        
        Args:
            output_file: Output file path
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in self.urls:
                f.write(f"{item['url']}\n")
        logger.info(f"Saved {len(self.urls)} URLs to {output_file}")


def main():
    """Main entry point for crawler."""
    crawler = WAFCrawler(
        start_url="https://learn.microsoft.com/azure/well-architected/",
        max_depth=3,
        max_pages=500,
        delay=0.5
    )
    
    urls = crawler.crawl()
    crawler.save_urls("waf_urls.txt")
    
    print(f"\nCrawl Summary:")
    print(f"Total URLs discovered: {len(urls)}")
    print(f"URLs saved to: waf_urls.txt")


if __name__ == "__main__":
    main()
