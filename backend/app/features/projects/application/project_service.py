from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_system.services.aaa_state_models import ensure_aaa_defaults
from app.features.projects.infrastructure.project_state_decomposition import compose_project_state
from app.features.projects.infrastructure.project_state_store import ProjectStateStore
from app.models import Project

if TYPE_CHECKING:
    from typing import Protocol

    class CreateProjectRequest(Protocol):
        name: str

    class UpdateRequirementsRequest(Protocol):
        text_requirements: str | None

logger = logging.getLogger(__name__)
_project_state_store = ProjectStateStore()

DiagramSessionFactory = Callable[[], AsyncIterator[AsyncSession]]
DiagramSetCleanupGateway = Callable[[AsyncSession, list[str]], Awaitable[None]]
ChecklistBootstrapGateway = Callable[[str, AsyncSession], Awaitable[None]]
ChecklistStateGateway = Callable[[str, AsyncSession], Awaitable[dict[str, Any] | None]]


class ProjectService:
    """Project CRUD operations."""

    def __init__(
        self,
        diagram_session_factory: DiagramSessionFactory | None = None,
        delete_diagram_sets: DiagramSetCleanupGateway | None = None,
        bootstrap_checklists: ChecklistBootstrapGateway | None = None,
        get_checklist_state: ChecklistStateGateway | None = None,
    ) -> None:
        self._diagram_session_factory = diagram_session_factory
        self._delete_diagram_sets = delete_diagram_sets
        self._bootstrap_checklists = bootstrap_checklists
        self._get_checklist_state = get_checklist_state

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

        await _project_state_store.persist_composed_state(
            project_id=project.id,
            state=ensure_aaa_defaults({}),
            db=db,
            replace_missing=True,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

        await db.commit()
        await db.refresh(project)

        if self._bootstrap_checklists is not None:
            await self._bootstrap_checklists(project.id, db)

        logger.info(f"✓ Project persisted to DB: id={project.id}, name={project.name}")
        return cast(dict[str, Any], project.to_dict())

    async def get_waf_checklist_state(
        self,
        project_id: str,
        db: AsyncSession,
    ) -> dict[str, Any] | None:
        if self._get_checklist_state is None:
            return None
        return await self._get_checklist_state(project_id, db)

    async def list_projects(self, db: AsyncSession) -> list[dict[str, Any]]:
        result = await db.execute(
            select(Project).where(Project.deleted_at.is_(None))
        )
        projects = result.scalars().all()
        logger.info(f"Listing {len(projects)} projects")
        return [cast(dict[str, Any], p.to_dict()) for p in projects]

    async def get_project(
        self, project_id: str, db: AsyncSession
    ) -> dict[str, Any] | None:
        result = await db.execute(
            select(Project).where(
                Project.id == project_id, Project.deleted_at.is_(None)
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            return None
        return cast(dict[str, Any], project.to_dict())

    async def update_requirements(
        self, project_id: str, request: UpdateRequirementsRequest, db: AsyncSession
    ) -> dict[str, Any]:
        result = await db.execute(
            select(Project).where(
                Project.id == project_id, Project.deleted_at.is_(None)
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        project.text_requirements = request.text_requirements
        await db.commit()
        await db.refresh(project)

        logger.info(f"Requirements updated for project: {project_id}")
        return cast(dict[str, Any], project.to_dict())

    async def soft_delete_project(self, project_id: str, db: AsyncSession) -> None:
        """Soft delete a project by setting deleted_at timestamp.

        Also cleans up associated diagrams from the diagrams database.
        """
        result = await db.execute(
            select(Project).where(
                Project.id == project_id, Project.deleted_at.is_(None)
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        # Mark project as deleted
        project.deleted_at = datetime.now(timezone.utc).isoformat()
        await db.commit()

        # Clean up associated diagrams (best effort)
        try:
            await self._cleanup_project_diagrams(project_id, db)
        except Exception as e:
            logger.error(
                f"Failed to cleanup diagrams for project {project_id}: {e}",
                exc_info=True,
            )

        logger.info(f"Soft deleted project: {project_id}")

    async def bulk_soft_delete_projects(
        self, project_ids: list[str], db: AsyncSession
    ) -> dict[str, Any]:
        """Bulk soft delete multiple projects.

        Returns dict with deleted_count and project_ids.
        """
        if not project_ids:
            return {"deleted_count": 0, "project_ids": []}

        # Get projects that exist and are not already deleted
        result = await db.execute(
            select(Project).where(
                Project.id.in_(project_ids), Project.deleted_at.is_(None)
            )
        )
        projects = result.scalars().all()

        if not projects:
            return {"deleted_count": 0, "project_ids": []}

        # Mark all projects as deleted
        deleted_at = datetime.now(timezone.utc).isoformat()
        deleted_ids = []
        for project in projects:
            project.deleted_at = deleted_at
            deleted_ids.append(str(project.id))

        await db.commit()

        # Clean up diagrams for all deleted projects (best effort)
        for project_id in deleted_ids:
            try:
                await self._cleanup_project_diagrams(project_id, db)
            except Exception as e:
                logger.error(
                    f"Failed to cleanup diagrams for project {project_id}: {e}",
                    exc_info=True,
                )

        logger.info(f"Bulk soft deleted {len(deleted_ids)} projects: {deleted_ids}")
        return {"deleted_count": len(deleted_ids), "project_ids": deleted_ids}

    async def _cleanup_project_diagrams(
        self, project_id: str, db: AsyncSession
    ) -> None:
        """Delete diagram sets associated with a project from diagrams database.

        Diagrams are linked to projects via ProjectState.state JSON field which
        contains diagram references with diagramSetId.
        """
        # Get project state to find diagram set IDs
        blob_state = await _project_state_store.get_blob_state(project_id=project_id, db=db)
        if blob_state is None:
            return

        try:
            state_data = await compose_project_state(
                project_id=project_id,
                state=blob_state,
                db=db,
            )
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse state for project {project_id}")
            return

        # Extract diagram set IDs from diagrams array
        diagrams = state_data.get("diagrams", [])
        if not isinstance(diagrams, list):
            return

        diagram_set_ids = [
            str(d.get("diagramSetId"))
            for d in diagrams
            if isinstance(d, dict) and d.get("diagramSetId")
        ]

        if not diagram_set_ids:
            return

        if self._diagram_session_factory is None or self._delete_diagram_sets is None:
            logger.warning(
                "Skipping diagram cleanup for project %s because no diagram cleanup gateway is configured",
                project_id,
            )
            return

        # Delete diagram sets from diagrams database
        async for diagram_session in self._diagram_session_factory():
            await self._delete_diagram_sets(diagram_session, diagram_set_ids)
            # Session commits automatically on context manager exit
            logger.info(
                f"Deleted {len(diagram_set_ids)} diagram sets for project {project_id}"
            )




