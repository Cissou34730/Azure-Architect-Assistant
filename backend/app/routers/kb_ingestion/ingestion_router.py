"""
FastAPI Router for KB Ingestion Endpoints
Clean routing layer - business logic delegated to operations.py
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
import logging

from app.ingestion.application.ingestion_service import IngestionService
from app.service_registry import get_kb_manager
from app.kb.knowledge_base_manager import KBManager

from .ingestion_models import (
    StartIngestionRequest,
    StartIngestionResponse,
    JobStatusResponse,
    JobListResponse
)
from .ingestion_operations import KBIngestionService, get_ingestion_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingestion", tags=["kb-ingestion"])


# ============================================================================
# Dependency Injection
# ============================================================================

def get_kb_manager_dep() -> KBManager:
    """Dependency for KB Manager - allows mocking in tests"""
    return get_kb_manager()


def get_ingestion_service_dep() -> IngestionService:
    """Dependency for Ingestion Service - allows mocking in tests"""
    return IngestionService.instance()


def get_operations_service_dep() -> KBIngestionService:
    """Dependency for Operations Service - allows mocking in tests"""
    return get_ingestion_service()


# ============================================================================
# Ingestion Job Endpoints
# ============================================================================

@router.post("/kb/{kb_id}/start", response_model=StartIngestionResponse)
async def start_ingestion(
    kb_id: str,
    kb_manager: KBManager = Depends(get_kb_manager_dep),
    ingest_service: IngestionService = Depends(get_ingestion_service_dep),
    operations: KBIngestionService = Depends(get_operations_service_dep)
) -> StartIngestionResponse:
    """Start ingestion for a knowledge base"""
    try:
        # Validate and get orchestration result
        result = operations.start_ingestion(kb_id)
        
        # Get KB configuration
        kb_config = kb_manager.get_kb_config(kb_id)
        
        # Start ingestion
        await ingest_service.start(kb_id, kb_config)
        # Retrieve job_id from current state
        state = ingest_service.status(kb_id)
        job_id = state.job_id if state and state.job_id else f"{kb_id}-job"
        
        # Return result including job_id
        return StartIngestionResponse(message=result.get("message", "Ingestion started"), job_id=job_id, kb_id=kb_id)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start ingestion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start ingestion: {str(e)}")


@router.get("/kb/{kb_id}/status")
async def get_kb_status(
    kb_id: str,
    kb_manager: KBManager = Depends(get_kb_manager_dep)
) -> Dict[str, Any]:
    """Get live ingestion metrics for a KB (no persisted state)."""
    try:
        if not kb_manager.kb_exists(kb_id):
            raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_id}' not found")

        index_ready = False
        try:
            index_ready = kb_manager.is_index_ready(kb_id)
        except Exception as e:
            logger.warning(f"KB {kb_id}: readiness check failed: {e}")

        # Try to fetch live queue stats if repository exists
        metrics: Dict[str, Any] = {}
        try:
            from app.ingestion.infrastructure.repository import create_database_repository
            repo = create_database_repository()
            # Use kb_id as job_id surrogate when no orchestrator/state exists
            queue_stats = repo.get_queue_stats(job_id=kb_id)
            metrics.update({
                'chunks_pending': queue_stats.get('pending', 0),
                'chunks_processing': queue_stats.get('processing', 0),
                'chunks_done': queue_stats.get('done', 0),
                'chunks_error': queue_stats.get('error', 0),
                'chunks_queued': sum(queue_stats.values()) if queue_stats else 0,
            })
        except Exception as e:
            logger.info(f"KB {kb_id}: queue stats unavailable: {e}")

        # Attempt to read lightweight in-memory counters from KB manager if exposed
        try:
            counters = kb_manager.get_runtime_counters(kb_id)
            metrics.update({
                'documents_loaded': counters.get('documents_loaded', 0),
                'chunks_enqueued': counters.get('chunks_enqueued', 0),
            })
        except Exception:
            pass

        return {
            'kb_id': kb_id,
            'index_ready': index_ready,
            'metrics': metrics,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")





@router.get("/jobs")
async def list_jobs(
    kb_id: Optional[str] = None,
    limit: int = 50,
    kb_manager: KBManager = Depends(get_kb_manager_dep)
) -> Dict[str, Any]:
    """List KBs with minimal live metrics (no persisted jobs)."""
    try:
        kb_ids = kb_manager.list_kbs()
        if kb_id:
            kb_ids = [k for k in kb_ids if k == kb_id]
        kb_ids = kb_ids[:limit]

        items = []
        from app.ingestion.infrastructure.repository import create_database_repository
        repo = None
        try:
            repo = create_database_repository()
        except Exception:
            repo = None

        for k in kb_ids:
            index_ready = False
            try:
                index_ready = kb_manager.is_index_ready(k)
            except Exception:
                pass
            metrics = {}
            if repo:
                try:
                    qs = repo.get_queue_stats(job_id=k)
                    metrics = {
                        'chunks_pending': qs.get('pending', 0),
                        'chunks_processing': qs.get('processing', 0),
                        'chunks_done': qs.get('done', 0),
                        'chunks_error': qs.get('error', 0),
                        'chunks_queued': sum(qs.values()) if qs else 0,
                    }
                } except Exception:
                    pass
            items.append({
                'kb_id': k,
                'index_ready': index_ready,
                'metrics': metrics,
            })

        return {'items': items}
    except Exception as e:
        logger.error(f"Failed to list jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")
