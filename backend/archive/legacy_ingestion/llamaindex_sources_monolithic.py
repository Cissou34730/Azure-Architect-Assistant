"""
LlamaIndex-based Source Handlers
Unified implementation using free LlamaIndex readers for all source types.
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from enum import Enum

from llama_index.core import Document
from llama_index.readers.web import TrafilaturaWebReader
from llama_index.readers.file import SimpleDirectoryReader, PyMuPDFReader
from llama_index.readers.youtube_transcript import YoutubeTranscriptReader
from llama_index.llms.openai import OpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Structured Output Models for YouTube Distillation
# ============================================================================

class KeyConcept(BaseModel):
    """Extracted key concept from transcript"""
    name: str = Field(description="Name of the concept or technical term")
    definition: str = Field(description="Definition, rule, or constraint")


class TechnicalQA(BaseModel):
    """Question/Answer pair for better retrieval"""
    question: str = Field(description="Question an architect would ask")
    answer: str = Field(description="Precise technical answer")


class DistilledTranscript(BaseModel):
    """Complete distilled transcript output"""
    key_concepts: List[KeyConcept] = Field(default_factory=list, description="Key concepts and facts")
    technical_qa: List[TechnicalQA] = Field(default_factory=list, description="Technical Q&A pairs")
    summary: str = Field(description="One-paragraph summary of main topics")


# ============================================================================
# YouTube Distillation Prompt
# ============================================================================

YOUTUBE_DISTILLATION_PROMPT = """### ROLE
You are a Senior Technical Writer at Microsoft, specializing in Azure Architecture. 
Your mission is to convert raw spoken transcripts into dense, structured technical documentation for a Knowledge Base (RAG).

### INSTRUCTIONS
Analyze the provided transcript and extract two types of structured information:

1. **FACTS & RULES**: 
   - Indisputable technical statements
   - Limits (quotas, latencies, constraints)
   - Firm recommendations (Do/Don't patterns)
   - Key concept definitions
   - Best practices and patterns

2. **TECHNICAL Q&A**: 
   - Transform narrative explanations into clear Question/Answer pairs
   - The question must reflect what an architect would ask
   - The answer must be the specific technical solution from the text
   - Critical for retrieval: write questions an architect would naturally search for

### CLEANING RULES
- **IGNORE**: 
  - Oral fillers ("um", "so", "you see", "basically")
  - Jokes and personal anecdotes
  - Introductions and marketing fluff
  - Greetings ("Hello everyone", "Thanks for watching")
  
- **SYNTHESIZE**: 
  - If the speaker takes 5 sentences to say something, extract the essence
  - Example: "So like, what happens is, you know, the SLA is actually 99.9%" → "SLA = 99.9%"
  
- **CONTEXT**: 
  - Define acronyms at first mention (e.g., "App Service Environment (ASE)")
  - Use full technical names for Azure services
  
- **LANGUAGE**: 
  - Keep Azure technical terms in English
  - Write explanations in clear, professional language

### INPUT TRANSCRIPT
{transcript}

### OUTPUT
Extract the information and format according to the DistilledTranscript schema.
"""


# ============================================================================
# Website Source Handler (Trafilatura)
# ============================================================================

class WebsiteSourceHandler:
    """
    Handle website ingestion using TrafilaturaWebReader.
    Replaces BeautifulSoup + html2text + Readability.
    """
    
    def __init__(self, kb_id: str):
        self.kb_id = kb_id
        self.reader = TrafilaturaWebReader()
        logger.info(f"WebsiteSourceHandler initialized for KB: {kb_id}")
    
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


# ============================================================================
# YouTube Source Handler (with LLM Distillation)
# ============================================================================

class YouTubeSourceHandler:
    """
    Handle YouTube transcript ingestion with LLM-powered distillation.
    Converts raw transcripts into structured knowledge (concepts + Q&A).
    """
    
    def __init__(self, kb_id: str):
        self.kb_id = kb_id
        self.reader = YoutubeTranscriptReader()
        self.llm = OpenAI(model="gpt-4o-mini", temperature=0.1)
        logger.info(f"YouTubeSourceHandler initialized for KB: {kb_id}")
    
    def ingest_video(self, video_url: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Ingest YouTube video transcript with distillation.
        
        Args:
            video_url: YouTube video URL
            metadata: Optional metadata (title, channel, etc.)
            
        Returns:
            List of Documents (summary + concepts + Q&A pairs)
        """
        try:
            video_id = self._extract_video_id(video_url)
            logger.info(f"Ingesting YouTube video: {video_id}")
            
            # Load transcript
            transcript_docs = self.reader.load_data(ytlinks=[video_url])
            
            if not transcript_docs:
                logger.warning(f"No transcript found for {video_url}")
                return []
            
            transcript_text = transcript_docs[0].get_content()
            
            # Distill transcript using LLM
            distilled = self._distill_transcript(transcript_text)
            
            # Create documents for better retrieval
            documents = []
            base_metadata = {
                'source_type': 'youtube',
                'video_url': video_url,
                'video_id': video_id,
                'kb_id': self.kb_id,
                'date_ingested': datetime.now().isoformat(),
                **(metadata or {})
            }
            
            # 1. Summary document
            summary_doc = Document(
                text=f"# Video Summary\n\n{distilled.summary}",
                metadata={**base_metadata, 'content_type': 'summary'}
            )
            documents.append(summary_doc)
            
            # 2. Concept documents (one per concept)
            for concept in distilled.key_concepts:
                concept_doc = Document(
                    text=f"**{concept.name}**: {concept.definition}",
                    metadata={
                        **base_metadata,
                        'content_type': 'concept',
                        'concept_name': concept.name
                    }
                )
                documents.append(concept_doc)
            
            # 3. Q&A documents (one per Q&A pair)
            for qa in distilled.technical_qa:
                qa_doc = Document(
                    text=f"**Q: {qa.question}**\n\nA: {qa.answer}",
                    metadata={
                        **base_metadata,
                        'content_type': 'qa',
                        'question': qa.question
                    }
                )
                documents.append(qa_doc)
            
            logger.info(f"Distilled {video_id}: {len(distilled.key_concepts)} concepts, "
                       f"{len(distilled.technical_qa)} Q&A pairs")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to ingest YouTube video {video_url}: {e}", exc_info=True)
            return []
    
    def _distill_transcript(self, transcript: str) -> DistilledTranscript:
        """Use LLM to distill transcript into structured format"""
        
        prompt = YOUTUBE_DISTILLATION_PROMPT.format(transcript=transcript)
        
        try:
            response = self.llm.structured_predict(
                output_cls=DistilledTranscript,
                prompt=prompt
            )
            return response
            
        except Exception as e:
            logger.error(f"Distillation failed: {e}")
            # Return minimal structure
            return DistilledTranscript(
                key_concepts=[],
                technical_qa=[],
                summary="Failed to distill transcript"
            )
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^&]+)',
            r'(?:https?://)?(?:www\.)?youtu\.be/([^?]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([^?]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError(f"Could not extract video ID from {url}")
    
    def ingest_playlist(self, playlist_url: str) -> List[Document]:
        """
        Ingest entire YouTube playlist.
        
        Args:
            playlist_url: YouTube playlist URL
            
        Returns:
            List of Documents from all videos
        """
        # TODO: Implement playlist parsing
        logger.warning("Playlist ingestion not yet implemented")
        return []


# ============================================================================
# PDF Source Handler (Free - PyMuPDF)
# ============================================================================

class PDFSourceHandler:
    """
    Handle PDF ingestion using free PyMuPDFReader.
    Supports local files and online PDFs.
    """
    
    def __init__(self, kb_id: str):
        self.kb_id = kb_id
        self.reader = PyMuPDFReader()
        logger.info(f"PDFSourceHandler initialized for KB: {kb_id}")
    
    def ingest_local_pdf(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Ingest local PDF file.
        
        Args:
            file_path: Path to PDF file
            metadata: Optional metadata
            
        Returns:
            List of LlamaIndex Documents
        """
        try:
            logger.info(f"Ingesting PDF: {file_path}")
            docs = self.reader.load_data(file_path=Path(file_path))
            
            # Enrich metadata
            for doc in docs:
                doc.metadata.update({
                    'source_type': 'pdf',
                    'file_path': file_path,
                    'file_name': os.path.basename(file_path),
                    'kb_id': self.kb_id,
                    'date_ingested': datetime.now().isoformat(),
                    **(metadata or {})
                })
            
            logger.info(f"Successfully ingested {len(docs)} documents from PDF")
            return docs
            
        except Exception as e:
            logger.error(f"Failed to ingest PDF {file_path}: {e}")
            return []
    
    def ingest_online_pdf(self, pdf_url: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Ingest PDF from URL.
        
        Args:
            pdf_url: Direct URL to PDF file
            metadata: Optional metadata
            
        Returns:
            List of LlamaIndex Documents
        """
        import requests
        import tempfile
        
        try:
            logger.info(f"Downloading PDF: {pdf_url}")
            response = requests.get(pdf_url, timeout=60)
            response.raise_for_status()
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name
            
            # Ingest from temp file
            docs = self.ingest_local_pdf(tmp_path, metadata)
            
            # Update metadata with URL
            for doc in docs:
                doc.metadata['source_type'] = 'pdf_online'
                doc.metadata['url'] = pdf_url
                doc.metadata.pop('file_path', None)
            
            # Clean up temp file
            os.unlink(tmp_path)
            
            return docs
            
        except Exception as e:
            logger.error(f"Failed to ingest PDF from {pdf_url}: {e}")
            return []
    
    def ingest_pdf_folder(self, folder_path: str, pattern: str = "*.pdf") -> List[Document]:
        """
        Ingest all PDFs from a folder.
        
        Args:
            folder_path: Path to folder containing PDFs
            pattern: File pattern (default: *.pdf)
            
        Returns:
            List of all documents from all PDFs
        """
        documents = []
        folder = Path(folder_path)
        
        pdf_files = list(folder.glob(pattern))
        logger.info(f"Found {len(pdf_files)} PDFs in {folder_path}")
        
        for pdf_file in pdf_files:
            docs = self.ingest_local_pdf(str(pdf_file))
            documents.extend(docs)
        
        return documents


# ============================================================================
# Markdown Source Handler
# ============================================================================

class MarkdownSourceHandler:
    """
    Handle Markdown file ingestion using SimpleDirectoryReader.
    Preserves markdown structure and hierarchy.
    """
    
    def __init__(self, kb_id: str):
        self.kb_id = kb_id
        logger.info(f"MarkdownSourceHandler initialized for KB: {kb_id}")
    
    def ingest_folder(self, folder_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Ingest all Markdown files from a folder.
        
        Args:
            folder_path: Path to folder containing .md files
            metadata: Optional metadata
            
        Returns:
            List of LlamaIndex Documents
        """
        try:
            logger.info(f"Ingesting Markdown folder: {folder_path}")
            
            reader = SimpleDirectoryReader(
                input_dir=folder_path,
                required_exts=['.md'],
                recursive=True
            )
            docs = reader.load_data()
            
            # Enrich metadata
            for doc in docs:
                file_path = doc.metadata.get('file_path', '')
                doc.metadata.update({
                    'source_type': 'markdown',
                    'folder_path': folder_path,
                    'kb_id': self.kb_id,
                    'date_ingested': datetime.now().isoformat(),
                    'hierarchy': self._extract_hierarchy(file_path, folder_path),
                    **(metadata or {})
                })
            
            logger.info(f"Successfully ingested {len(docs)} Markdown documents")
            return docs
            
        except Exception as e:
            logger.error(f"Failed to ingest Markdown folder {folder_path}: {e}")
            return []
    
    def ingest_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Document]:
        """
        Ingest single Markdown file.
        
        Args:
            file_path: Path to .md file
            metadata: Optional metadata
            
        Returns:
            LlamaIndex Document or None
        """
        try:
            logger.info(f"Ingesting Markdown file: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            doc = Document(
                text=content,
                metadata={
                    'source_type': 'markdown',
                    'file_path': file_path,
                    'file_name': os.path.basename(file_path),
                    'kb_id': self.kb_id,
                    'date_ingested': datetime.now().isoformat(),
                    **(metadata or {})
                }
            )
            
            return doc
            
        except Exception as e:
            logger.error(f"Failed to ingest Markdown file {file_path}: {e}")
            return None
    
    def _extract_hierarchy(self, file_path: str, base_path: str) -> Dict[str, Any]:
        """Extract folder hierarchy from file path"""
        try:
            rel_path = Path(file_path).relative_to(base_path)
            parts = rel_path.parts
            
            return {
                'depth': len(parts) - 1,
                'path_components': list(parts),
                'category': parts[0] if len(parts) > 1 else 'root'
            }
        except:
            return {'depth': 0, 'path_components': [], 'category': 'root'}


# ============================================================================
# Unified Source Handler Factory
# ============================================================================

class SourceHandlerFactory:
    """Factory to create appropriate source handler based on type"""
    
    @staticmethod
    def create_handler(source_type: str, kb_id: str):
        """
        Create source handler based on type.
        
        Args:
            source_type: Type of source (website, youtube, pdf, markdown)
            kb_id: Knowledge base ID
            
        Returns:
            Appropriate source handler instance
        """
        handlers = {
            'website': WebsiteSourceHandler,
            'youtube': YouTubeSourceHandler,
            'pdf': PDFSourceHandler,
            'markdown': MarkdownSourceHandler
        }
        
        handler_class = handlers.get(source_type.lower())
        if not handler_class:
            raise ValueError(f"Unknown source type: {source_type}")
        
        return handler_class(kb_id)
