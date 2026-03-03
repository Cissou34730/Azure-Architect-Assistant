"""
KB Management Router
FastAPI endpoints for KB CRUD operations, listing, and health monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_kb_management_service_dependency, get_kb_manager
from app.kb import KBManager
from app.routers.error_utils import map_value_error
from app.services.kb.management_orchestration_service import (
    CreateKnowledgeBaseInput,
    KBManagementService,
)

from .management_models import (
    CreateKBRequest,
    CreateKBResponse,
    KBHealthInfo,
    KBHealthResponse,
    KBInfo,
    KBListResponse,
    KBStatusResponse,
)

router = APIRouter(prefix="/api/kb", tags=["knowledge-bases"])


def get_management_service_dep() -> KBManagementService:
    """Dependency for Management Service."""
    return get_kb_management_service_dependency()


# ============================================================================
# KB CRUD Endpoints
# ============================================================================


@router.post("/create", response_model=CreateKBResponse)
async def create_kb(
    request: CreateKBRequest,
    kb_manager: KBManager = Depends(get_kb_manager),
    operations: KBManagementService = Depends(get_management_service_dep),
) -> CreateKBResponse:
    """Create a new knowledge base"""
    try:
        result = operations.create_knowledge_base(
            CreateKnowledgeBaseInput(
                kb_id=request.kb_id,
                name=request.name,
                description=request.description or "",
                source_type=request.source_type.value,
                source_config=request.source_config,
                embedding_model=request.embedding_model,
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap,
                profiles=request.profiles,
                priority=request.priority,
            ),
            kb_manager,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise map_value_error(e, default_status=400) from e
    return CreateKBResponse(**result)


@router.delete("/{kb_id}")
async def delete_kb(
    kb_id: str,
    kb_manager: KBManager = Depends(get_kb_manager),
    operations: KBManagementService = Depends(get_management_service_dep),
) -> dict[str, str]:
    """
    Delete a knowledge base and all its data.

    This will:
    - Cancel any running ingestion jobs
    - Unload the index from memory
    - Remove the KB from configuration
    - Delete all KB data (index, documents, etc.)
    """
    try:
        return await operations.delete_knowledge_base(kb_id, kb_manager)
    except HTTPException:
        raise
    except ValueError as e:
        raise map_value_error(e, default_status=400) from e


@router.get("/list", response_model=KBListResponse)
async def list_knowledge_bases(
    kb_manager: KBManager = Depends(get_kb_manager),
    operations: KBManagementService = Depends(get_management_service_dep),
) -> KBListResponse:
    """
    List all available knowledge bases with their configuration.
    Returns KB metadata including supported profiles and priority.
    """
    kbs_info = operations.list_knowledge_bases(kb_manager)
    kb_list = [
        KBInfo(
            id=kb["id"],
            name=kb["name"],
            profiles=kb.get("profiles", []),
            priority=kb.get("priority", 0),
            status=kb.get("status", "unknown"),
        )
        for kb in kbs_info
    ]
    return KBListResponse(knowledge_bases=kb_list)


@router.get("/health", response_model=KBHealthResponse)
async def check_kb_health(
    kb_manager: KBManager = Depends(get_kb_manager),
    operations: KBManagementService = Depends(get_management_service_dep),
) -> KBHealthResponse:
    """
    Check health status of all knowledge bases.
    Returns per-KB status including index readiness.
    """
    result = operations.check_health(kb_manager)
    kb_health = [KBHealthInfo(**kb_info) for kb_info in result["knowledge_bases"]]
    return KBHealthResponse(
        overall_status=result["overall_status"], knowledge_bases=kb_health
    )


# ============================================================================
# Phase 3: KB-level persisted status
# ============================================================================


@router.get("/{kb_id}/status", response_model=KBStatusResponse)
async def get_kb_status(
    kb_id: str,
    kb_manager: KBManager = Depends(get_kb_manager),
    operations: KBManagementService = Depends(get_management_service_dep),
) -> KBStatusResponse:
    """Persisted-only KB status derived from phase rows; no runtime calls."""
    payload = operations.get_persisted_status(kb_id, kb_manager)
    return KBStatusResponse.model_validate(payload)

