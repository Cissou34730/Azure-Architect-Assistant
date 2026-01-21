import logging

import requests
from defusedxml import ElementTree

logger = logging.getLogger(__name__)


class SitemapParser:
    """
    Responsible for parsing sitemap.xml files.
    """

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def parse_sitemap(self, sitemap_url: str) -> list[str]:
        """
        Extract URLs from sitemap.xml (handles sitemap indices recursively).

        Args:
            sitemap_url: URL to sitemap.xml

        Returns:
            List of URLs found in sitemap
        """
        try:
            logger.debug(f'Parsing sitemap: {sitemap_url}')

            response = requests.get(sitemap_url, timeout=self.timeout)
            response.raise_for_status()
            root = ElementTree.fromstring(response.content)

            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            urls = []

            # Check if this is a sitemap index
            if root.tag.endswith('sitemapindex'):
                logger.debug(f'Found sitemap index at {sitemap_url}')
                for sitemap_elem in root.findall('.//ns:loc', namespace):
                    if sitemap_elem is not None and sitemap_elem.text:
                        # Recursively parse sub-sitemaps
                        urls.extend(self.parse_sitemap(sitemap_elem.text))
            else:
                # Regular sitemap - extract URLs
                for url_elem in root.findall('.//ns:loc', namespace):
                    if url_elem is not None and url_elem.text:
                        urls.append(url_elem.text)

            logger.debug(f'Found {len(urls)} URLs in {sitemap_url}')
            return urls
        except (requests.RequestException, ElementTree.ParseError) as e:
            logger.error(f'  Error parsing sitemap {sitemap_url}: {e}')
            return []
