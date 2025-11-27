"""
Website Source Handler
Handles website ingestion using Trafilatura.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from llama_index.core import Document
from llama_index.readers.web import TrafilaturaWebReader

from .base import BaseSourceHandler

logger = logging.getLogger(__name__)


class WebsiteSourceHandler(BaseSourceHandler):
    """
    Handle website ingestion using TrafilaturaWebReader.
    Replaces BeautifulSoup + html2text + Readability.
    """
    
    def __init__(self, kb_id: str):
        super().__init__(kb_id)
        self.reader = TrafilaturaWebReader()
        logger.info(f"WebsiteSourceHandler initialized for KB: {kb_id}")
    
    def ingest(self, config: Dict[str, Any]) -> List[Document]:
        """
        Ingest websites from config.
        
        Args:
            config: Must contain 'urls' list or 'sitemap_url'
            
        Returns:
            List of Documents
        """
        if 'sitemap_url' in config:
            return self.ingest_sitemap(config['sitemap_url'])
        elif 'urls' in config:
            return self.ingest_urls(config['urls'])
        else:
            raise ValueError("Website config requires 'urls' or 'sitemap_url'")
    
    def ingest_urls(self, urls: List[str]) -> List[Document]:
        """
        Ingest documents from URLs using Trafilatura.
        
        Args:
            urls: List of URLs to crawl
            
        Returns:
            List of LlamaIndex Documents
        """
        documents = []
        
        for url in urls:
            try:
                logger.info(f"Fetching URL: {url}")
                docs = self.reader.load_data(urls=[url])
                
                # Enrich metadata
                for doc in docs:
                    doc.metadata.update({
                        'source_type': 'website',
                        'url': url,
                        'kb_id': self.kb_id,
                        'date_ingested': datetime.now().isoformat()
                    })
                
                documents.extend(docs)
                logger.info(f"Successfully ingested {len(docs)} documents from {url}")
                
            except Exception as e:
                logger.error(f"Failed to ingest {url}: {e}")
        
        return documents
    
    def ingest_sitemap(self, sitemap_url: str) -> List[Document]:
        """
        Parse sitemap and ingest all URLs.
        
        Args:
            sitemap_url: URL to sitemap.xml
            
        Returns:
            List of LlamaIndex Documents
        """
        urls = self._parse_sitemap(sitemap_url)
        logger.info(f"Found {len(urls)} URLs in sitemap: {sitemap_url}")
        return self.ingest_urls(urls)
    
    def _parse_sitemap(self, sitemap_url: str) -> List[str]:
        """Extract URLs from sitemap.xml"""
        import requests
        import xml.etree.ElementTree as ET
        
        try:
            response = requests.get(sitemap_url, timeout=30)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            urls = []
            
            # Check for sitemap index
            if root.tag.endswith('sitemapindex'):
                for sitemap_elem in root.findall('.//ns:loc', namespace):
                    urls.extend(self._parse_sitemap(sitemap_elem.text))
            else:
                # Regular sitemap
                for url_elem in root.findall('.//ns:loc', namespace):
                    urls.append(url_elem.text)
            
            return urls
            
        except Exception as e:
            logger.error(f"Failed to parse sitemap {sitemap_url}: {e}")
            return []
