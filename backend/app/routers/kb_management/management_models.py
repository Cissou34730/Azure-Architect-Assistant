"""
Pydantic Models for KB Management API
Request and response models for KB endpoints.
"""

from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from app.core.config import get_openai_settings, get_kb_defaults


class SourceType(str, Enum):
    """Document source types"""
    WEBSITE = "website"
    YOUTUBE = "youtube"
    PDF = "pdf"
    MARKDOWN = "markdown"


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


class CreateKBResponse(BaseModel):
    """Response after KB creation"""
    message: str
    kb_id: str
    kb_name: str


class KBInfo(BaseModel):
    """Information about a knowledge base"""
    id: str
    name: str
    profiles: List[str]
    priority: int
    status: str


class KBListResponse(BaseModel):
    """Response for KB list endpoint"""
    knowledge_bases: List[KBInfo]


class KBHealthInfo(BaseModel):
    """Health information for a single KB"""
    kb_id: str
    kb_name: str
    status: str
    index_ready: bool
    error: Optional[str] = None


class KBHealthResponse(BaseModel):
    """Response for KB health check endpoint"""
    overall_status: str
    knowledge_bases: List[KBHealthInfo]


class KBStatusResponse(BaseModel):
    """KB-level persisted status response (Phase 3)."""
    kb_id: str
    status: str  # ready | pending | not_ready
    metrics: Optional[Dict[str, int]] = None  # minimal persisted counters
