"""Orchestration layer for KB management API endpoints."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from fastapi import HTTPException

from app.features.ingestion.application.metrics import (
    build_persisted_status_metrics,
    get_job_counters,
)
from app.features.ingestion.application.status_query_service import StatusQueryService
from app.features.ingestion.infrastructure import create_job_repository
from app.features.knowledge.infrastructure import (
    KBManager,
    KnowledgeBaseService,
    clear_index_cache,
)
from app.service_registry import ServiceRegistry
from app.shared.config.app_settings import get_app_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CreateKnowledgeBaseInput:
    kb_id: str
    name: str
    description: str
    source_type: str
    source_config: dict[str, Any]
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    profiles: list[str] | None
    priority: int


class KBManagementService:
    """Stateless orchestration for KB CRUD and health endpoints."""

    def __init__(
        self,
        invalidate_kb_cache: Callable[[], None] = ServiceRegistry.invalidate_kb_manager,
    ) -> None:
        self._invalidate_kb_cache = invalidate_kb_cache

    def create_knowledge_base(
        self, request: CreateKnowledgeBaseInput, manager: KBManager
    ) -> dict[str, str]:
        if manager.kb_exists(request.kb_id):
            raise ValueError(f"Knowledge base '{request.kb_id}' already exists")

        kb_config = {
            "id": request.kb_id,
            "name": request.name,
            "description": request.description,
            "status": "active",
            "source_type": request.source_type,
            "source_config": request.source_config,
            "embedding_model": request.embedding_model,
            "chunk_size": request.chunk_size,
            "chunk_overlap": request.chunk_overlap,
            "profiles": request.profiles or ["chat", "kb-query"],
            "priority": request.priority,
            "indexed": False,
        }

        manager.create_kb(request.kb_id, kb_config)
        self._invalidate_kb_cache()
        logger.info("KB created id=%s name=%s", request.kb_id, request.name)

        return {
            "message": f"Knowledge base '{request.name}' created successfully",
            "kb_id": request.kb_id,
            "kb_name": request.name,
        }

    def list_knowledge_bases(self, manager: KBManager) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], manager.list_kbs())

    def check_health(self, manager: KBManager) -> dict[str, Any]:
        health_dict: dict[str, dict[str, Any]] = {}
        for kb in manager.knowledge_bases.values():
            try:
                if not kb.is_active:
                    health_dict[kb.id] = {
                        "name": kb.name,
                        "status": "inactive",
                        "error": None,
                    }
                    continue

                ready = KnowledgeBaseService(kb).is_index_ready()
                status = "ready" if ready else "not-indexed"
                health_dict[kb.id] = {"name": kb.name, "status": status, "error": None}
            except Exception as exc:
                logger.exception("Health check failed for KB %s", kb.id)
                health_dict[kb.id] = {
                    "name": kb.name,
                    "status": "error",
                    "error": str(exc),
                }

        kb_health = []
        all_ready = True
        for kb_id, kb_info in health_dict.items():
            index_ready = kb_info.get("status") == "ready"
            if not index_ready:
                all_ready = False

            kb_health.append(
                {
                    "kb_id": kb_id,
                    "kb_name": kb_info["name"],
                    "status": kb_info["status"],
                    "index_ready": index_ready,
                    "error": kb_info.get("error"),
                }
            )

        overall_status = (
            "healthy"
            if all_ready
            else "degraded"
            if len(kb_health) > 0
            else "unavailable"
        )
        logger.info("KB health status=%s", overall_status)
        return {"overall_status": overall_status, "knowledge_bases": kb_health}

    def get_persisted_status(
        self, kb_id: str, manager: KBManager
    ) -> dict[str, str | dict[str, int] | None]:
        if not manager.kb_exists(kb_id):
            raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_id}' not found")

        status = StatusQueryService().get_status(kb_id)
        metrics: dict[str, int] | None = None

        try:
            job_repo = create_job_repository()
            job_id = job_repo.get_latest_job_id(kb_id)
            if job_id:
                metrics = build_persisted_status_metrics(
                    status,
                    get_job_counters(job_repo.get_job(job_id)),
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Unable to retrieve persisted ingestion metrics for kb_id=%s: %s",
                kb_id,
                exc,
                exc_info=True,
            )

        return {"kb_id": kb_id, "status": status.status, "metrics": metrics}

    async def delete_knowledge_base(
        self, kb_id: str, manager: KBManager
    ) -> dict[str, str]:
        if not manager.kb_exists(kb_id):
            raise HTTPException(
                status_code=404,
                detail=f"Knowledge base '{kb_id}' not found",
            )

        kb_config = manager.get_kb(kb_id)
        storage_dir = kb_config.index_path if kb_config else None

        try:
            repo = create_job_repository()
            repo.update_job_status(
                job_id=repo.get_latest_job_id(kb_id) or "",
                status="canceled",
            )
        except Exception:  # noqa: BLE001
            logger.debug("No active job to cancel for KB: %s", kb_id)

        if storage_dir:
            clear_index_cache(kb_id=kb_id, storage_dir=storage_dir)
            await asyncio.sleep(get_app_settings().kb_operation_sleep)

        manager.delete_kb(kb_id)
        self._invalidate_kb_cache()
        logger.info("Deleted KB: %s", kb_id)
        return {
            "message": f"Knowledge base '{kb_id}' deleted successfully",
            "kb_id": kb_id,
        }


_management_service = KBManagementService()


def get_management_service() -> KBManagementService:
    """Get KB management orchestration service instance."""
    return _management_service
