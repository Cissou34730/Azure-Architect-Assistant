"""
Pydantic Models for KB Query API
Request and response models for query endpoints.
"""


from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Legacy query request (WAF only)"""

    question: str = Field(..., description="The question to query")
    top_k: int = Field(5, alias="topK", description="Number of results to return")


class ProfileQueryRequest(BaseModel):
    """Query request with profile support"""

    question: str = Field(..., description="The question to query")
    top_k_per_kb: int | None = Field(
        None, alias="topKPerKB", description="Number of results per knowledge base"
    )


class KBQueryRequest(BaseModel):
    """Query request for specific KBs"""

    question: str = Field(..., description="The question to query")
    kb_ids: list[str] = Field(..., description="List of KB IDs to query")
    top_k_per_kb: int = Field(5, alias="topKPerKB", description="Number of results per knowledge base")


class SourceInfo(BaseModel):
    """Source information from query results"""

    url: str
    title: str
    section: str
    score: float
    kb_id: str | None = None
    kb_name: str | None = None


class QueryResponse(BaseModel):
    """Response for query endpoints"""

    answer: str
    sources: list[SourceInfo]
    has_results: bool = Field(True, alias="hasResults")
    suggested_follow_ups: list[str] | None = Field(None, alias="suggestedFollowUps")

