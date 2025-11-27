"""
Content Fetcher - Download and extract content from URLs
"""

import logging
import requests
import time
import trafilatura
from typing import Optional

logger = logging.getLogger(__name__)


class ContentFetcher:
    """
    Responsible for downloading web pages and extracting clean text content.
    """
    
    def __init__(self, max_retries: int = 3, timeout: int = 15):
        self.max_retries = max_retries
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def fetch_content(self, url: str) -> Optional[str]:
        """
        Download and extract clean text content from a URL.
        
        Args:
            url: URL to fetch
            
        Returns:
            Extracted text content or None if failed
        """
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Fetching content from {url} (attempt {attempt + 1}/{self.max_retries})")
                
                # Download page
                response = requests.get(url, timeout=self.timeout, headers=self.headers)
                response.raise_for_status()
                
                # Extract clean content with trafilatura
                text = trafilatura.extract(
                    response.content,
                    include_comments=False,
                    include_tables=True
                )
                
                if not text:
                    logger.warning(f"Failed to extract content from {url}")
                    return None
                
                logger.debug(f"Successfully extracted {len(text)} chars from {url}")
                return text
                
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Request failed: {e}, retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    logger.error(f"Failed to fetch {url} after {self.max_retries} attempts: {e}")
                    return None
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                return None
        
        return None
