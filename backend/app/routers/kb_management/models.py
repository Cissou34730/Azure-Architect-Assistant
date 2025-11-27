"""
Pydantic Models for KB Management API
Request and response models for KB endpoints.
"""

from pydantic import BaseModel
from typing import List, Optional


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
