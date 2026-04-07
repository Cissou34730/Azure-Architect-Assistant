"""Project workspace persistence queries."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project


class ProjectWorkspaceRepository:
    """Load the project-owned data needed to compose a workspace view."""

    async def get_workspace_seed(
        self,
        *,
        project_id: str,
        db: AsyncSession,
    ) -> dict[str, Any] | None:
        result = await db.execute(
            select(Project)
            .where(Project.id == project_id, Project.deleted_at.is_(None))
            .options(
                selectinload(Project.documents),
                selectinload(Project.messages),
                selectinload(Project.threads),
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            return None

        last_message_at = None
        if project.messages:
            last_message_at = max(message.timestamp for message in project.messages)

        return {
            "project": project.to_dict(),
            "documentCount": len(project.documents),
            "messageCount": len(project.messages),
            "threadCount": len(project.threads),
            "lastMessageAt": last_message_at,
        }
