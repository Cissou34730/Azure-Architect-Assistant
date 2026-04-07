"""Workspace endpoints owned by the projects feature."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.projects.application import ProjectWorkspaceComposer
from app.features.projects.contracts import ProjectWorkspaceView
from app.shared.db.projects_database import get_db

from ._deps import get_workspace_composer_dep

router = APIRouter(prefix="/api", tags=["projects"])


@router.get("/projects/{project_id}/workspace", response_model=ProjectWorkspaceView)
async def get_project_workspace(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    workspace_composer: ProjectWorkspaceComposer = Depends(get_workspace_composer_dep),
) -> ProjectWorkspaceView:
    """Return a composed workspace view for a project."""
    try:
        return await workspace_composer.compose(project_id=project_id, db=db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
