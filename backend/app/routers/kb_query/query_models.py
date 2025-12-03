"""
Pydantic Models for KB Query API
Request and response models for query endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class QueryRequest(BaseModel):
    """Legacy query request (WAF only)"""
    question: str = Field(..., description="The question to query")
    topK: int = Field(5, description="Number of results to return")


class ProfileQueryRequest(BaseModel):
    """Query request with profile support"""
    question: str = Field(..., description="The question to query")
    topKPerKB: Optional[int] = Field(None, description="Number of results per knowledge base")


class KBQueryRequest(BaseModel):
    """Query request for specific KBs"""
    question: str = Field(..., description="The question to query")
    kb_ids: List[str] = Field(..., description="List of KB IDs to query")
    topKPerKB: int = Field(5, description="Number of results per knowledge base")


class SourceInfo(BaseModel):
    """Source information from query results"""
    url: str
    title: str
    section: str
    score: float
    kb_id: Optional[str] = None
    kb_name: Optional[str] = None


class QueryResponse(BaseModel):
    """Response for query endpoints"""
    answer: str
    sources: List[SourceInfo]
    hasResults: bool = True
    suggestedFollowUps: Optional[List[str]] = None
