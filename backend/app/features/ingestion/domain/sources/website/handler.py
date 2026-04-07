import logging
from collections.abc import Generator
from datetime import datetime
from typing import Any, ClassVar
from urllib.parse import urlparse

from llama_index.core import Document

from ..handler_base import BaseSourceHandler
from .content_fetcher import ContentFetcher
from .crawler import WebsiteCrawler

logger = logging.getLogger(__name__)


class WebsiteSourceHandler(BaseSourceHandler):
    """
    Handle website ingestion with multiple modes:
    1. start_url → Crawl (optionally filtered by url_prefix)
    2. Direct urls → Ingest specific URLs
    """

    PROBLEMATIC_DOMAINS: ClassVar[list[str]] = []

    def __init__(self, kb_id: str, job: Any | None = None, state: Any | None = None) -> None:
        super().__init__(kb_id, job=job, state=state)
        self.crawler = WebsiteCrawler(kb_id, job=job, state=state)
        self.content_fetcher = ContentFetcher()
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

        # Mode 1: start_url → crawl
        if 'start_url' in config:
            start_url = config['start_url']
            _ = urlparse(start_url).netloc.lower()
            return self.crawler.crawl(start_url, url_prefix, max_pages, batch_size=10)

        # Mode 2: Direct URLs
        if 'urls' in config:
            return self._ingest_urls(config['urls'], url_prefix)

        raise ValueError("Config must have 'start_url' or 'urls'")

    def _ingest_urls(self, urls: list[str], url_prefix: str | None = None) -> list[Document]:
        """Ingest specific list of URLs."""
        if url_prefix:
            normalized_prefix = url_prefix.rstrip('/')
            urls = [url for url in urls if url.rstrip('/').startswith(normalized_prefix)]

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
