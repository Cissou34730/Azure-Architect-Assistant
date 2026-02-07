"""
Service layer for WAF checklist management.
Provides FastAPI dependencies and orchestrates Registry and Engine.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_system.checklists.engine import ChecklistEngine
from app.agents_system.checklists.registry import ChecklistRegistry
from app.core.app_settings import AppSettings, get_settings
from app.models.checklist import ChecklistItemEvaluation
from app.projects_database import get_db

logger = logging.getLogger(__name__)

# Singleton registry instance across the application
_REGISTRY_INSTANCE: ChecklistRegistry | None = None


def get_checklist_registry(
    settings: AppSettings = Depends(get_settings),
) -> ChecklistRegistry:
    """
    Dependency to get the ChecklistRegistry singleton.
    """
    global _REGISTRY_INSTANCE  # noqa: PLW0603
    if _REGISTRY_INSTANCE is None:
        cache_dir = Path(settings.waf_template_cache_dir)
        _REGISTRY_INSTANCE = ChecklistRegistry(cache_dir, settings)
    return _REGISTRY_INSTANCE


class ChecklistService:
    """
    Service layer adapter for ChecklistEngine.

    Provides dependency injection and API-friendly interface.
    """

    def __init__(self, engine: ChecklistEngine, registry: ChecklistRegistry) -> None:
        """
        Initialize the service.

        Args:
            engine: The checklist execution engine.
            registry: The template registry.
        """
        self.engine = engine
        self.registry = registry

    async def process_agent_result(self, project_id: str, agent_result: dict) -> dict:
        """
        Process agent result containing AAA_STATE_UPDATE.
        """
        return await self.engine.process_agent_result(project_id, agent_result)

    async def sync_project(
        self, project_id: str, project_state: dict, chunk_size: int | None = None
    ) -> dict:
        """
        Sync project state to normalized database rows.
        """
        return await self.engine.sync_project_state_to_db(
            project_id, project_state, chunk_size
        )

    async def get_progress(
        self, project_id: str, checklist_id: UUID | None = None
    ) -> dict:
        """
        Get completion metrics for project or checklist.
        """
        return await self.engine.compute_progress(project_id, checklist_id)

    async def list_next_actions(
        self, project_id: str, limit: int = 20, severity: str | None = None
    ) -> list[dict]:
        """
        List prioritized next actions for the project.
        """
        return await self.engine.list_next_actions(project_id, limit, severity)

    async def evaluate_item(
        self, project_id: str, item_id: UUID, evaluation_payload: dict
    ) -> ChecklistItemEvaluation:
        """
        Create a new evaluation for a checklist item.
        """
        return await self.engine.evaluate_item(project_id, item_id, evaluation_payload)

    async def get_templates(self) -> list[Any]:
        """
        List all available templates.
        """
        return self.registry.list_templates()

    async def ensure_project_checklist(
        self, project_id: str, template_slug: str = "azure-waf-v1"
    ) -> bool:
        """
        Ensure a project checklist exists and is populated from template items.
        """
        checklist = await self.engine.ensure_project_checklist(project_id, template_slug)
        return checklist is not None


async def get_checklist_service(
    db: AsyncSession = Depends(get_db), settings: AppSettings = Depends(get_settings)
) -> ChecklistService:
    """FastAPI dependency for ChecklistService."""
    registry = get_checklist_registry(settings)

    @asynccontextmanager
    async def session_factory():
        yield db

    engine = ChecklistEngine(
        db_session_factory=session_factory, registry=registry, settings=settings
    )
    return ChecklistService(engine=engine, registry=registry)
