"""
WAF Documentation Ingestion Pipeline
Handles HTML extraction, cleaning, normalization, and chunking.
"""

import os
import requests
from typing import List, Dict
from readability import Document
from bs4 import BeautifulSoup
import html2text
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WAFIngestionPipeline:
    """Pipeline for ingesting and processing WAF documentation."""
    
    def __init__(self):
        """Initialize the ingestion pipeline."""
        self.html_to_text = html2text.HTML2Text()
        self.html_to_text.ignore_links = False
        self.html_to_text.ignore_images = True
        self.html_to_text.ignore_emphasis = False
        self.html_to_text.body_width = 0  # No wrapping
        
    def fetch_html(self, url: str) -> str:
        """
        Fetch HTML content from URL.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content
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
    
    def extract_main_content(self, html: str) -> str:
        """
        Extract main article content using Readability.
        
        Args:
            html: Raw HTML content
            
        Returns:
            Cleaned HTML with main content only
        """
        try:
            doc = Document(html)
            return doc.summary()
        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            return html
    
    def clean_html(self, html: str) -> str:
        """
        Further clean HTML structure with BeautifulSoup.
        
        Args:
            html: HTML content
            
        Returns:
            Cleaned HTML
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted elements
        for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
        
        # Remove specific classes/IDs commonly used for navigation
        for element in soup.find_all(class_=re.compile(r'(nav|menu|sidebar|footer|header|breadcrumb)', re.I)):
            element.decompose()
            
        return str(soup)
    
    def html_to_markdown(self, html: str) -> str:
        """
        Convert HTML to markdown/text.
        
        Args:
            html: HTML content
            
        Returns:
            Text content
        """
        return self.html_to_text.handle(html)
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text by removing noise and standardizing format.
        
        Args:
            text: Raw text content
            
        Returns:
            Normalized text
        """
        # Remove common noise sections
        noise_patterns = [
            r'(?i)^.*?Next steps.*?$',
            r'(?i)^.*?Feedback.*?$',
            r'(?i)^.*?See also.*?$',
            r'(?i)^.*?Related articles.*?$',
            r'(?i)^.*?In this article.*?$',
            r'(?i)^.*?Table of contents.*?$',
        ]
        
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.MULTILINE)
        
        # Normalize whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Max 2 newlines
        text = re.sub(r' +', ' ', text)  # Multiple spaces to single
        text = re.sub(r'\t+', ' ', text)  # Tabs to space
        
        # Remove excessive dashes/underscores (markdown artifacts)
        text = re.sub(r'^[-_]{3,}$', '', text, flags=re.MULTILINE)
        
        return text.strip()
    
    def extract_metadata(self, url: str, html: str) -> Dict[str, str]:
        """
        Extract metadata from URL and HTML.
        
        Args:
            url: Page URL
            html: HTML content
            
        Returns:
            Metadata dictionary
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        title = "Unknown"
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
        elif soup.find('h1'):
            title = soup.find('h1').get_text().strip()
        
        # Determine section from URL
        section = "general"
        if "/pillars/" in url:
            section = "pillar"
        elif "/workloads/" in url:
            section = "workload"
        elif "/service-guides/" in url:
            section = "service-guide"
        
        return {
            'url': url,
            'title': title,
            'section': section
        }
    
    def process_url(self, url: str) -> Dict[str, any]:
        """
        Process a single URL through the full pipeline.
        
        Args:
            url: URL to process
            
        Returns:
            Processed document data
        """
        logger.info(f"Processing: {url}")
        
        # Fetch HTML
        html = self.fetch_html(url)
        if not html:
            return None
        
        # Extract metadata
        metadata = self.extract_metadata(url, html)
        
        # Extract main content
        main_content = self.extract_main_content(html)
        
        # Clean HTML
        cleaned_html = self.clean_html(main_content)
        
        # Convert to text
        text = self.html_to_markdown(cleaned_html)
        
        # Normalize text
        normalized_text = self.normalize_text(text)
        
        return {
            'url': url,
            'title': metadata['title'],
            'section': metadata['section'],
            'content': normalized_text,
            'char_count': len(normalized_text)
        }
    
    def process_urls_from_file(self, urls_file: str) -> List[Dict[str, any]]:
        """
        Process all URLs from a file.
        
        Args:
            urls_file: Path to file containing URLs (one per line)
            
        Returns:
            List of processed documents
        """
        documents = []
        
        # Read URLs
        with open(urls_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        logger.info(f"Processing {len(urls)} URLs...")
        
        # Process each URL
        for i, url in enumerate(urls, 1):
            logger.info(f"[{i}/{len(urls)}] Processing {url}")
            doc = self.process_url(url)
            if doc and doc['content']:
                documents.append(doc)
        
        logger.info(f"Successfully processed {len(documents)} documents")
        return documents
    
    def save_documents(self, documents: List[Dict[str, any]], output_file: str = "waf_documents.jsonl"):
        """
        Save processed documents to JSONL file.
        
        Args:
            documents: List of document dictionaries
            output_file: Output file path
        """
        import json
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for doc in documents:
                f.write(json.dumps(doc, ensure_ascii=False) + '\n')
        
        logger.info(f"Saved {len(documents)} documents to {output_file}")


def main():
    """Main entry point for ingestion pipeline."""
    pipeline = WAFIngestionPipeline()
    
    # Process URLs from crawler output
    urls_file = "waf_urls.txt"
    if not os.path.exists(urls_file):
        logger.error(f"URLs file not found: {urls_file}")
        logger.info("Please run crawler.py first to generate URLs")
        return
    
    # Process documents
    documents = pipeline.process_urls_from_file(urls_file)
    
    # Save results
    pipeline.save_documents(documents, "waf_documents.jsonl")
    
    print(f"\nIngestion Summary:")
    print(f"Total documents processed: {len(documents)}")
    print(f"Documents saved to: waf_documents.jsonl")


if __name__ == "__main__":
    main()
