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
    JobListResponse,
    PhaseDetail,
    KBIngestionDetailsResponse,
)
from .ingestion_operations import KBIngestionService, get_ingestion_service
from app.ingestion.application.status_query_service import StatusQueryService

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


@router.get("/kb/{kb_id}/details", response_model=KBIngestionDetailsResponse)
async def get_ingestion_details(
    kb_id: str,
    kb_manager: KBManager = Depends(get_kb_manager_dep),
) -> KBIngestionDetailsResponse:
    """Persisted ingestion details for a KB: current phase, progress, per-phase info."""
    try:
        if not kb_manager.kb_exists(kb_id):
            raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_id}' not found")

        status_service = StatusQueryService()
        s = status_service.get_status(kb_id)

        def to_iso(dt):
            try:
                return dt.isoformat() if dt else None
            except Exception:
                return dt if isinstance(dt, str) else None

        phase_details = [
            PhaseDetail(
                name=p['name'],
                status=p['status'],
                progress=p['progress'],
                items_processed=p['items_processed'],
                items_total=p['items_total'],
                started_at=to_iso(p['started_at']),
                completed_at=to_iso(p['completed_at']),
                error=p['error'],
            )
            for p in s.phase_details
        ]

        return KBIngestionDetailsResponse(
            kb_id=kb_id,
            current_phase=s.current_phase,
            overall_progress=s.overall_progress,
            phase_details=phase_details,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ingestion details: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get ingestion details: {str(e)}")





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
                    job_id = repo.get_latest_job_id(k)
                    if job_id:
                        qs = repo.get_queue_stats(job_id)
                        metrics = {
                            'chunks_pending': qs.get('pending', 0),
                            'chunks_processing': qs.get('processing', 0),
                            'chunks_done': qs.get('done', 0),
                            'chunks_error': qs.get('error', 0),
                            'chunks_queued': sum(qs.values()) if qs else 0,
                        }
                except Exception:
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


# ============================================================================
# Phase 7: Control Endpoints
# ============================================================================

@router.post("/kb/{kb_id}/pause")
async def pause_ingestion(
    kb_id: str,
    ingest_service: IngestionService = Depends(get_ingestion_service_dep),
) -> Dict[str, Any]:
    try:
        # Persist pause on current phase
        from app.ingestion.infrastructure.repository import create_database_repository
        repo = create_database_repository()
        repo.pause_current_phase(kb_id)
        # Best-effort runtime pause
        try:
            ingest_service.pause(kb_id)
        except Exception:
            pass
        return {"message": "Pause requested", "kb_id": kb_id}
    except Exception as e:
        logger.error(f"Failed to pause ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kb/{kb_id}/resume")
async def resume_ingestion(
    kb_id: str,
    ingest_service: IngestionService = Depends(get_ingestion_service_dep),
) -> Dict[str, Any]:
    try:
        # Persist resume on current phase
        from app.ingestion.infrastructure.repository import create_database_repository
        repo = create_database_repository()
        repo.resume_current_phase(kb_id)
        # Best-effort runtime resume
        try:
            ingest_service.resume(kb_id)
        except Exception:
            pass
        return {"message": "Resume requested", "kb_id": kb_id}
    except Exception as e:
        logger.error(f"Failed to resume ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kb/{kb_id}/cancel")
async def cancel_ingestion(
    kb_id: str,
    ingest_service: IngestionService = Depends(get_ingestion_service_dep),
) -> Dict[str, Any]:
    try:
        # Persist cancel/reset
        from app.ingestion.infrastructure.repository import create_database_repository
        repo = create_database_repository()
        repo.cancel_job_and_reset(kb_id)
        # Best-effort runtime cancel
        try:
            ingest_service.cancel(kb_id)
        except Exception:
            pass
        return {"message": "Cancel requested", "kb_id": kb_id}
    except Exception as e:
        logger.error(f"Failed to cancel ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
