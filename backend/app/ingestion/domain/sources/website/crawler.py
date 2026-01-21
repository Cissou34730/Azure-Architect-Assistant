import logging
import re
import time
from collections.abc import Generator
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup
from llama_index.core import Document

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT = 15
MAX_RETRIES = 3
DEFAULT_MAX_PAGES = 1000
DEFAULT_BATCH_SIZE = 10
RATE_LIMIT_DELAY = 0.5
RETRY_DELAY = 2.0
MAX_ERRORS_COUNT = 5
MAX_REJECTED_COUNT = 10
LOG_INTERVAL = 20
HTTP_BAD_REQUEST = 400
HTTP_INTERNAL_ERROR = 500

EXCLUDED_EXTENSIONS = (
    '.pdf',
    '.zip',
    '.png',
    '.jpg',
    '.gif',
    '.svg',
    '.mp4',
    '.exe',
)


class WebsiteCrawler:
    """
    Orchestrates website crawling with link discovery and support for batching.
    """

    def __init__(self, kb_id: str, job: Any | None = None, state: Any | None = None) -> None:
        self.kb_id = kb_id
        self.job = job
        self.state = state
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.timeout = DEFAULT_TIMEOUT
        self.max_retries = MAX_RETRIES
        self.base_domain = ''
        self.semantic_path = ''
        self._invalid_url_count = 0
        self._rejected_count = 0

    def _queue_new_links(
        self, links: list[str], visited: set[str], to_visit: list[str]
    ) -> None:
        """Add new, non-visited, non-queued links to the visit queue."""
        for link in links:
            if link not in visited and link not in to_visit:
                to_visit.append(link)

    def crawl(
        self,
        start_url: str,
        url_prefix: str | None = None,
        max_pages: int = DEFAULT_MAX_PAGES,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> Generator[list[Document], None, None]:
        """Crawl a website yields batches of documents."""
        if not url_prefix:
            url_prefix = start_url.rstrip("/")

        self.semantic_path = self._extract_semantic_path(url_prefix)
        self.base_domain = urlparse(url_prefix).netloc

        visited: set[str] = set()
        to_visit: list[str] = [self._normalize_url(start_url)]
        current_batch: list[Document] = []
        last_id = 0
        failed_count = 0

        logger.info(f"Crawler start: {start_url} (limit={max_pages})")

        while to_visit and len(visited) < max_pages:
            url = self._get_next_valid_url(to_visit, visited)
            if not url:
                break

            last_id += 1
            visited.add(url)

            doc, final_url, links = self._fetch_and_process_url(url, last_id)
            if not doc and not links:
                failed_count += 1
                time.sleep(RATE_LIMIT_DELAY)
                continue

            self._handle_redirect(url, final_url, visited)

            if doc:
                current_batch.append(doc)
                if len(current_batch) >= batch_size:
                    yield current_batch
                    current_batch = []

            self._queue_new_links(links, visited, to_visit)
            self._log_progress(len(visited), len(to_visit))
            time.sleep(RATE_LIMIT_DELAY)

        if current_batch:
            yield current_batch

        self._log_summary(visited, to_visit, max_pages, failed_count)

    def _fetch_and_process_url(self, url: str, last_id: int) -> tuple[Document | None, str | None, list[str]]:
        """Fetch HTML, extract document and links in one step."""
        content, final_url = self._fetch_html_with_redirect(url)
        if not content:
            return None, None, []

        actual_url = final_url or url
        doc = self._extract_document(content, actual_url, last_id)
        links = self._extract_links(content, actual_url)
        return doc, final_url, links

    def _handle_redirect(self, url: str, final_url: str | None, visited: set[str]) -> None:
        """Add normalized final URL to visited if it differs from the original."""
        if final_url and final_url != url:
            visited.add(self._normalize_url(final_url))

    def _log_progress(self, visited_count: int, queue_count: int) -> None:
        """Log crawl progress periodically."""
        if visited_count <= MAX_ERRORS_COUNT or visited_count % LOG_INTERVAL == 0:
            logger.info(f"  → Progress: {visited_count} visited, {queue_count} queue")

    def _get_next_valid_url(self, to_visit: list[str], visited: set[str]) -> str | None:
        """Get the next URL from the queue that hasn't been visited and is valid."""
        while to_visit:
            url = to_visit.pop(0)
            if url in visited or not self._is_valid_url(url):
                self._log_skipped_url(url, url in visited)
                continue
            return url
        return None

    def _log_skipped_url(self, url: str, already_visited: bool) -> None:
        """Log skipped URL if it's the first few times."""
        if already_visited:
            return
        self._invalid_url_count += 1
        if self._invalid_url_count <= MAX_ERRORS_COUNT:
            logger.info(f'Skipping invalid URL: {url}')

    def _log_summary(
        self, visited: set[str], to_visit: list[str], max_pages: int, failed: int
    ) -> None:
        """Log crawl completion summary."""
        logger.info('=' * 70)
        logger.info('CRAWLER STOPPED')
        logger.info(f'  Visited: {len(visited)} pages')
        logger.info(f'  Queue empty: {not to_visit}')
        logger.info(f'  Hit limit: {len(visited) >= max_pages}')
        logger.info(f'  Failed: {failed} pages')
        logger.info('=' * 70)

    def _extract_document(self, html: str, url: str, doc_id: int) -> Document | None:
        """Extract clean text content and wrap in Document."""
        content = trafilatura.extract(html, include_comments=False, include_tables=True)
        if not content:
            logger.warning(f'  ✗ Failed to extract content from {url}')
            return None

        return Document(
            text=content,
            metadata={
                'doc_id': doc_id,
                'source_type': 'website',
                'url': url,
                'kb_id': self.kb_id,
                'date_ingested': datetime.now().isoformat(),
            },
        )

    def _extract_semantic_path(self, url: str) -> str:
        """Extract semantic path from URL, removing language codes."""
        parsed = urlparse(url)
        path = parsed.path
        # Remove language codes (e.g., /en-us/, /fr-fr/)
        path = re.sub(r'^/[a-z]{2}-[a-z]{2}/', '/', path)
        return path.rstrip('/')

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL matches the semantic path and is not a media file."""
        parsed = urlparse(url)

        if parsed.netloc != self.base_domain:
            return False

        url_semantic_path = self._extract_semantic_path(url)
        if not url_semantic_path.startswith(self.semantic_path):
            self._rejected_count += 1
            if self._rejected_count <= MAX_REJECTED_COUNT:
                logger.debug(f'Rejected path mismatch: {url}')
            return False

        return not url.lower().endswith(EXCLUDED_EXTENSIONS)

    def _fetch_html_with_redirect(self, url: str) -> tuple[str | None, str | None]:
        """Fetch HTML content with retries and redirect following."""
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url,
                    timeout=self.timeout,
                    headers=self.headers,
                    allow_redirects=True,
                )
                response.raise_for_status()
                final_url = response.url if response.history else url
                return response.text, final_url

            except requests.exceptions.HTTPError as e:
                # Don't retry on 4xx errors
                status = e.response.status_code
                if HTTP_BAD_REQUEST <= status < HTTP_INTERNAL_ERROR:
                    logger.warning(f'  ✗ Client error {status}: {url}')
                    return None, None
                self._handle_retry(attempt, str(e))
            except requests.exceptions.RequestException as e:
                self._handle_retry(attempt, str(e))

        return None, None

    def _handle_retry(self, attempt: int, error: str) -> None:
        """Log retry attempt if possible."""
        if attempt < self.max_retries - 1:
            logger.warning(f'  Retry delayed ({attempt + 1}/{self.max_retries}): {error}')
            time.sleep(RETRY_DELAY)
        else:
            logger.error(f'  Failed after {self.max_retries} attempts')

    def _extract_links(self, html: str, current_url: str) -> list[str]:
        """Extract all valid links from HTML content."""
        try:
            soup = BeautifulSoup(html, 'lxml')
            links = []
            for anchor in soup.find_all('a', href=True):
                href = anchor['href']
                if href.startswith(('#', 'javascript:', 'mailto:')):
                    continue
                absolute_url = urljoin(current_url, href)
                normalized_url = self._normalize_url(absolute_url)
                if normalized_url and self._is_valid_url(normalized_url):
                    links.append(normalized_url)
            return list(set(links))
        except (ValueError, RuntimeError) as e:
            logger.error(f'  Error extracting links: {e}')
            return []

    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and trailing slashes."""
        try:
            url = url.split('#')[0].rstrip('/')
            return url if url.startswith(('http://', 'https://')) else ''
        except (ValueError, AttributeError):
            return ''
