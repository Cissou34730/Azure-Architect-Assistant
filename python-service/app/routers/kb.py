"""
Knowledge Base Router - KB management endpoints
Handles listing and health checking of knowledge bases
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import logging

from app.services import get_kb_manager, get_multi_query_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kb", tags=["knowledge-bases"])


# Response Models
class KBInfo(BaseModel):
    id: str
    name: str
    profiles: List[str]
    priority: int
    status: str


class KBListResponse(BaseModel):
    knowledge_bases: List[KBInfo]


class KBHealthInfo(BaseModel):
    kb_id: str
    kb_name: str
    status: str
    index_ready: bool
    error: str = None


class KBHealthResponse(BaseModel):
    overall_status: str
    knowledge_bases: List[KBHealthInfo]


@router.get("/list", response_model=KBListResponse)
async def list_knowledge_bases():
    """
    List all available knowledge bases with their configuration.
    Returns KB metadata including supported profiles and priority.
    """
    try:
        manager = get_kb_manager()
        kbs_info = manager.list_kbs()
        
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
        
        logger.info(f"Listed {len(kb_list)} knowledge bases")
        return KBListResponse(knowledge_bases=kb_list)
        
    except Exception as e:
        logger.error(f"Failed to list knowledge bases: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list knowledge bases: {str(e)}")


@router.get("/health", response_model=KBHealthResponse)
async def check_kb_health():
    """
    Check health status of all knowledge bases.
    Returns per-KB status including index readiness.
    """
    try:
        service = get_multi_query_service()
        health_result = service.check_health()
        
        kb_health = [
            KBHealthInfo(
                kb_id=kb['kb_id'],
                kb_name=kb['kb_name'],
                status=kb['status'],
                index_ready=kb['index_ready'],
                error=kb.get('error')
            )
            for kb in health_result['kbs']
        ]
        
        logger.info(f"Health check: {health_result['overall_status']}")
        return KBHealthResponse(
            overall_status=health_result['overall_status'],
            knowledge_bases=kb_health
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
