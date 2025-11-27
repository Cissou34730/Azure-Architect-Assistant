"""
KB Query Router
FastAPI endpoints for knowledge base queries.
"""

from fastapi import APIRouter, HTTPException
import logging

from app.service_registry import get_query_service, get_multi_query_service
from app.kb import QueryProfile
from .models import (
    QueryRequest,
    ProfileQueryRequest,
    KBQueryRequest,
    SourceInfo,
    QueryResponse
)
from .operations import KBQueryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/query", tags=["query"])


@router.post("", response_model=QueryResponse)
@router.post("/", response_model=QueryResponse, include_in_schema=False)
async def query_legacy(request: QueryRequest):
    """
    Legacy WAF query endpoint (redirects to WAF KB service).
    Maintained for backward compatibility.
    """
    try:
        service = get_query_service()
        result = KBQueryService.query_legacy_waf(
            service,
            request.question,
            request.topK
        )
        
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
        service = get_multi_query_service()
        result = KBQueryService.query_with_profile(
            service,
            request.question,
            QueryProfile.CHAT,
            request.topKPerKB
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
        service = get_multi_query_service()
        result = KBQueryService.query_with_profile(
            service,
            request.question,
            QueryProfile.PROPOSAL,
            request.topKPerKB
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
        service = get_multi_query_service()
        result = KBQueryService.query_specific_kbs(
            service,
            request.question,
            request.kb_ids,
            request.topKPerKB
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
