import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_system.checklists.default_templates import resolve_bootstrap_template_slugs
from app.agents_system.checklists.engine import ChecklistEngine
from app.agents_system.checklists.registry import ChecklistRegistry
from app.agents_system.services.aaa_state_models import ensure_aaa_defaults
from app.core.app_settings import get_app_settings
from app.models import Project
from app.models.project import ProjectState

from ..project_models import CreateProjectRequest, UpdateRequirementsRequest

logger = logging.getLogger(__name__)


class ProjectService:
    """Project CRUD operations."""

    async def create_project(
        self, request: CreateProjectRequest, db: AsyncSession
    ) -> dict[str, Any]:
        if not request.name or not request.name.strip():
            raise ValueError("Project name is required")

        project = Project(
            id=str(uuid.uuid4()),
            name=request.name.strip(),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        db.add(project)
        await db.flush()

        initial_state = ensure_aaa_defaults({})
        db.add(
            ProjectState(
                project_id=project.id,
                state=json.dumps(initial_state),
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
        )

        await db.commit()
        await db.refresh(project)

        await self._bootstrap_waf_checklist(project.id, db)

        logger.info(f"✓ Project persisted to DB: id={project.id}, name={project.name}")
        return cast(dict[str, Any], project.to_dict())

    async def list_projects(self, db: AsyncSession) -> list[dict[str, Any]]:
        result = await db.execute(select(Project))
        projects = result.scalars().all()
        logger.info(f"Listing {len(projects)} projects")
        return [cast(dict[str, Any], p.to_dict()) for p in projects]

    async def get_project(
        self, project_id: str, db: AsyncSession
    ) -> dict[str, Any] | None:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            return None
        return cast(dict[str, Any], project.to_dict())

    async def update_requirements(
        self, project_id: str, request: UpdateRequirementsRequest, db: AsyncSession
    ) -> dict[str, Any]:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        project.text_requirements = request.text_requirements
        await db.commit()
        await db.refresh(project)

        logger.info(f"Requirements updated for project: {project_id}")
        return cast(dict[str, Any], project.to_dict())

    async def _bootstrap_waf_checklist(self, project_id: str, db: AsyncSession) -> None:
        settings = get_app_settings()
        if not settings.aaa_feature_waf_normalized:
            return

        @asynccontextmanager
        async def session_factory():
            yield db

        registry = ChecklistRegistry(Path(settings.waf_template_cache_dir), settings)
        engine = ChecklistEngine(session_factory, registry, settings)

        try:
            selected_slugs = resolve_bootstrap_template_slugs(
                [template.slug for template in registry.list_templates()]
            )
            checklists = await engine.ensure_project_checklists(
                project_id, selected_slugs if selected_slugs else None
            )
            if not checklists:
                logger.warning(
                    "Project %s created without checklist bootstrap (no template available).",
                    project_id,
                )
                return

            reconstructed = await engine.sync_db_to_project_state(project_id)
            if not reconstructed:
                return

            waf_payload = _merge_reconstructed_waf(reconstructed)
            if not isinstance(waf_payload, dict):
                return

            state_record = (
                await db.execute(
                    select(ProjectState).where(ProjectState.project_id == project_id)
                )
            ).scalar_one_or_none()
            if state_record is None:
                return

            try:
                state_data = (
                    json.loads(state_record.state)
                    if isinstance(state_record.state, str)
                    else dict(state_record.state)
                )
            except json.JSONDecodeError:
                state_data = {}

            state_data = ensure_aaa_defaults(state_data)
            state_data["wafChecklist"] = waf_payload
            state_record.state = json.dumps(state_data)
            state_record.updated_at = datetime.now(timezone.utc).isoformat()
            await db.commit()
            logger.info("Bootstrapped WAF checklist for project %s at creation time.", project_id)
        except Exception as exc:
            await db.rollback()
            logger.error(
                "Failed to bootstrap WAF checklist for project %s: %s",
                project_id,
                exc,
                exc_info=True,
            )


def _merge_reconstructed_waf(reconstructed: dict[str, Any]) -> dict[str, Any] | None:
    """Merge multiple reconstructed template payloads into one legacy-compatible object."""
    if not reconstructed:
        return None

    all_items: list[dict[str, Any]] = []
    pillar_order: list[str] = []
    seen_pillars: set[str] = set()
    versions: set[str] = set()

    for payload in reconstructed.values():
        if not isinstance(payload, dict):
            continue

        version = payload.get("version")
        if isinstance(version, str) and version.strip():
            versions.add(version.strip())

        pillars = payload.get("pillars", [])
        if isinstance(pillars, list):
            for pillar in pillars:
                name = str(pillar).strip()
                if not name or name in seen_pillars:
                    continue
                seen_pillars.add(name)
                pillar_order.append(name)

        items = payload.get("items")
        if isinstance(items, list):
            all_items.extend(item for item in items if isinstance(item, dict))
        elif isinstance(items, dict):
            all_items.extend(item for item in items.values() if isinstance(item, dict))

    merged_version = versions.pop() if len(versions) == 1 else "multi"
    return {
        "version": merged_version,
        "pillars": pillar_order,
        "items": all_items,
    }

