"""
FastAPI Router for Project CRUD Endpoints
Transport layer only - business logic delegated to project services.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.projects_database import get_db
from app.routers.error_utils import map_value_error
from app.services.project.project_service import ProjectService

from ._deps import get_document_service_dep, get_project_service_dep
from .project_models import (
    BulkDeleteProjectsRequest,
    CreateProjectRequest,
    DeleteResponse,
    ProjectResponse,
    ProjectsListResponse,
    UpdateRequirementsRequest,
)

router = APIRouter(prefix="/api", tags=["projects"])
document_service = get_document_service_dep()



# ============================================================================
# Project CRUD Endpoints
# ============================================================================


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    db: AsyncSession = Depends(get_db),
    project_service: ProjectService = Depends(get_project_service_dep),
) -> dict[str, Any]:
    """Create a new project"""
    try:
        project = await project_service.create_project(request, db)
    except ValueError as e:
        raise map_value_error(e, default_status=400) from e
    return {"project": project}


@router.get("/projects", response_model=ProjectsListResponse)
async def list_projects(
    db: AsyncSession = Depends(get_db),
    project_service: ProjectService = Depends(get_project_service_dep),
) -> dict[str, Any]:
    """List all projects"""
    projects = await project_service.list_projects(db)
    return {"projects": projects}


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    project_service: ProjectService = Depends(get_project_service_dep),
) -> dict[str, Any]:
    """Get project details"""
    project = await project_service.get_project(project_id, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project}


@router.put("/projects/{project_id}/requirements", response_model=ProjectResponse)
async def update_requirements(
    project_id: str,
    request: UpdateRequirementsRequest,
    db: AsyncSession = Depends(get_db),
    project_service: ProjectService = Depends(get_project_service_dep),
) -> dict[str, Any]:
    """Update project requirements"""
    try:
        project = await project_service.update_requirements(project_id, request, db)
    except ValueError as e:
        raise map_value_error(e, default_status=400) from e
    return {"project": project}


@router.delete("/projects/{project_id}", response_model=DeleteResponse)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    project_service: ProjectService = Depends(get_project_service_dep),
) -> dict[str, Any]:
    """Soft delete a project (sets deleted_at timestamp)"""
    try:
        await project_service.soft_delete_project(project_id, db)
    except ValueError as e:
        raise map_value_error(e, default_status=404) from e
    return {
        "message": "Project deleted successfully",
        "deletedCount": 1,
        "projectIds": [project_id],
    }


@router.post("/projects/bulk-delete", response_model=DeleteResponse)
async def bulk_delete_projects(
    request: BulkDeleteProjectsRequest,
    db: AsyncSession = Depends(get_db),
    project_service: ProjectService = Depends(get_project_service_dep),
) -> dict[str, Any]:
    """Bulk soft delete multiple projects"""
    result = await project_service.bulk_soft_delete_projects(request.project_ids, db)
    message = (
        f"Successfully deleted {result['deleted_count']} project(s)"
        if result["deleted_count"] > 0
        else "No projects were deleted"
    )
    return {
        "message": message,
        "deletedCount": result["deleted_count"],
        "projectIds": result["project_ids"],
    }
