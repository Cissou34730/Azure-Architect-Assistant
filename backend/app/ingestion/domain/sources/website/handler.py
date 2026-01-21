import logging
from collections.abc import Generator
from datetime import datetime
from typing import Any, ClassVar
from urllib.parse import urlparse

from llama_index.core import Document
from trafilatura.sitemaps import sitemap_search

from ..handler_base import BaseSourceHandler
from .content_fetcher import ContentFetcher
from .crawler import WebsiteCrawler
from .sitemap_parser import SitemapParser

logger = logging.getLogger(__name__)


class WebsiteSourceHandler(BaseSourceHandler):
    """
    Handle website ingestion with multiple modes:
    1. Explicit sitemap_url → Parse sitemap
    2. start_url → Try sitemap discovery → Fallback to crawling
    3. Direct urls → Ingest specific URLs
    """

    # Domains with massive sitemaps - skip auto-discovery
    PROBLEMATIC_DOMAINS: ClassVar[list[str]] = [
        'learn.microsoft.com',
        'docs.microsoft.com',
        'developer.mozilla.org',
        'docs.aws.amazon.com',
    ]

    def __init__(self, kb_id: str, job: Any | None = None, state: Any | None = None) -> None:
        super().__init__(kb_id, job=job, state=state)
        self.crawler = WebsiteCrawler(kb_id, job=job, state=state)
        self.content_fetcher = ContentFetcher()
        self.sitemap_parser = SitemapParser()
        logger.info(f'WebsiteSourceHandler ready KB={kb_id}')

    def ingest(
        self, config: dict[str, Any]
    ) -> list[Document] | Generator[list[Document], None, None]:
        """
        Ingest websites based on config.
        """
        logger.info('Website ingestion start')

        url_prefix = config.get('url_prefix')
        max_pages = config.get('max_pages', 1000)

        # Mode 1: Explicit sitemap
        if 'sitemap_url' in config:
            return self._ingest_from_sitemap(config['sitemap_url'], url_prefix)

        # Mode 2: start_url (try sitemap → fallback to crawl)
        if 'start_url' in config:
            start_url = config['start_url']
            domain = urlparse(start_url).netloc.lower()

            if any(prob in domain for prob in self.PROBLEMATIC_DOMAINS):
                return self.crawler.crawl(start_url, url_prefix, max_pages)

            try:
                sitemap_urls = sitemap_search(start_url, target_lang=None)
                if sitemap_urls:
                    return self._ingest_urls(list(sitemap_urls), url_prefix)
            except (ValueError, RuntimeError) as e:
                logger.warning(f'Sitemap discovery failed: {e}')

            return self.crawler.crawl(start_url, url_prefix, max_pages, batch_size=10)

        # Mode 3: Direct URLs
        if 'urls' in config:
            return self._ingest_urls(config['urls'], url_prefix)

        raise ValueError("Config must have 'sitemap_url', 'start_url', or 'urls'")

    def _ingest_from_sitemap(
        self, sitemap_url: str, url_prefix: str | None = None
    ) -> list[Document]:
        """Parse sitemap and ingest URLs."""
        urls = self.sitemap_parser.parse_sitemap(sitemap_url)
        urls = list(set(urls))
        return self._ingest_urls(urls, url_prefix)

    def _ingest_urls(self, urls: list[str], url_prefix: str | None = None) -> list[Document]:
        """Ingest specific list of URLs."""
        if url_prefix:
            urls = [url for url in urls if url.startswith(url_prefix)]

        documents = []
        for url in urls:
            content = self.content_fetcher.fetch_content(url)
            if content:
                doc = Document(
                    text=content,
                    metadata={
                        'source_type': 'website',
                        'url': url,
                        'kb_id': self.kb_id,
                        'date_ingested': datetime.now().isoformat(),
                    },
                )
                documents.append(doc)
            else:
                logger.warning(f'  ✗ Failed to fetch content from {url}')

        logger.info(f'Website ingestion complete: {len(documents)}/{len(urls)} successful')
        return documents
