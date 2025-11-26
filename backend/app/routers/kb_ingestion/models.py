"""
Request/Response Models for KB Ingestion API
"""

from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

from app.kb.ingestion.job_manager import JobStatus, IngestionPhase


class SourceType(str, Enum):
    """Document source types"""
    WEB_DOCUMENTATION = "web_documentation"
    WEB_GENERIC = "web_generic"
    LOCAL_FILES = "local_files"


class WebDocumentationConfig(BaseModel):
    """Configuration for structured documentation crawler"""
    start_urls: List[HttpUrl]
    allowed_domains: Optional[List[str]] = None
    path_prefix: Optional[str] = None
    follow_links: bool = True
    max_pages: int = 1000


class WebGenericConfig(BaseModel):
    """Configuration for generic web crawler"""
    urls: List[HttpUrl]
    follow_links: bool = False
    max_depth: int = 1
    same_domain_only: bool = True


class CreateKBRequest(BaseModel):
    """Request to create a new knowledge base"""
    kb_id: str = Field(..., description="Unique KB identifier")
    name: str = Field(..., description="Human-readable KB name")
    description: Optional[str] = Field(None, description="KB description")
    source_type: SourceType = Field(..., description="Type of document source")
    source_config: Dict[str, Any] = Field(..., description="Source-specific configuration")
    embedding_model: str = Field(default="text-embedding-3-small", description="OpenAI embedding model")
    chunk_size: int = Field(default=800, description="Chunk size for indexing")
    chunk_overlap: int = Field(default=120, description="Chunk overlap for indexing")
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
