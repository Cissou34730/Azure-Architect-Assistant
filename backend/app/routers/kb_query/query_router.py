"""
KB Query Router
FastAPI endpoints for knowledge base queries.
"""

from typing import Any, cast

from fastapi import APIRouter, Depends

from app.dependencies import (
    get_kb_manager,
    get_kb_query_service_dependency,
    get_multi_query_service_dependency,
)
from app.kb import KBManager
from app.kb.service import KnowledgeBaseService
from app.services.kb import MultiKBQueryService, QueryProfile
from app.services.kb.query_orchestration_service import KBQueryService

from .query_models import (
    KBQueryRequest,
    ProfileQueryRequest,
    QueryRequest,
    QueryResponse,
    SourceInfo,
)

router = APIRouter(prefix="/api/query", tags=["query"])


# ============================================================================
# Dependency Injection
# Note: Using centralized dependencies from app.dependencies for consistency
# ============================================================================


def get_multi_query_service_dep() -> MultiKBQueryService:
    """Dependency for Multi Query Service."""
    return get_multi_query_service_dependency()


def get_query_service_dep() -> KBQueryService:
    """Dependency for Query Service."""
    return get_kb_query_service_dependency()


def _to_query_response(result: dict[str, str | list | bool | None]) -> QueryResponse:
    raw_sources = cast(list[dict[str, Any]], result.get("sources") or [])
    sources = [
        SourceInfo(
            url=source.get("url", ""),
            title=source.get("title", ""),
            section=source.get("section", ""),
            score=source.get("score", 0.0),
            kb_id=source.get("kb_id"),
            kb_name=source.get("kb_name"),
        )
        for source in raw_sources
        if isinstance(source, dict)
    ]
    return QueryResponse(
        answer=str(result["answer"]),
        sources=sources,
        hasResults=result.get("has_results", True),
        suggestedFollowUps=result.get("suggested_follow_ups"),
    )


def _ready_kbs_for_profile(kb_manager: KBManager, profile: QueryProfile) -> list[object]:
    return [
        kb
        for kb in kb_manager.get_kbs_for_profile(profile.value)
        if KnowledgeBaseService(kb).is_index_ready()
    ]


def _ready_selected_kb_ids(kb_manager: KBManager, kb_ids: list[str]) -> list[str]:
    """Filter user-selected KB ids to those with a ready index."""
    return [
        kb_id
        for kb_id in kb_ids
        if (kb_config := kb_manager.get_kb(kb_id))
        and KnowledgeBaseService(kb_config).is_index_ready()
    ]


# ============================================================================
# Query Endpoints
# ============================================================================


@router.post("", response_model=QueryResponse)
async def query_legacy(
    request: QueryRequest,
    multi_query_service: MultiKBQueryService = Depends(get_multi_query_service_dep),
    operations: KBQueryService = Depends(get_query_service_dep),
) -> QueryResponse:
    """
    Legacy query endpoint - queries all active KBs using CHAT profile.
    Maintained for backward compatibility.
    """
    result = operations.query_with_profile(
        multi_query_service, request.question, QueryProfile.CHAT, request.top_k
    )
    return _to_query_response(result)


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
    ready_kbs = _ready_kbs_for_profile(kb_manager, QueryProfile.CHAT)
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
    return _to_query_response(result)


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
    ready_kbs = _ready_kbs_for_profile(kb_manager, QueryProfile.PROPOSAL)
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
    return _to_query_response(result)


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
    ready_kb_ids = _ready_selected_kb_ids(kb_manager, request.kb_ids)
    if not ready_kb_ids:
        return QueryResponse(
            answer="Selected KBs have no built index yet.",
            sources=[],
            has_results=False,
            suggested_follow_ups=None,
        )

    result = operations.query_specific_kbs(
        multi_query_service, request.question, ready_kb_ids, request.top_k_per_kb
    )
    return _to_query_response(result)

