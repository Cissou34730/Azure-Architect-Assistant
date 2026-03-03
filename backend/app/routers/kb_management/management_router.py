"""
KB Management Router
FastAPI endpoints for KB CRUD operations, listing, and health monitoring.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_kb_manager
from app.ingestion.application.status_query_service import StatusQueryService
from app.ingestion.infrastructure import create_job_repository, create_queue_repository
from app.kb import KBManager
from app.routers.error_utils import internal_server_error, map_value_error
from app.services.kb import MultiKBQueryService

from .management_models import (
    CreateKBRequest,
    CreateKBResponse,
    KBHealthInfo,
    KBHealthResponse,
    KBInfo,
    KBListResponse,
    KBStatusResponse,
)
from .management_operations import KBManagementService, get_management_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/kb", tags=["knowledge-bases"])


# ============================================================================
# Dependency Injection
# Note: Using centralized dependencies from app.dependencies for consistency
# ============================================================================


def get_multi_query_service_dep() -> MultiKBQueryService:
    """Dependency for Multi Query Service."""
    from app.service_registry import get_multi_query_service
    return get_multi_query_service()


def get_management_service_dep() -> KBManagementService:
    """Dependency for Management Service."""
    return get_management_service()


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
        result = operations.create_knowledge_base(request, kb_manager)
        return CreateKBResponse(**result)
    except ValueError as e:
        raise map_value_error(e, default_status=400) from e
    except Exception as e:
        raise internal_server_error(
            logger=logger,
            message=f"Failed to create KB: {e!s}",
            exc=e,
            detail_prefix="Failed to create KB",
        ) from e


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
    except Exception as e:
        raise internal_server_error(
            logger=logger,
            message=f"Failed to delete KB: {e!s}",
            exc=e,
            detail_prefix="Failed to delete KB",
        ) from e


@router.get("/list", response_model=KBListResponse)
async def list_knowledge_bases(
    kb_manager: KBManager = Depends(get_kb_manager),
    operations: KBManagementService = Depends(get_management_service_dep),
) -> KBListResponse:
    """
    List all available knowledge bases with their configuration.
    Returns KB metadata including supported profiles and priority.
    """
    try:
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

    except Exception as e:
        raise internal_server_error(
            logger=logger,
            message=f"Failed to list knowledge bases: {e!s}",
            exc=e,
            detail_prefix="Failed to list knowledge bases",
        ) from e


@router.get("/health", response_model=KBHealthResponse)
async def check_kb_health(
    kb_manager: KBManager = Depends(get_kb_manager),
    operations: KBManagementService = Depends(get_management_service_dep),
) -> KBHealthResponse:
    """
    Check health status of all knowledge bases.
    Returns per-KB status including index readiness.
    """
    try:
        result = operations.check_health(kb_manager)

        kb_health = [KBHealthInfo(**kb_info) for kb_info in result["knowledge_bases"]]

        return KBHealthResponse(
            overall_status=result["overall_status"], knowledge_bases=kb_health
        )

    except Exception as e:
        raise internal_server_error(
            logger=logger,
            message=f"Health check failed: {e!s}",
            exc=e,
            detail_prefix="Health check failed",
        ) from e


# ============================================================================
# Phase 3: KB-level persisted status
# ============================================================================


@router.get("/{kb_id}/status", response_model=KBStatusResponse)
async def get_kb_status(
    kb_id: str,
    kb_manager: KBManager = Depends(get_kb_manager),
) -> KBStatusResponse:
    """Persisted-only KB status derived from phase rows; no runtime calls."""
    try:
        if not kb_manager.kb_exists(kb_id):
            raise HTTPException(
                status_code=404, detail=f"Knowledge base '{kb_id}' not found"
            )

        status_service = StatusQueryService()
        status = status_service.get_status(kb_id)

        # Minimal persisted counters from queue using correct job_id
        metrics = None
        try:
            queue_repo = create_queue_repository()
            job_repo = create_job_repository()
            job_id = job_repo.get_latest_job_id(kb_id)
            if job_id:
                qs = queue_repo.get_queue_stats(job_id)
                metrics = {
                    "pending": qs.get("pending", 0),
                    "processing": qs.get("processing", 0),
                    "done": qs.get("done", 0),
                    "error": qs.get("error", 0),
                }
        except Exception:  # noqa: BLE001
            metrics = None

        return KBStatusResponse(kb_id=kb_id, status=status.status, metrics=metrics)
    except HTTPException:
        raise
    except Exception as e:
        raise internal_server_error(
            logger=logger,
            message=f"Failed to get KB status: {e!s}",
            exc=e,
            detail_prefix="Failed to get KB status",
        ) from e

