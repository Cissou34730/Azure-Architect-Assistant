import logging
import uuid
from datetime import datetime, timezone
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project

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
        await db.commit()
        await db.refresh(project)

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

