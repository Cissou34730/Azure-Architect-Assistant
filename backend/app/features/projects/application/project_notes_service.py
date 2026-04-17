"""Application service for per-project long-term notes."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.projects.contracts import ProjectNoteContract, ProjectNoteUpsertRequest
from app.models.project import Project, ProjectNote


class ProjectNotesService:
    """CRUD operations for project-scoped notes."""

    async def list_notes(self, *, project_id: str, db: AsyncSession) -> list[ProjectNoteContract]:
        await self._ensure_project_exists(project_id=project_id, db=db)
        result = await db.execute(
            select(ProjectNote)
            .where(ProjectNote.project_id == project_id)
            .order_by(ProjectNote.updated_at.desc(), ProjectNote.created_at.desc())
        )
        return [
            ProjectNoteContract.model_validate(note.to_dict())
            for note in result.scalars().all()
        ]

    async def create_note(
        self,
        *,
        project_id: str,
        request: ProjectNoteUpsertRequest,
        db: AsyncSession,
    ) -> ProjectNoteContract:
        await self._ensure_project_exists(project_id=project_id, db=db)
        timestamp = self._now_iso()
        note = ProjectNote(
            project_id=project_id,
            category=request.category,
            content=request.content,
            source_message_id=request.source_message_id,
            created_at=timestamp,
            updated_at=timestamp,
        )
        db.add(note)
        await db.flush()
        return ProjectNoteContract.model_validate(note.to_dict())

    async def update_note(
        self,
        *,
        project_id: str,
        note_id: str,
        request: ProjectNoteUpsertRequest,
        db: AsyncSession,
    ) -> ProjectNoteContract:
        note = await self._get_note(project_id=project_id, note_id=note_id, db=db)
        note.category = request.category
        note.content = request.content
        note.source_message_id = request.source_message_id
        note.updated_at = self._now_iso()
        await db.flush()
        return ProjectNoteContract.model_validate(note.to_dict())

    async def delete_note(self, *, project_id: str, note_id: str, db: AsyncSession) -> None:
        note = await self._get_note(project_id=project_id, note_id=note_id, db=db)
        await db.delete(note)
        await db.flush()

    async def _ensure_project_exists(self, *, project_id: str, db: AsyncSession) -> None:
        result = await db.execute(
            select(Project.id).where(Project.id == project_id, Project.deleted_at.is_(None))
        )
        if result.scalar_one_or_none() is None:
            raise ValueError("Project not found")

    async def _get_note(
        self,
        *,
        project_id: str,
        note_id: str,
        db: AsyncSession,
    ) -> ProjectNote:
        await self._ensure_project_exists(project_id=project_id, db=db)
        result = await db.execute(
            select(ProjectNote).where(ProjectNote.project_id == project_id, ProjectNote.id == note_id)
        )
        note = result.scalar_one_or_none()
        if note is None:
            raise ValueError("Project note not found")
        return note

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

