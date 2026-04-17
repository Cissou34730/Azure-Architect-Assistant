"""Project note endpoints owned by the projects feature."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.projects.application.project_notes_service import ProjectNotesService
from app.features.projects.contracts import (
    ProjectNoteDeleteResponse,
    ProjectNoteResponse,
    ProjectNotesListResponse,
    ProjectNoteUpsertRequest,
)
from app.shared.db.projects_database import get_db
from app.shared.http.error_utils import map_value_error

from ._deps import get_project_notes_service_dep

router = APIRouter(prefix="/api", tags=["projects"])


@router.get("/projects/{project_id}/notes", response_model=ProjectNotesListResponse)
async def list_project_notes(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    project_notes_service: ProjectNotesService = Depends(get_project_notes_service_dep),
) -> ProjectNotesListResponse:
    try:
        notes = await project_notes_service.list_notes(project_id=project_id, db=db)
    except ValueError as exc:
        raise map_value_error(exc, default_status=404) from exc
    return ProjectNotesListResponse(notes=notes)


@router.post("/projects/{project_id}/notes", response_model=ProjectNoteResponse)
async def create_project_note(
    project_id: str,
    request: ProjectNoteUpsertRequest,
    db: AsyncSession = Depends(get_db),
    project_notes_service: ProjectNotesService = Depends(get_project_notes_service_dep),
) -> ProjectNoteResponse:
    try:
        note = await project_notes_service.create_note(project_id=project_id, request=request, db=db)
    except ValueError as exc:
        raise map_value_error(exc, default_status=404) from exc
    return ProjectNoteResponse(note=note)


@router.put("/projects/{project_id}/notes/{note_id}", response_model=ProjectNoteResponse)
async def update_project_note(
    project_id: str,
    note_id: str,
    request: ProjectNoteUpsertRequest,
    db: AsyncSession = Depends(get_db),
    project_notes_service: ProjectNotesService = Depends(get_project_notes_service_dep),
) -> ProjectNoteResponse:
    try:
        note = await project_notes_service.update_note(
            project_id=project_id,
            note_id=note_id,
            request=request,
            db=db,
        )
    except ValueError as exc:
        raise map_value_error(exc, default_status=404) from exc
    return ProjectNoteResponse(note=note)


@router.delete("/projects/{project_id}/notes/{note_id}", response_model=ProjectNoteDeleteResponse)
async def delete_project_note(
    project_id: str,
    note_id: str,
    db: AsyncSession = Depends(get_db),
    project_notes_service: ProjectNotesService = Depends(get_project_notes_service_dep),
) -> ProjectNoteDeleteResponse:
    try:
        await project_notes_service.delete_note(project_id=project_id, note_id=note_id, db=db)
    except ValueError as exc:
        raise map_value_error(exc, default_status=404) from exc
    return ProjectNoteDeleteResponse(deleted=True, note_id=note_id)
