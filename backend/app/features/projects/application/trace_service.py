"""Read-side service for project trace timelines."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.projects.contracts.trace import (
    ProjectTraceEventContract,
    ProjectTraceEventsResponse,
)
from app.models.project import Project, ProjectTraceEvent


class ProjectTraceService:
    """List persisted trace events for a project."""

    async def list_events(
        self,
        *,
        project_id: str,
        db: AsyncSession,
        limit: int = 200,
        thread_id: str | None = None,
    ) -> ProjectTraceEventsResponse:
        await self._ensure_project_exists(project_id=project_id, db=db)

        query = select(ProjectTraceEvent).where(ProjectTraceEvent.project_id == project_id)
        if thread_id is not None:
            query = query.where(ProjectTraceEvent.thread_id == thread_id)

        result = await db.execute(query.order_by(ProjectTraceEvent.created_at.asc()).limit(limit))
        events = [
            ProjectTraceEventContract.model_validate(event.to_dict())
            for event in result.scalars().all()
        ]
        return ProjectTraceEventsResponse(events=events)

    async def _ensure_project_exists(self, *, project_id: str, db: AsyncSession) -> None:
        result = await db.execute(
            select(Project.id).where(Project.id == project_id, Project.deleted_at.is_(None))
        )
        if result.scalar_one_or_none() is None:
            raise ValueError("Project not found")
