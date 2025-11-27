# RAG Ingestion Strategy - LlamaIndex Ecosystem

**Version 1.0** - November 2024
**Status**: Design & Implementation Plan

## Overview

Unified RAG ingestion pipeline supporting 4 source types:
1. **Websites** → TrafilaturaWebReader
2. **YouTube Transcripts** → YoutubeTranscriptReader + LLM Distillation
3. **PDFs** → LlamaParse (local & online)
4. **Markdown Files** → SimpleDirectoryReader

All sources flow through a consistent processing pipeline with LLM-powered distillation and chunking strategies.

---

## Architecture

```
Source Types
├── Websites (URLs, Sitemaps)
│   └── TrafilaturaWebReader
├── YouTube Videos
│   ├── YoutubeTranscriptReader
│   └── LLM Distillation (Structured Output)
├── PDFs (Local & Online)
│   └── LlamaParse (with cost optimization)
└── Markdown Files
    └── SimpleDirectoryReader

    ↓

Document Processing Pipeline
├── Load Documents (source-specific readers)
├── LLM Distillation (YouTube → Q&A + Facts)
├── Chunking Strategy (recursive, semantic)
├── Metadata Enrichment (source, type, category)
└── Embedding & Indexing (OpenAI text-embedding-3-small)

    ↓

Vector Store
├── Persistent Storage (file-based)
└── Query Interface (semantic search + retrieval)
```

---

## 1. Website Ingestion (TrafilaturaWebReader)

### LlamaIndex Integration

```python
from llama_index.readers.web import TrafilaturaWebReader
from llama_index.core import Document

class WebsiteIngestionService:
    """Ingest websites and sitemaps using Trafilatura"""
    
    def __init__(self):
        self.reader = TrafilaturaWebReader()
    
    def ingest_urls(self, urls: List[str]) -> List[Document]:
        """
        Load documents from URLs using Trafilatura
        
        Args:
            urls: List of URLs to crawl
            
        Returns:
            List of LlamaIndex Documents with metadata
        """
        documents = []
        for url in urls:
            try:
                docs = self.reader.load_data([url])
                # Enrich metadata
                for doc in docs:
                    doc.metadata = {
                        'source_type': 'website',
                        'url': url,
                        'date_ingested': datetime.now().isoformat(),
                        'kb_id': self.kb_id
                    }
                documents.extend(docs)
            except Exception as e:
                logger.error(f"Failed to load {url}: {e}")
        
        return documents
    
    def ingest_sitemap(self, sitemap_url: str) -> List[Document]:
        """
        Load all URLs from a sitemap using Trafilatura
        
        Args:
            sitemap_url: URL to sitemap.xml
            
        Returns:
            List of LlamaIndex Documents
        """
        # Parse sitemap and extract URLs
        urls = self._parse_sitemap(sitemap_url)
        return self.ingest_urls(urls)
    
    def _parse_sitemap(self, sitemap_url: str) -> List[str]:
        """Extract URLs from sitemap.xml"""
        import requests
        import xml.etree.ElementTree as ET
        
        response = requests.get(sitemap_url)
        root = ET.fromstring(response.content)
        
        # Handle both regular sitemaps and sitemap indexes
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = []
        
        # Check for sitemap index (points to other sitemaps)
        sitemaps = root.findall('.//ns:loc', namespace)
        if root.tag.endswith('sitemapindex'):
            for sitemap_elem in sitemaps:
                urls.extend(self._parse_sitemap(sitemap_elem.text))
        else:
            # Regular sitemap (points to URLs)
            for url_elem in root.findall('.//ns:loc', namespace):
                urls.append(url_elem.text)
        
        return urls
```

### Configuration

```python
# config/website_sources.py
WEBSITE_SOURCES = [
    {
        'name': 'Azure Well-Architected Framework',
        'type': 'sitemap',
        'url': 'https://learn.microsoft.com/azure/architecture/framework/sitemap.xml',
        'chunk_size': 1024,
        'chunk_overlap': 200
    },
    {
        'name': 'Azure Architecture Center',
        'type': 'sitemap',
        'url': 'https://learn.microsoft.com/azure/architecture/sitemap.xml',
        'chunk_size': 1024,
        'chunk_overlap': 200
    },
    {
        'name': 'Azure Cloud Adoption Framework',
        'type': 'urls',
        'urls': [
            'https://learn.microsoft.com/azure/cloud-adoption-framework',
            'https://learn.microsoft.com/azure/cloud-adoption-framework/govern',
            # ... more URLs
        ],
        'chunk_size': 1024,
        'chunk_overlap': 200
    }
]
```

---

## 2. YouTube Transcript Ingestion + LLM Distillation

### LlamaIndex Integration with Structured Output

```python
from llama_index.readers.youtube_transcript import YoutubeTranscriptReader
from llama_index.core import Document
from llama_index.core.output_parsers import PydanticOutputParser
from llama_index.llm.openai import OpenAI
from pydantic import BaseModel, Field
from typing import List

# Define structured output schema
class KeyConcept(BaseModel):
    """Extracted key concept from transcript"""
    name: str = Field(description="Name of the concept")
    definition: str = Field(description="Definition or rule")

class TechnicalQA(BaseModel):
    """Question/Answer pair extracted from transcript"""
    question: str = Field(description="Technical question that would be asked by an architect")
    answer: str = Field(description="Precise technical answer from the transcript")

class DistilledTranscript(BaseModel):
    """Complete distilled transcript output"""
    key_concepts: List[KeyConcept] = Field(description="Key concepts and facts")
    technical_qa: List[TechnicalQA] = Field(description="Technical Q&A pairs")
    summary: str = Field(description="One-paragraph summary")

class YoutubeIngestionService:
    """Ingest YouTube videos with transcript distillation"""
    
    def __init__(self, kb_id: str):
        self.reader = YoutubeTranscriptReader()
        self.llm = OpenAI(model="gpt-4o-mini")
        self.kb_id = kb_id
        self.output_parser = PydanticOutputParser(DistilledTranscript)
    
    def ingest_video(self, video_url: str, metadata: dict = None) -> List[Document]:
        """
        Load YouTube transcript and distill into structured content
        
        Args:
            video_url: YouTube video URL
            metadata: Additional metadata (title, channel, etc.)
            
        Returns:
            List of Documents: one per concept/Q&A pair for better retrieval
        """
        try:
            # Extract video ID
            video_id = self._extract_video_id(video_url)
            
            # Load transcript
            docs = self.reader.load_data([video_id])
            if not docs:
                logger.warning(f"No transcript found for {video_url}")
                return []
            
            transcript_text = docs[0].get_content()
            
            # Distill transcript using LLM
            distilled = self._distill_transcript(transcript_text)
            
            # Convert to documents (one doc per concept/QA for better retrieval)
            documents = []
            
            # 1. Create a summary document
            summary_doc = Document(
                text=distilled.summary,
                metadata={
                    'source_type': 'youtube',
                    'video_url': video_url,
                    'video_id': video_id,
                    'content_type': 'summary',
                    'title': metadata.get('title', 'YouTube Video') if metadata else 'YouTube Video',
                    'date_ingested': datetime.now().isoformat(),
                    'kb_id': self.kb_id
                }
            )
            documents.append(summary_doc)
            
            # 2. Create documents for each key concept
            for concept in distilled.key_concepts:
                concept_doc = Document(
                    text=f"**{concept.name}**: {concept.definition}",
                    metadata={
                        'source_type': 'youtube',
                        'video_url': video_url,
                        'video_id': video_id,
                        'content_type': 'concept',
                        'concept_name': concept.name,
                        'title': metadata.get('title', 'YouTube Video') if metadata else 'YouTube Video',
                        'date_ingested': datetime.now().isoformat(),
                        'kb_id': self.kb_id
                    }
                )
                documents.append(concept_doc)
            
            # 3. Create documents for each Q&A pair
            for qa in distilled.technical_qa:
                qa_doc = Document(
                    text=f"**Q: {qa.question}**\n\nA: {qa.answer}",
                    metadata={
                        'source_type': 'youtube',
                        'video_url': video_url,
                        'video_id': video_id,
                        'content_type': 'qa',
                        'question': qa.question,
                        'title': metadata.get('title', 'YouTube Video') if metadata else 'YouTube Video',
                        'date_ingested': datetime.now().isoformat(),
                        'kb_id': self.kb_id
                    }
                )
                documents.append(qa_doc)
            
            logger.info(f"Distilled {video_id}: {len(distilled.key_concepts)} concepts, "
                       f"{len(distilled.technical_qa)} Q&A pairs")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to ingest YouTube video {video_url}: {e}")
            return []
    
    def _distill_transcript(self, transcript: str) -> DistilledTranscript:
        """Use LLM to distill transcript into structured format"""
        
        distillation_prompt = """### ROLE
You are a Senior Technical Writer at Microsoft, specializing in Azure Architecture. 
Your mission is to convert raw spoken transcripts into dense, structured technical documentation for a Knowledge Base (RAG).

### INSTRUCTIONS
I will provide you with a segment of a raw transcript (from a technical YouTube video).
Analyze the text and extract two types of structured information:

1. **FACTS & RULES**: Indisputable technical statements, limits (quotas, latencies), firm recommendations (Do/Don't), and key concept definitions.
2. **TECHNICAL Q&A**: Transform narrative explanations into clear Question/Answer pairs. This is critical for future retrieval. The question must be what an architect would ask, and the answer must be the specific technical solution provided in the text.

### CLEANING RULES
- **IGNORE**: Oral style ("um", "so", "you see"), jokes, personal anecdotes, introductions ("Hello everyone"), and marketing fluff.
- **SYNTHESIZE**: If the speaker takes 5 sentences to say "SLA is 99.9%", output only "SLA = 99.9%".
- **CONTEXT**: If an acronym is used (e.g., "ASE"), use the full name at the first mention ("App Service Environment").
- **LANGUAGE**: Keep technical terms in English (Azure terminology), but write the explanations in clear, professional language.

### EXPECTED OUTPUT FORMAT
Extract the information and format as JSON with these fields:
- key_concepts: Array of objects with "name" and "definition"
- technical_qa: Array of objects with "question" and "answer"
- summary: One paragraph summary of the main topics

### INPUT TRANSCRIPT
{transcript}
"""
        
        prompt_formatted = distillation_prompt.format(transcript=transcript)
        
        # Use structured output
        response = self.llm.structured_predict(
            output_cls=DistilledTranscript,
            prompt=prompt_formatted
        )
        
        return response
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from various YouTube URL formats"""
        import re
        
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
        """Ingest entire YouTube playlist"""
        # Extract playlist ID and fetch all videos
        # Implementation depends on YouTube API or web scraping
        pass
```

---

## 3. PDF Ingestion (LlamaParse)

### LlamaIndex Integration with LlamaParse

```python
from llama_index.readers.llamaparse import LlamaParseReader
from llama_index.core import Document
import requests
from urllib.parse import urlparse

class PDFIngestionService:
    """Ingest PDFs using LlamaParse (intelligent parsing)"""
    
    def __init__(self, kb_id: str, api_key: str = None):
        self.reader = LlamaParseReader(api_key=api_key or os.getenv('LLAMA_PARSE_API_KEY'))
        self.kb_id = kb_id
    
    def ingest_local_pdf(self, file_path: str, metadata: dict = None) -> List[Document]:
        """
        Load local PDF using LlamaParse
        
        Args:
            file_path: Path to local PDF file
            metadata: Additional metadata (title, category, etc.)
            
        Returns:
            List of LlamaIndex Documents
        """
        try:
            # LlamaParse handles complex PDFs intelligently
            # Returns structured content with tables, images, etc.
            docs = self.reader.load_data(file_path)
            
            # Enrich metadata
            for doc in docs:
                doc.metadata = {
                    'source_type': 'pdf_local',
                    'file_path': file_path,
                    'file_name': os.path.basename(file_path),
                    'date_ingested': datetime.now().isoformat(),
                    'kb_id': self.kb_id,
                    **(metadata or {})
                }
            
            logger.info(f"Ingested {len(docs)} documents from {file_path}")
            return docs
            
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return []
    
    def ingest_online_pdf(self, pdf_url: str, metadata: dict = None) -> List[Document]:
        """
        Load PDF from URL using LlamaParse
        
        Args:
            pdf_url: Direct URL to PDF file
            metadata: Additional metadata
            
        Returns:
            List of LlamaIndex Documents
        """
        try:
            # Download PDF temporarily
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()
            
            # Save to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name
            
            # Parse with LlamaParse
            docs = self.reader.load_data(tmp_path)
            
            # Enrich metadata
            for doc in docs:
                doc.metadata = {
                    'source_type': 'pdf_online',
                    'url': pdf_url,
                    'file_name': urlparse(pdf_url).path.split('/')[-1],
                    'date_ingested': datetime.now().isoformat(),
                    'kb_id': self.kb_id,
                    **(metadata or {})
                }
            
            # Clean up temp file
            os.unlink(tmp_path)
            
            logger.info(f"Ingested {len(docs)} documents from {pdf_url}")
            return docs
            
        except Exception as e:
            logger.error(f"Failed to parse PDF from {pdf_url}: {e}")
            return []
    
    def ingest_pdf_folder(self, folder_path: str, pattern: str = "*.pdf") -> List[Document]:
        """
        Ingest all PDFs from a folder
        
        Args:
            folder_path: Path to folder containing PDFs
            pattern: File pattern (default: *.pdf)
            
        Returns:
            List of all documents from all PDFs
        """
        documents = []
        folder = Path(folder_path)
        
        for pdf_file in folder.glob(pattern):
            docs = self.ingest_local_pdf(str(pdf_file))
            documents.extend(docs)
        
        logger.info(f"Ingested {len(documents)} documents from {len(list(folder.glob(pattern)))} PDFs")
        return documents
```

### LlamaParse Configuration & Cost Optimization

```python
# LlamaParse pricing: $3-5 per 1000 pages
# Strategy: Parse once, cache results, reuse

class LlamaParseCacheManager:
    """Cache LlamaParse results to minimize API calls"""
    
    def __init__(self, cache_dir: str = "data/llama_parse_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cache_key(self, file_path: str) -> str:
        """Generate cache key from file (hash of path + size + mtime)"""
        import hashlib
        
        stat = os.stat(file_path)
        key_str = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get_cached(self, file_path: str) -> Optional[List[Document]]:
        """Retrieve cached parse results"""
        cache_key = self.get_cache_key(file_path)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
            return [Document(**doc_data) for doc_data in cached_data]
        return None
    
    def cache_result(self, file_path: str, documents: List[Document]):
        """Cache parse results"""
        cache_key = self.get_cache_key(file_path)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        doc_data = [
            {'text': doc.text, 'metadata': doc.metadata}
            for doc in documents
        ]
        
        with open(cache_file, 'w') as f:
            json.dump(doc_data, f)
```

---

## 4. Markdown File Ingestion (SimpleDirectoryReader)

### LlamaIndex Integration

```python
from llama_index.core import SimpleDirectoryReader, Document
from pathlib import Path

class MarkdownIngestionService:
    """Ingest Markdown files using SimpleDirectoryReader"""
    
    def __init__(self, kb_id: str):
        self.kb_id = kb_id
    
    def ingest_markdown_folder(self, folder_path: str, metadata: dict = None) -> List[Document]:
        """
        Load all Markdown files from a folder
        
        Args:
            folder_path: Path to folder containing .md files
            metadata: Additional metadata (category, source, etc.)
            
        Returns:
            List of LlamaIndex Documents
        """
        try:
            reader = SimpleDirectoryReader(
                input_dir=folder_path,
                file_extractor={'.md': MarkdownExtractor()}
            )
            docs = reader.load_data()
            
            # Enrich metadata with hierarchy info
            for doc in docs:
                file_path = doc.metadata.get('file_path', '')
                doc.metadata.update({
                    'source_type': 'markdown',
                    'folder_path': folder_path,
                    'date_ingested': datetime.now().isoformat(),
                    'kb_id': self.kb_id,
                    'hierarchy': self._extract_hierarchy(file_path),
                    **(metadata or {})
                })
            
            logger.info(f"Ingested {len(docs)} Markdown documents from {folder_path}")
            return docs
            
        except Exception as e:
            logger.error(f"Failed to ingest Markdown folder {folder_path}: {e}")
            return []
    
    def ingest_single_markdown(self, file_path: str, metadata: dict = None) -> Optional[Document]:
        """
        Load single Markdown file
        
        Args:
            file_path: Path to .md file
            metadata: Additional metadata
            
        Returns:
            LlamaIndex Document
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            doc = Document(
                text=content,
                metadata={
                    'source_type': 'markdown',
                    'file_path': file_path,
                    'file_name': Path(file_path).name,
                    'date_ingested': datetime.now().isoformat(),
                    'kb_id': self.kb_id,
                    'hierarchy': self._extract_hierarchy(file_path),
                    **(metadata or {})
                }
            )
            
            return doc
            
        except Exception as e:
            logger.error(f"Failed to ingest Markdown file {file_path}: {e}")
            return None
    
    def _extract_hierarchy(self, file_path: str) -> dict:
        """Extract folder hierarchy from file path"""
        path = Path(file_path)
        parts = path.relative_to(path.anchor).parts if hasattr(path, 'relative_to') else path.parts
        
        return {
            'depth': len(parts),
            'path_components': list(parts),
            'category': parts[0] if parts else 'root'
        }


class MarkdownExtractor:
    """Custom extractor for Markdown files to preserve structure"""
    
    def extract(self, file_path: str) -> str:
        """Extract and preserve markdown structure"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
```

---

## 5. Unified Ingestion Pipeline

### Orchestration Service

```python
from enum import Enum
from typing import Union
from datetime import datetime

class SourceType(Enum):
    WEBSITE = "website"
    YOUTUBE = "youtube"
    PDF = "pdf"
    MARKDOWN = "markdown"

class IngestionSource(BaseModel):
    """Configuration for an ingestion source"""
    id: str
    name: str
    source_type: SourceType
    location: Union[str, List[str]]  # URL, folder path, file path, or list of URLs
    metadata: dict = Field(default_factory=dict)
    chunk_size: int = 1024
    chunk_overlap: int = 200
    enabled: bool = True

class UnifiedRAGIngestionService:
    """
    Orchestrates ingestion from all source types with consistent processing
    """
    
    def __init__(self, kb_id: str):
        self.kb_id = kb_id
        self.website_service = WebsiteIngestionService()
        self.youtube_service = YoutubeIngestionService(kb_id)
        self.pdf_service = PDFIngestionService(kb_id)
        self.markdown_service = MarkdownIngestionService(kb_id)
    
    async def ingest_source(self, source: IngestionSource) -> List[Document]:
        """
        Ingest from a source based on its type
        
        Args:
            source: IngestionSource configuration
            
        Returns:
            List of processed documents
        """
        if not source.enabled:
            logger.info(f"Source {source.name} is disabled, skipping")
            return []
        
        logger.info(f"Starting ingestion from {source.name} ({source.source_type.value})")
        
        documents = []
        
        try:
            if source.source_type == SourceType.WEBSITE:
                documents = await self._ingest_websites(source)
            
            elif source.source_type == SourceType.YOUTUBE:
                documents = await self._ingest_youtube(source)
            
            elif source.source_type == SourceType.PDF:
                documents = await self._ingest_pdfs(source)
            
            elif source.source_type == SourceType.MARKDOWN:
                documents = await self._ingest_markdown(source)
            
            # Apply common processing to all documents
            documents = await self._process_documents(documents, source)
            
            logger.info(f"Successfully ingested {len(documents)} documents from {source.name}")
            return documents
            
        except Exception as e:
            logger.error(f"Error ingesting from {source.name}: {e}", exc_info=True)
            return []
    
    async def _ingest_websites(self, source: IngestionSource) -> List[Document]:
        """Handle website ingestion"""
        if isinstance(source.location, str) and source.location.endswith('sitemap.xml'):
            return self.website_service.ingest_sitemap(source.location)
        else:
            urls = source.location if isinstance(source.location, list) else [source.location]
            return self.website_service.ingest_urls(urls)
    
    async def _ingest_youtube(self, source: IngestionSource) -> List[Document]:
        """Handle YouTube ingestion with distillation"""
        video_urls = source.location if isinstance(source.location, list) else [source.location]
        
        all_docs = []
        for url in video_urls:
            docs = self.youtube_service.ingest_video(url, source.metadata)
            all_docs.extend(docs)
        
        return all_docs
    
    async def _ingest_pdfs(self, source: IngestionSource) -> List[Document]:
        """Handle PDF ingestion"""
        locations = source.location if isinstance(source.location, list) else [source.location]
        
        all_docs = []
        for location in locations:
            if location.startswith('http://') or location.startswith('https://'):
                docs = self.pdf_service.ingest_online_pdf(location, source.metadata)
            else:
                # Check if folder or file
                if Path(location).is_dir():
                    docs = self.pdf_service.ingest_pdf_folder(location)
                else:
                    docs = self.pdf_service.ingest_local_pdf(location, source.metadata)
            
            all_docs.extend(docs)
        
        return all_docs
    
    async def _ingest_markdown(self, source: IngestionSource) -> List[Document]:
        """Handle Markdown ingestion"""
        location = source.location if isinstance(source.location, str) else source.location[0]
        
        if Path(location).is_dir():
            return self.markdown_service.ingest_markdown_folder(location, source.metadata)
        else:
            doc = self.markdown_service.ingest_single_markdown(location, source.metadata)
            return [doc] if doc else []
    
    async def _process_documents(self, documents: List[Document], source: IngestionSource) -> List[Document]:
        """
        Apply common processing to all documents:
        - Chunking
        - Metadata enrichment
        - Deduplication
        """
        # Add source-level metadata
        for doc in documents:
            doc.metadata['source_id'] = source.id
            doc.metadata['source_name'] = source.name
            doc.metadata['kb_id'] = self.kb_id
        
        # Apply chunking if specified
        if source.chunk_size and source.chunk_size > 0:
            documents = await self._chunk_documents(
                documents,
                chunk_size=source.chunk_size,
                chunk_overlap=source.chunk_overlap
            )
        
        return documents
    
    async def _chunk_documents(
        self,
        documents: List[Document],
        chunk_size: int = 1024,
        chunk_overlap: int = 200
    ) -> List[Document]:
        """
        Split documents into chunks for better retrieval
        Uses recursive splitting for semantic coherence
        """
        from llama_index.core.text_splitter import RecursiveSplitter
        
        splitter = RecursiveSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        chunked_docs = []
        for doc in documents:
            chunks = splitter.split_text(doc.text)
            
            for chunk in chunks:
                chunk_doc = Document(
                    text=chunk,
                    metadata={
                        **doc.metadata,
                        'chunk_index': len(chunked_docs),
                        'original_doc_id': doc.id
                    }
                )
                chunked_docs.append(chunk_doc)
        
        return chunked_docs
    
    async def ingest_multiple_sources(
        self,
        sources: List[IngestionSource],
        progress_callback = None
    ) -> dict:
        """
        Ingest from multiple sources sequentially with progress tracking
        
        Args:
            sources: List of IngestionSource configurations
            progress_callback: Optional callback(current, total, source_name)
            
        Returns:
            Summary dict with statistics
        """
        stats = {
            'total_sources': len(sources),
            'successful_sources': 0,
            'failed_sources': 0,
            'total_documents': 0,
            'sources_processed': []
        }
        
        for i, source in enumerate(sources):
            if progress_callback:
                await progress_callback(i + 1, len(sources), source.name)
            
            try:
                docs = await self.ingest_source(source)
                stats['successful_sources'] += 1
                stats['total_documents'] += len(docs)
                stats['sources_processed'].append({
                    'name': source.name,
                    'type': source.source_type.value,
                    'document_count': len(docs),
                    'status': 'success'
                })
            except Exception as e:
                stats['failed_sources'] += 1
                stats['sources_processed'].append({
                    'name': source.name,
                    'type': source.source_type.value,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return stats
```

---

## 6. Configuration Schema

### YAML Configuration Example

```yaml
# config/kb-sources-schema.yaml
knowledge_bases:
  - id: "waf-kb"
    name: "Azure Well-Architected Framework"
    sources:
      - id: "waf-website"
        name: "WAF Official Documentation"
        type: "website"
        location: "https://learn.microsoft.com/azure/architecture/framework/sitemap.xml"
        chunk_size: 1024
        chunk_overlap: 200
        enabled: true
      
      - id: "azure-youtube"
        name: "Azure Architecture YouTube"
        type: "youtube"
        location:
          - "https://www.youtube.com/watch?v=..."
          - "https://www.youtube.com/watch?v=..."
        metadata:
          channel: "Microsoft Azure"
          category: "Architecture"
        enabled: true
      
      - id: "architecture-pdfs"
        name: "Architecture Reference PDFs"
        type: "pdf"
        location:
          - "https://learn.microsoft.com/docs/reference.pdf"
          - "data/local_docs/"
        metadata:
          category: "reference"
        enabled: true
      
      - id: "best-practices"
        name: "Local Best Practices"
        type: "markdown"
        location: "data/best-practices/"
        metadata:
          category: "best-practices"
          organization: "internal"
        enabled: true

  - id: "custom-kb"
    name: "Custom Enterprise Knowledge Base"
    sources:
      - id: "company-docs"
        name: "Company Internal Docs"
        type: "markdown"
        location: "/share/documentation/azure/"
        enabled: true
```

---

## 7. Integration with Existing KB System

### Updated KBManager

```python
class KBManager:
    """
    Enhanced KB Manager with unified ingestion support
    """
    
    async def ingest_with_sources(
        self,
        kb_id: str,
        sources: List[IngestionSource]
    ) -> dict:
        """
        Orchestrate complete ingestion pipeline
        """
        ingestion_service = UnifiedRAGIngestionService(kb_id)
        
        # Ingest from all sources
        stats = await ingestion_service.ingest_multiple_sources(
            sources=sources,
            progress_callback=self._update_progress
        )
        
        # Build index from ingested documents
        await self._build_index(kb_id, stats)
        
        return stats
    
    async def _update_progress(self, current: int, total: int, source_name: str):
        """Update ingestion progress"""
        progress = (current / total) * 100
        logger.info(f"Ingestion progress: {progress:.1f}% ({source_name})")
        # Update KB status via event system
```

---

## 8. Performance Considerations

### Parallelization Strategy

```python
class ParallelIngestionService:
    """
    Ingest multiple sources in parallel for faster processing
    """
    
    async def ingest_parallel(
        self,
        sources: List[IngestionSource],
        max_concurrent: int = 3
    ) -> List[Document]:
        """
        Ingest multiple sources concurrently
        
        Args:
            sources: List of sources to ingest
            max_concurrent: Maximum concurrent operations
        """
        import asyncio
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def ingest_with_semaphore(source):
            async with semaphore:
                service = UnifiedRAGIngestionService(source.kb_id or "default")
                return await service.ingest_source(source)
        
        results = await asyncio.gather(
            *[ingest_with_semaphore(source) for source in sources],
            return_exceptions=True
        )
        
        # Flatten and filter
        all_docs = []
        for result in results:
            if isinstance(result, list):
                all_docs.extend(result)
        
        return all_docs
```

### Cost Optimization

```python
# LlamaParse costs: $3-5 per 1000 pages
# Strategy: Cache, batch, and reuse

INGESTION_STRATEGIES = {
    'fast': {
        'description': 'Quick ingestion with basic parsing',
        'chunk_size': 512,
        'chunk_overlap': 50,
        'parallel': True
    },
    'balanced': {
        'description': 'Default strategy',
        'chunk_size': 1024,
        'chunk_overlap': 200,
        'parallel': True
    },
    'thorough': {
        'description': 'Deep ingestion with semantic chunking',
        'chunk_size': 2048,
        'chunk_overlap': 512,
        'parallel': False  # Sequential for consistency
    }
}
```

---

## 9. Error Handling & Resilience

```python
class IngestionErrorHandler:
    """
    Robust error handling for ingestion pipeline
    """
    
    async def retry_with_backoff(
        self,
        operation,
        max_retries: int = 3,
        backoff_factor: float = 2.0
    ):
        """Retry failed operations with exponential backoff"""
        import asyncio
        
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                
                wait_time = backoff_factor ** attempt
                logger.warning(
                    f"Operation failed (attempt {attempt + 1}/{max_retries}), "
                    f"retrying in {wait_time}s: {e}"
                )
                await asyncio.sleep(wait_time)
```

---

## 10. Implementation Roadmap

### Phase 1: Core Implementation
- [x] Define unified ingestion architecture
- [ ] Implement WebsiteIngestionService (TrafilaturaWebReader)
- [ ] Implement YoutubeIngestionService with LLM distillation
- [ ] Implement PDFIngestionService (LlamaParse)
- [ ] Implement MarkdownIngestionService (SimpleDirectoryReader)

### Phase 2: Orchestration
- [ ] Implement UnifiedRAGIngestionService
- [ ] Create IngestionSource configuration schema
- [ ] Integrate with existing KB management system
- [ ] Add progress tracking and events

### Phase 3: Optimization
- [ ] Implement caching for LlamaParse results
- [ ] Add parallel ingestion support
- [ ] Optimize chunking strategies
- [ ] Add deduplication logic

### Phase 4: Testing & Documentation
- [ ] Unit tests for each ingestion service
- [ ] Integration tests with LlamaIndex
- [ ] Performance benchmarks
- [ ] Complete API documentation

---

## Distillation Prompt (Ready to Use)

```markdown
### ROLE
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

### EXPECTED OUTPUT FORMAT (JSON)
{
  "key_concepts": [
    {"name": "...", "definition": "..."},
    {"name": "...", "definition": "..."}
  ],
  "technical_qa": [
    {"question": "...", "answer": "..."},
    {"question": "...", "answer": "..."}
  ],
  "summary": "..."
}

### INPUT TRANSCRIPT
[Transcript goes here]
```

---

## References

- **LlamaIndex Documentation**: https://docs.llamaindex.ai/
- **TrafilaturaWebReader**: https://github.com/llm-extraction/trafilatura
- **YoutubeTranscriptReader**: https://github.com/xtekky/youtube-transcript-api
- **LlamaParse**: https://www.llamaindex.ai/llama-parse
- **SimpleDirectoryReader**: https://docs.llamaindex.ai/en/stable/module_guides/loading/simple_directory_reader/

