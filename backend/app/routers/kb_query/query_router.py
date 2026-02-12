"""
KB Query Router
FastAPI endpoints for knowledge base queries.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_kb_manager
from app.kb import KBManager
from app.kb.service import KnowledgeBaseService
from app.services.kb import MultiKBQueryService, QueryProfile

from .query_models import (
    KBQueryRequest,
    ProfileQueryRequest,
    QueryRequest,
    QueryResponse,
    SourceInfo,
)
from .query_operations import KBQueryService, get_query_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/query", tags=["query"])


# ============================================================================
# Dependency Injection
# Note: Using centralized dependencies from app.dependencies for consistency
# ============================================================================


def get_multi_query_service_dep() -> MultiKBQueryService:
    """Dependency for Multi Query Service."""
    from app.service_registry import get_multi_query_service
    return get_multi_query_service()


def get_query_service_dep() -> KBQueryService:
    """Dependency for Query Service."""
    return get_query_service()


# ============================================================================
# Query Endpoints
# ============================================================================


@router.post("", response_model=QueryResponse)
@router.post("/", response_model=QueryResponse, include_in_schema=False)
async def query_legacy(
    request: QueryRequest,
    multi_query_service: MultiKBQueryService = Depends(get_multi_query_service_dep),
    operations: KBQueryService = Depends(get_query_service_dep),
) -> QueryResponse:
    """
    Legacy query endpoint - queries all active KBs using CHAT profile.
    Maintained for backward compatibility.
    """
    try:
        result = operations.query_with_profile(
            multi_query_service, request.question, QueryProfile.CHAT, request.top_k
        )

        sources = [
            SourceInfo(
                url=source.get("url", ""),
                title=source.get("title", ""),
                section=source.get("section", ""),
                score=source.get("score", 0.0),
                kb_id=source.get("kb_id"),
                kb_name=source.get("kb_name"),
            )
            for source in result.get("sources", [])
        ]

        return QueryResponse(
            answer=result["answer"],
            sources=sources,
            has_results=result.get("has_results", True),
            suggested_follow_ups=result.get("suggested_follow_ups"),
        )

    except Exception as e:
        logger.error(f"Legacy query failed: {e!s}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {e!s}") from e


@router.post("/chat", response_model=QueryResponse)
async def query_chat(
    request: ProfileQueryRequest,
    multi_query_service: MultiKBQueryService = Depends(get_multi_query_service_dep),
    operations: KBQueryService = Depends(get_query_service_dep),
    kb_manager: KBManager = Depends(get_kb_manager),
) -> QueryResponse:
    """
    Query knowledge bases using CHAT profile (fast, targeted responses).
    Returns answer with sources from chat-enabled knowledge bases.
    """
    try:
        # Filter to ready KBs only
        ready_kbs = [
            kb
            for kb in kb_manager.get_kbs_for_profile(QueryProfile.CHAT.value)
            if KnowledgeBaseService(kb).is_index_ready()
        ]
        if not ready_kbs:
            return QueryResponse(
                answer="No indexed knowledge bases available for chat yet.",
                sources=[],
                has_results=False,
                suggested_follow_ups=None,
            )

        result = operations.query_with_profile(
            multi_query_service,
            request.question,
            QueryProfile.CHAT,
            request.top_k_per_kb,
        )

        sources = [
            SourceInfo(
                url=source.get("url", ""),
                title=source.get("title", ""),
                section=source.get("section", ""),
                score=source.get("score", 0.0),
                kb_id=source.get("kb_id"),
                kb_name=source.get("kb_name"),
            )
            for source in result.get("sources", [])
        ]

        return QueryResponse(
            answer=result["answer"],
            sources=sources,
            has_results=result.get("has_results", True),
            suggested_follow_ups=result.get("suggested_follow_ups"),
        )

    except Exception as e:
        logger.error(f"Chat query failed: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Chat query failed: {e!s}"
        ) from e


@router.post("/proposal", response_model=QueryResponse)
async def query_proposal(
    request: ProfileQueryRequest,
    multi_query_service: MultiKBQueryService = Depends(get_multi_query_service_dep),
    operations: KBQueryService = Depends(get_query_service_dep),
    kb_manager: KBManager = Depends(get_kb_manager),
) -> QueryResponse:
    """
    Query knowledge bases using PROPOSAL profile (comprehensive, detailed responses).
    Returns answer with sources from proposal-enabled knowledge bases.
    """
    try:
        ready_kbs = [
            kb
            for kb in kb_manager.get_kbs_for_profile(QueryProfile.PROPOSAL.value)
            if KnowledgeBaseService(kb).is_index_ready()
        ]
        if not ready_kbs:
            return QueryResponse(
                answer="No indexed knowledge bases available for proposal yet.",
                sources=[],
                has_results=False,
                suggested_follow_ups=None,
            )

        result = operations.query_with_profile(
            multi_query_service,
            request.question,
            QueryProfile.PROPOSAL,
            request.top_k_per_kb,
        )

        sources = [
            SourceInfo(
                url=source.get("url", ""),
                title=source.get("title", ""),
                section=source.get("section", ""),
                score=source.get("score", 0.0),
                kb_id=source.get("kb_id"),
                kb_name=source.get("kb_name"),
            )
            for source in result.get("sources", [])
        ]

        return QueryResponse(
            answer=result["answer"],
            sources=sources,
            has_results=result.get("has_results", True),
            suggested_follow_ups=result.get("suggested_follow_ups"),
        )

    except Exception as e:
        logger.error(f"Proposal query failed: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Proposal query failed: {e!s}"
        ) from e


@router.post("/kb-query", response_model=QueryResponse)
async def query_kb_manual(
    request: KBQueryRequest,
    multi_query_service: MultiKBQueryService = Depends(get_multi_query_service_dep),
    operations: KBQueryService = Depends(get_query_service_dep),
    kb_manager: KBManager = Depends(get_kb_manager),
) -> QueryResponse:
    """
    Query specific knowledge bases manually selected by user.
    Used in KB Query tab for manual KB selection.
    """
    try:
        # Filter input kb_ids to those with ready indexes
        kb_ids: list[str] = []
        for kb_id in request.kb_ids:
            kb_config = kb_manager.get_kb(kb_id)
            if kb_config and KnowledgeBaseService(kb_config).is_index_ready():
                kb_ids.append(kb_id)

        if not kb_ids:
            return QueryResponse(
                answer="Selected KBs have no built index yet.",
                sources=[],
                has_results=False,
                suggested_follow_ups=None,
            )

        result = operations.query_specific_kbs(
            multi_query_service, request.question, kb_ids, request.top_k_per_kb
        )

        sources = [
            SourceInfo(
                url=source.get("url", ""),
                title=source.get("title", ""),
                section=source.get("section", ""),
                score=source.get("score", 0.0),
                kb_id=source.get("kb_id"),
                kb_name=source.get("kb_name"),
            )
            for source in result.get("sources", [])
        ]

        return QueryResponse(
            answer=result["answer"],
            sources=sources,
            has_results=result.get("has_results", True),
            suggested_follow_ups=result.get("suggested_follow_ups"),
        )

    except Exception as e:
        logger.error(f"KB Query failed: {e!s}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"KB Query failed: {e!s}") from e

