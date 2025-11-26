"""
Generic Web Content Cleaner
Cleans and structures HTML content from any website using Readability and BeautifulSoup.
"""

import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
import html2text
import logging

try:
    from readability.readability import Document as ReadabilityDocument
    READABILITY_AVAILABLE = True
except ImportError:
    READABILITY_AVAILABLE = False
    logging.warning("readability-lxml not available, using basic cleaning")

from ..base import DocumentCleaner

logger = logging.getLogger(__name__)


class WebContentCleaner(DocumentCleaner):
    """
    Generic cleaner for web content.
    Works with any HTML using Readability for main content extraction.
    """
    
    def __init__(self, kb_id: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize cleaner.
        
        Args:
            kb_id: Knowledge base ID
            config: Optional configuration with:
                - remove_elements: List of HTML tags to remove (default: script, style, nav, footer, header, aside)
                - min_content_length: Minimum content length in chars (default: 100)
                - extract_metadata: Whether to extract metadata (default: True)
        """
        super().__init__(kb_id, config)
        
        self.remove_elements = self.config.get('remove_elements', [
            'script', 'style', 'nav', 'footer', 'header', 'aside', 'form'
        ])
        self.min_content_length = self.config.get('min_content_length', 100)
        self.extract_metadata_flag = self.config.get('extract_metadata', True)
        
        # Initialize HTML to text converter
        self.html_to_text = html2text.HTML2Text()
        self.html_to_text.ignore_links = False
        self.html_to_text.ignore_images = True
        self.html_to_text.ignore_emphasis = False
        self.html_to_text.body_width = 0  # No wrapping
    
    def extract_main_content(self, html: str) -> str:
        """Extract main content using Readability if available."""
        if READABILITY_AVAILABLE:
            try:
                doc = ReadabilityDocument(html)
                return doc.summary()
            except Exception as e:
                self.logger.warning(f"Readability extraction failed: {e}, using fallback")
        
        # Fallback: use full HTML
        return html
    
    def clean_html(self, html: str) -> str:
        """Clean HTML by removing unwanted elements."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted elements
        for element_name in self.remove_elements:
            for element in soup.find_all(element_name):
                element.decompose()
        
        # Remove elements with navigation/menu classes
        for element in soup.find_all(class_=re.compile(r'(nav|menu|sidebar|footer|header|breadcrumb|banner)', re.I)):
            element.decompose()
        
        return str(soup)
    
    def html_to_markdown(self, html: str) -> str:
        """Convert HTML to markdown/text."""
        return self.html_to_text.handle(html)
    
    def normalize_text(self, text: str) -> str:
        """Normalize text by removing noise and standardizing format."""
        # Remove common noise patterns
        noise_patterns = [
            r'(?i)^.*?(next steps?|see also|related articles?|table of contents|feedback).*?$',
            r'(?i)^.*?(skip to main content|accept cookies|privacy policy).*?$',
        ]
        
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.MULTILINE)
        
        # Normalize whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Max 2 newlines
        text = re.sub(r' +', ' ', text)  # Multiple spaces to single
        text = re.sub(r'\t+', ' ', text)  # Tabs to space
        
        # Remove markdown artifacts
        text = re.sub(r'^[-_*]{3,}$', '', text, flags=re.MULTILINE)
        
        return text.strip()
    
    def extract_metadata(self, raw_content: str, url: str) -> Dict[str, Any]:
        """Extract metadata from HTML."""
        metadata = {'url': url}
        
        if not self.extract_metadata_flag:
            return metadata
        
        try:
            soup = BeautifulSoup(raw_content, 'html.parser')
            
            # Extract title
            title_tag = soup.find('title')
            if title_tag:
                metadata['title'] = title_tag.get_text().strip()
            else:
                metadata['title'] = url.split('/')[-1] or 'Untitled'
            
            # Extract meta description
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if desc_tag and desc_tag.get('content'):
                metadata['description'] = desc_tag['content'].strip()
            
            # Extract h1 (often the main heading)
            h1_tag = soup.find('h1')
            if h1_tag:
                metadata['section'] = h1_tag.get_text().strip()
            else:
                metadata['section'] = metadata.get('title', 'Main Content')
        
        except Exception as e:
            self.logger.warning(f"Metadata extraction failed for {url}: {e}")
        
        return metadata
    
    def clean(
        self,
        raw_content: str,
        metadata: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Clean and structure web content.
        
        Args:
            raw_content: Raw HTML content
            metadata: Document metadata (must include 'url')
            progress_callback: Optional progress callback
            
        Returns:
            Cleaned document dictionary
        """
        url = metadata.get('url', 'unknown')
        
        try:
            # Extract main content
            main_content_html = self.extract_main_content(raw_content)
            
            # Clean HTML
            cleaned_html = self.clean_html(main_content_html)
            
            # Convert to text/markdown
            text_content = self.html_to_markdown(cleaned_html)
            
            # Normalize
            normalized_content = self.normalize_text(text_content)
            
            # Check minimum length
            if len(normalized_content) < self.min_content_length:
                self.logger.warning(f"Content too short for {url}: {len(normalized_content)} chars")
                return {
                    'content': normalized_content,
                    'metadata': metadata,
                    'status': 'failed',
                    'error': f'Content too short: {len(normalized_content)} chars'
                }
            
            # Extract and merge metadata
            extracted_metadata = self.extract_metadata(raw_content, url)
            final_metadata = {**metadata, **extracted_metadata}
            
            return {
                'content': normalized_content,
                'metadata': final_metadata,
                'status': 'success'
            }
        
        except Exception as e:
            self.logger.error(f"Failed to clean {url}: {e}", exc_info=True)
            return {
                'content': '',
                'metadata': metadata,
                'status': 'failed',
                'error': str(e)
            }
