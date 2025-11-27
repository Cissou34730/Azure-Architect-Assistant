"""
KB Management Router
FastAPI endpoints for KB listing and health monitoring.
"""

from fastapi import APIRouter, HTTPException
import logging

from app.service_registry import get_kb_manager, get_multi_query_service
from .models import KBInfo, KBListResponse, KBHealthInfo, KBHealthResponse
from .operations import KBManagementService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/kb", tags=["knowledge-bases"])


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
