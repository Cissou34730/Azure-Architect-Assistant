"""
KB Management Router
FastAPI endpoints for KB CRUD operations, listing, and health monitoring.
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_kb_manager
from app.ingestion.application.status_query_service import StatusQueryService
from app.ingestion.infrastructure import create_job_repository, create_queue_repository
from app.kb import KBManager
from app.kb.service import clear_index_cache
from app.service_registry import invalidate_kb_manager
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

        # Invalidate KB manager cache to reload config
        invalidate_kb_manager()

        return CreateKBResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to create KB: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create KB: {e!s}"
        ) from e


@router.delete("/{kb_id}")
async def delete_kb(
    kb_id: str,
    kb_manager: KBManager = Depends(get_kb_manager),
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
        # Check if KB exists
        if not kb_manager.kb_exists(kb_id):
            raise HTTPException(
                status_code=404, detail=f"Knowledge base '{kb_id}' not found"
            )

        # Get KB config before deletion
        kb_config = kb_manager.get_kb(kb_id)
        storage_dir = kb_config.index_path if kb_config else None

        # Persist cancel/reset prior to deletion
        try:
            repo = create_job_repository()
            repo.update_job_status(
                job_id=repo.get_latest_job_id(kb_id) or "", status="canceled"
            )
        except Exception:  # noqa: BLE001
            logger.debug("No active job to cancel for KB: %s", kb_id)

        # Clear index from memory cache
        if storage_dir:
            clear_index_cache(kb_id=kb_id, storage_dir=storage_dir)
            logger.info(f"Cleared index cache for KB: {kb_id}")
            await asyncio.sleep(0.5)

        # Delete the KB
        kb_manager.delete_kb(kb_id)

        # Invalidate KB manager cache to reload config
        invalidate_kb_manager()

        logger.info(f"Deleted KB: {kb_id}")

        return {
            "message": f"Knowledge base '{kb_id}' deleted successfully",
            "kb_id": kb_id,
        }

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Failed to delete KB: {e!s}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to delete KB: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to delete KB: {e!s}"
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
        logger.error(f"Failed to list knowledge bases: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to list knowledge bases: {e!s}"
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
        logger.error(f"Health check failed: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Health check failed: {e!s}"
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
        logger.error(f"Failed to get KB status: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get KB status: {e!s}"
        ) from e

