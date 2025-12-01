"""
Query Router - Knowledge base query endpoints
Handles chat and proposal queries with profile support
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from app.service_registry import get_query_service, get_multi_query_service
from app.kb import QueryProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/query", tags=["query"])


# Request/Response Models
class QueryRequest(BaseModel):
    question: str = Field(..., description="The question to query")
    topK: int = Field(5, description="Number of results to return")


class ProfileQueryRequest(BaseModel):
    question: str = Field(..., description="The question to query")
    topKPerKB: Optional[int] = Field(None, description="Number of results per knowledge base")


class KBQueryRequest(BaseModel):
    question: str = Field(..., description="The question to query")
    kb_ids: List[str] = Field(..., description="List of KB IDs to query")
    topKPerKB: int = Field(5, description="Number of results per knowledge base")


class SourceInfo(BaseModel):
    url: str
    title: str
    section: str
    score: float
    kb_id: Optional[str] = None
    kb_name: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceInfo]
    hasResults: bool = True
    suggestedFollowUps: Optional[List[str]] = None


@router.post("", response_model=QueryResponse)
@router.post("/", response_model=QueryResponse, include_in_schema=False)
async def query_legacy(request: QueryRequest):
    """
    Legacy WAF query endpoint (redirects to chat profile).
    Maintained for backward compatibility.
    """
    try:
        logger.info(f"Legacy query request received (redirecting to chat): {request.question[:100]}")
        
        service = get_query_service()
        result = service.query(request.question, top_k=request.topK)
        
        sources = [
            SourceInfo(
                url=source.get('url', ''),
                title=source.get('title', ''),
                section=source.get('section', ''),
                score=source.get('score', 0.0)
            )
            for source in result.get('sources', [])
        ]
        
        return QueryResponse(
            answer=result['answer'],
            sources=sources,
            hasResults=result.get('has_results', True)
        )
        
    except Exception as e:
        logger.error(f"Legacy query failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.post("/chat", response_model=QueryResponse)
async def query_chat(request: ProfileQueryRequest):
    """
    Query knowledge bases using CHAT profile (fast, targeted responses).
    Returns answer with sources from chat-enabled knowledge bases.
    """
    try:
        logger.info(f"Chat query request: {request.question[:100]}")
        
        service = get_multi_query_service()
        
        result = service.query_profile(
            question=request.question,
            profile=QueryProfile.CHAT,
            top_k_per_kb=request.topKPerKB
        )
        
        sources = [
            SourceInfo(
                url=source.get('url', ''),
                title=source.get('title', ''),
                section=source.get('section', ''),
                score=source.get('score', 0.0),
                kb_id=source.get('kb_id'),
                kb_name=source.get('kb_name')
            )
            for source in result.get('sources', [])
        ]
        
        return QueryResponse(
            answer=result['answer'],
            sources=sources,
            hasResults=result.get('has_results', True),
            suggestedFollowUps=result.get('suggested_follow_ups')
        )
        
    except Exception as e:
        logger.error(f"Chat query failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat query failed: {str(e)}")


@router.post("/proposal", response_model=QueryResponse)
async def query_proposal(request: ProfileQueryRequest):
    """
    Query knowledge bases using PROPOSAL profile (comprehensive, detailed responses).
    Returns answer with sources from proposal-enabled knowledge bases.
    """
    try:
        logger.info(f"Proposal query request: {request.question[:100]}")
        
        service = get_multi_query_service()
        
        result = service.query_profile(
            question=request.question,
            profile=QueryProfile.PROPOSAL,
            top_k_per_kb=request.topKPerKB
        )
        
        sources = [
            SourceInfo(
                url=source.get('url', ''),
                title=source.get('title', ''),
                section=source.get('section', ''),
                score=source.get('score', 0.0),
                kb_id=source.get('kb_id'),
                kb_name=source.get('kb_name')
            )
            for source in result.get('sources', [])
        ]
        
        return QueryResponse(
            answer=result['answer'],
            sources=sources,
            hasResults=result.get('has_results', True),
            suggestedFollowUps=result.get('suggested_follow_ups')
        )
        
    except Exception as e:
        logger.error(f"Proposal query failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Proposal query failed: {str(e)}")


@router.post("/kb-query", response_model=QueryResponse)
async def query_kb_manual(request: KBQueryRequest):
    """
    Query specific knowledge bases manually selected by user.
    Used in KB Query tab for manual KB selection.
    """
    try:
        logger.info(f"KB Query request for KBs: {request.kb_ids}, question: {request.question[:100]}")
        
        service = get_multi_query_service()
        
        result = service.query_kbs(
            question=request.question,
            kb_ids=request.kb_ids,
            top_k_per_kb=request.topKPerKB
        )
        
        sources = [
            SourceInfo(
                url=source.get('url', ''),
                title=source.get('title', ''),
                section=source.get('section', ''),
                score=source.get('score', 0.0),
                kb_id=source.get('kb_id'),
                kb_name=source.get('kb_name')
            )
            for source in result.get('sources', [])
        ]
        
        return QueryResponse(
            answer=result['answer'],
            sources=sources,
            hasResults=result.get('has_results', True),
            suggestedFollowUps=result.get('suggested_follow_ups')
        )
        
    except Exception as e:
        logger.error(f"KB Query failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"KB Query failed: {str(e)}")
