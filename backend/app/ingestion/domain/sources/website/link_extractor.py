import logging
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT = 15
DEFAULT_MAX_RETRIES = 3
RETRY_DELAY = 2
DEBUG_MAX_LINKS = 3


class LinkExtractor:
    """
    Responsible for extracting links from web pages using BeautifulSoup.
    """

    def __init__(
        self, max_retries: int = DEFAULT_MAX_RETRIES, timeout: int = DEFAULT_TIMEOUT
    ) -> None:
        self.max_retries = max_retries
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def extract_links(self, url: str, url_prefix: str) -> list[str]:
        """
        Extract all links from a page that match the URL prefix.
        """
        for attempt in range(self.max_retries):
            try:
                content = self._fetch_page_content(url, attempt)
                if content is None:
                    continue

                links = self._parse_links(content, url, url_prefix)
                unique_links = list(set(links))
                logger.info(f'Extracted {len(unique_links)} unique links from {url}')
                return unique_links

            except requests.exceptions.RequestException as e:
                if not self._handle_retry(attempt, str(e)):
                    return []
            except (ValueError, RuntimeError) as e:
                logger.error(f'Error parsing links: {e}')
                return []

        return []

    def _fetch_page_content(self, url: str, attempt: int) -> bytes | None:
        """Fetch page content with logging."""
        logger.debug(f'Extracting links from {url} (attempt {attempt + 1}/{self.max_retries})')
        response = requests.get(url, timeout=self.timeout, headers=self.headers)
        response.raise_for_status()
        return response.content

    def _handle_retry(self, attempt: int, error: str) -> bool:
        """Log retry and return whether to continue."""
        if attempt < self.max_retries - 1:
            logger.warning(
                f'Failed to extract links: {error}, retrying in {RETRY_DELAY} seconds...'
            )
            time.sleep(RETRY_DELAY)
            return True
        logger.error(f'Failed to extract links after {self.max_retries} attempts: {error}')
        return False

    def _parse_links(self, content: bytes, base_url: str, url_prefix: str) -> list[str]:
        """Parse HTML content and extract matching links."""
        soup = BeautifulSoup(content, 'lxml')
        links = []
        skipped_prefix = 0

        for anchor in soup.find_all('a', href=True):
            href = anchor['href']

            # Skip common non-link patterns
            if href.startswith(('#', 'javascript:', 'mailto:')):
                continue

            absolute_url = urljoin(base_url, href)
            normalized_url = self._normalize_url(absolute_url)

            if normalized_url and normalized_url.startswith(url_prefix):
                links.append(normalized_url)
            else:
                skipped_prefix += 1
                if skipped_prefix <= DEBUG_MAX_LINKS:
                    logger.debug(f'Skipped URL (prefix mismatch): {normalized_url}')

        return links

    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and trailing slashes."""
        try:
            url = url.split('#')[0].rstrip('/')
            return url if url.startswith(('http://', 'https://')) else ''
        except (ValueError, AttributeError):
            return ''
