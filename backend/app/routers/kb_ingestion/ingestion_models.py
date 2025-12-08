"""
Request/Response Models for KB Ingestion API
"""

from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
from config import get_openai_settings, get_kb_defaults

from app.ingestion.domain.phase_tracker import IngestionPhase
from app.ingestion.domain.enums import JobStatus


class SourceType(str, Enum):
    """Document source types"""
    WEBSITE = "website"           # URLs/sitemaps → TrafilaturaWebReader
    YOUTUBE = "youtube"           # Video URLs → YoutubeTranscriptReader + LLM distillation
    PDF = "pdf"                   # PDF files (local/online) → PyMuPDFReader
    MARKDOWN = "markdown"         # Markdown files → SimpleDirectoryReader


class WebsiteConfig(BaseModel):
    """Configuration for website ingestion (Trafilatura)"""
    urls: Optional[List[HttpUrl]] = Field(None, description="List of URLs to crawl")
    sitemap_url: Optional[HttpUrl] = Field(None, description="Sitemap URL")


class YouTubeConfig(BaseModel):
    """Configuration for YouTube video ingestion"""
    video_urls: List[HttpUrl] = Field(..., description="List of YouTube video URLs")
    playlist_url: Optional[HttpUrl] = Field(None, description="YouTube playlist URL")


class PDFConfig(BaseModel):
    """Configuration for PDF ingestion"""
    local_paths: Optional[List[str]] = Field(None, description="Local PDF file paths")
    pdf_urls: Optional[List[HttpUrl]] = Field(None, description="Online PDF URLs")
    folder_path: Optional[str] = Field(None, description="Folder containing PDFs")


class MarkdownConfig(BaseModel):
    """Configuration for Markdown file ingestion"""
    folder_path: str = Field(..., description="Folder containing .md files")
    recursive: bool = Field(default=True, description="Recursively scan subfolders")


class PhaseDetail(BaseModel):
    """Detailed information about a single phase"""
    name: str = Field(..., description="Phase name (not_started, loading, chunking, embedding, indexing)")
    status: str = Field(..., description="Phase status (not_started, pending, running, completed, failed)")
    progress: int = Field(default=0, ge=0, le=100, description="Phase progress percentage")
    items_processed: int = Field(default=0, description="Number of items processed in this phase")
    items_total: int = Field(default=0, description="Total items for this phase")
    started_at: Optional[str] = Field(None, description="Phase start timestamp (ISO format)")
    completed_at: Optional[str] = Field(None, description="Phase completion timestamp (ISO format)")
    error: Optional[str] = Field(None, description="Error message if phase failed")


class CreateKBRequest(BaseModel):
    """Request to create a new knowledge base"""
    kb_id: str = Field(..., description="Unique KB identifier")
    name: str = Field(..., description="Human-readable KB name")
    description: Optional[str] = Field(None, description="KB description")
    source_type: SourceType = Field(..., description="Type of document source")
    source_config: Dict[str, Any] = Field(..., description="Source-specific configuration")
    embedding_model: str = Field(default_factory=lambda: get_openai_settings().embedding_model, description="OpenAI embedding model")
    chunk_size: int = Field(default_factory=lambda: get_kb_defaults().chunk_size, description="Chunk size for indexing")
    chunk_overlap: int = Field(default_factory=lambda: get_kb_defaults().chunk_overlap, description="Chunk overlap for indexing")
    profiles: Optional[List[str]] = Field(default=["chat", "kb-query"], description="Query profiles")
    priority: int = Field(default=1, description="KB priority for multi-query")


class StartIngestionRequest(BaseModel):
    """Request to start ingestion for a KB"""
    kb_id: str = Field(..., description="KB identifier")


class JobStatusResponse(BaseModel):
    """Job status information"""
    job_id: str
    kb_id: str
    status: JobStatus
    phase: IngestionPhase
    progress: float
    message: str
    error: Optional[str] = None
    metrics: Dict[str, Any]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    phase_details: Optional[List[PhaseDetail]] = Field(
        None, 
        description="Detailed status for each ingestion phase"
    )


class JobListResponse(BaseModel):
    """List of all jobs"""
    jobs: List[JobStatusResponse]


class CreateKBResponse(BaseModel):
    """Response after KB creation"""
    message: str
    kb_id: str
    kb_name: str


class StartIngestionResponse(BaseModel):
    """Response after starting ingestion"""
    message: str
    job_id: str
    kb_id: str


class KBListResponse(BaseModel):
    """List of knowledge bases"""
    knowledge_bases: List[Dict[str, Any]]
