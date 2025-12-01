"""
KB Management Router
FastAPI endpoints for KB CRUD operations, listing, and health monitoring.
"""

from fastapi import APIRouter, HTTPException
import logging
import asyncio

from app.service_registry import get_kb_manager, get_multi_query_service, invalidate_kb_manager
from app.kb.service import clear_index_cache
from .models import (
    KBInfo, 
    KBListResponse, 
    KBHealthInfo, 
    KBHealthResponse,
    CreateKBRequest,
    CreateKBResponse
)
from .operations import KBManagementService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/kb", tags=["knowledge-bases"])


@router.post("/create", response_model=CreateKBResponse)
async def create_kb(request: CreateKBRequest):
    """Create a new knowledge base"""
    try:
        manager = get_kb_manager()
        result = KBManagementService.create_knowledge_base(request, manager)
        
        # Invalidate KB manager cache to reload config
        invalidate_kb_manager()
        
        return CreateKBResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create KB: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create KB: {str(e)}")


@router.delete("/{kb_id}")
async def delete_kb(kb_id: str):
    """
    Delete a knowledge base and all its data.
    
    This will:
    - Cancel any running ingestion jobs
    - Unload the index from memory
    - Remove the KB from configuration
    - Delete all KB data (index, documents, etc.)
    """
    try:
        kb_manager = get_kb_manager()
        
        # Check if KB exists
        if not kb_manager.kb_exists(kb_id):
            raise HTTPException(
                status_code=404,
                detail=f"Knowledge base '{kb_id}' not found"
            )
        
        # Get KB config before deletion
        kb_config = kb_manager.get_kb(kb_id)
        storage_dir = kb_config.index_path if kb_config else None
        
        # Cancel any running ingestion via IngestionService
        from app.ingestion.service import IngestionService
        ingest_service = IngestionService.instance()
        await ingest_service.cancel(kb_id)
        logger.info(f"Cancelled ingestion for KB before deletion: {kb_id}")
        await asyncio.sleep(1.0)
        
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
            "kb_id": kb_id
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Failed to delete KB: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete KB: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete KB: {str(e)}")


@router.get("/list", response_model=KBListResponse)
async def list_knowledge_bases():
    """
    List all available knowledge bases with their configuration.
    Returns KB metadata including supported profiles and priority.
    """
    try:
        manager = get_kb_manager()
        kbs_info = KBManagementService.list_knowledge_bases(manager)
        
        kb_list = [
            KBInfo(
                id=kb['id'],
                name=kb['name'],
                profiles=kb.get('profiles', []),
                priority=kb.get('priority', 0),
                status=kb.get('status', 'unknown')
            )
            for kb in kbs_info
        ]
        
        return KBListResponse(knowledge_bases=kb_list)
        
    except Exception as e:
        logger.error(f"Failed to list knowledge bases: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list knowledge bases: {str(e)}"
        )


@router.get("/health", response_model=KBHealthResponse)
async def check_kb_health():
    """
    Check health status of all knowledge bases.
    Returns per-KB status including index readiness.
    """
    try:
        service = get_multi_query_service()
        result = KBManagementService.check_health(service)
        
        kb_health = [
            KBHealthInfo(**kb_info)
            for kb_info in result['knowledge_bases']
        ]
        
        return KBHealthResponse(
            overall_status=result['overall_status'],
            knowledge_bases=kb_health
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )
