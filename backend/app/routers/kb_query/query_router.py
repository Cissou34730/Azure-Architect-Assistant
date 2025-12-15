"""
KB Query Router
FastAPI endpoints for knowledge base queries.
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends
import logging

from app.service_registry import get_multi_query_service, get_kb_manager
from app.services.kb import QueryProfile, MultiKBQueryService
from app.kb.service import KnowledgeBaseService
from .query_models import (
    QueryRequest,
    ProfileQueryRequest,
    KBQueryRequest,
    SourceInfo,
    QueryResponse
)
from .query_operations import KBQueryService, get_query_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/query", tags=["query"])


# ============================================================================
# Dependency Injection
# ============================================================================

def get_multi_query_service_dep() -> MultiKBQueryService:
    """Dependency for Multi Query Service - allows mocking in tests"""
    return get_multi_query_service()


def get_query_service_dep() -> KBQueryService:
    """Dependency for Query Service - allows mocking in tests"""
    return get_query_service()


# ============================================================================
# Query Endpoints
# ============================================================================

@router.post("", response_model=QueryResponse)
@router.post("/", response_model=QueryResponse, include_in_schema=False)
async def query_legacy(
    request: QueryRequest,
    multi_query_service: MultiKBQueryService = Depends(get_multi_query_service_dep),
    operations: KBQueryService = Depends(get_query_service_dep)
) -> QueryResponse:
    """
    Legacy query endpoint - queries all active KBs using CHAT profile.
    Maintained for backward compatibility.
    """
    try:
        result = operations.query_with_profile(
            multi_query_service,
            request.question,
            QueryProfile.CHAT,
            request.topK
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
        logger.error(f"Legacy query failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.post("/chat", response_model=QueryResponse)
async def query_chat(
    request: ProfileQueryRequest,
    multi_query_service: MultiKBQueryService = Depends(get_multi_query_service_dep),
    operations: KBQueryService = Depends(get_query_service_dep)
) -> QueryResponse:
    """
    Query knowledge bases using CHAT profile (fast, targeted responses).
    Returns answer with sources from chat-enabled knowledge bases.
    """
    try:
        # Filter to ready KBs only
        ready_kbs = [kb for kb in get_kb_manager().get_kbs_for_profile(QueryProfile.CHAT.value)
                     if KnowledgeBaseService(kb).is_index_ready()]
        if not ready_kbs:
            return QueryResponse(
                answer="No indexed knowledge bases available for chat yet.",
                sources=[],
                hasResults=False,
                suggestedFollowUps=None
            )

        result = operations.query_with_profile(
            multi_query_service,
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
async def query_proposal(
    request: ProfileQueryRequest,
    multi_query_service: MultiKBQueryService = Depends(get_multi_query_service_dep),
    operations: KBQueryService = Depends(get_query_service_dep)
) -> QueryResponse:
    """
    Query knowledge bases using PROPOSAL profile (comprehensive, detailed responses).
    Returns answer with sources from proposal-enabled knowledge bases.
    """
    try:
        ready_kbs = [kb for kb in get_kb_manager().get_kbs_for_profile(QueryProfile.PROPOSAL.value)
                     if KnowledgeBaseService(kb).is_index_ready()]
        if not ready_kbs:
            return QueryResponse(
                answer="No indexed knowledge bases available for proposal yet.",
                sources=[],
                hasResults=False,
                suggestedFollowUps=None
            )

        result = operations.query_with_profile(
            multi_query_service,
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
async def query_kb_manual(
    request: KBQueryRequest,
    multi_query_service: MultiKBQueryService = Depends(get_multi_query_service_dep),
    operations: KBQueryService = Depends(get_query_service_dep)
) -> QueryResponse:
    """
    Query specific knowledge bases manually selected by user.
    Used in KB Query tab for manual KB selection.
    """
    try:
        # Filter input kb_ids to those with ready indexes
        from typing import List
        kb_ids: List[str] = [kb_id for kb_id in request.kb_ids
                             if (lambda cfg: cfg and KnowledgeBaseService(cfg).is_index_ready())
                             (get_kb_manager().get_kb(kb_id))]
        if not kb_ids:
            return QueryResponse(
                answer="Selected KBs have no built index yet.",
                sources=[],
                hasResults=False,
                suggestedFollowUps=None
            )

        result = operations.query_specific_kbs(
            multi_query_service,
            request.question,
            kb_ids,
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
