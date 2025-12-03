"""
Link Extractor - Extract and normalize links from web pages
"""

import logging
import requests
import time
from typing import List
from urllib.parse import urljoin
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class LinkExtractor:
    """
    Responsible for extracting links from web pages using BeautifulSoup.
    """
    
    def __init__(self, max_retries: int = 3, timeout: int = 15):
        self.max_retries = max_retries
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def extract_links(self, url: str, url_prefix: str) -> List[str]:
        """
        Extract all links from a page that match the URL prefix.
        
        Args:
            url: URL to extract links from
            url_prefix: Only return links starting with this prefix
            
        Returns:
            List of absolute, normalized URLs
        """
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Extracting links from {url} (attempt {attempt + 1}/{self.max_retries})")
                
                response = requests.get(url, timeout=self.timeout, headers=self.headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'lxml')
                links = []
                
                # Debug: count all anchors
                all_anchors = soup.find_all('a', href=True)
                
                # Debug counters
                skipped_fragment = 0
                skipped_js_mailto = 0
                skipped_prefix = 0
                
                for anchor in all_anchors:
                    href = anchor['href']
                    
                    # Skip non-http links
                    if href.startswith('#'):
                        skipped_fragment += 1
                        continue
                    if href.startswith(('javascript:', 'mailto:')):
                        skipped_js_mailto += 1
                        continue
                    
                    # Convert to absolute URL
                    absolute_url = urljoin(url, href)
                    
                    # Normalize
                    normalized_url = self._normalize_url(absolute_url)
                    
                    # Filter by prefix
                    if normalized_url and normalized_url.startswith(url_prefix):
                        links.append(normalized_url)
                    else:
                        skipped_prefix += 1
                        # Show first few filtered links for debugging
                        if skipped_prefix <= 3:
                            # Filtered prefix detail suppressed
                            pass
                
                # Debug: show why links were filtered
                # Skip counters suppressed
                
                # Deduplicate
                unique_links = list(set(links))
                logger.info(f"Matched links: {len(unique_links)} unique")
                
                # Show sample of matched links
                # Sample matched links suppressed
                
                logger.debug(f"Extracted {len(unique_links)} unique links from {url} (before dedup: {len(links)})")
                
                return unique_links
                
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Failed to extract links: {e}, retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    logger.error(f"Failed to extract links after {self.max_retries} attempts: {e}")
                    return []
            except Exception as e:
                logger.error(f"Unexpected error extracting links: {e}")
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
