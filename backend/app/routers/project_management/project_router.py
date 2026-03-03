"""
FastAPI Router for Project Management Endpoints
Transport layer only - business logic delegated to project services.
"""

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.app_settings import get_app_settings
from app.projects_database import get_db
from app.routers.error_utils import map_value_error
from app.services.project.chat_service import ChatService
from app.services.project.document_content_service import DocumentContentService
from app.services.project.document_service import DocumentService
from app.services.project.project_analysis_service import ProjectAnalysisService
from app.services.project.project_service import ProjectService
from app.services.project.proposal_stream_service import stream_architecture_proposal
from app.services.project.state_edit_service import ProjectStateEditService

from .project_models import (
    BulkDeleteProjectsRequest,
    CreateProjectRequest,
    DeleteResponse,
    DocumentsResponse,
    MessagesResponse,
    ProjectResponse,
    ProjectsListResponse,
    StateResponse,
    UpdateRequirementsRequest,
)

router = APIRouter(prefix="/api", tags=["projects"])
project_service = ProjectService()
document_service = DocumentService()
document_content_service = DocumentContentService()
project_analysis_service = ProjectAnalysisService(document_service)
chat_service = ChatService()
project_state_edit_service = ProjectStateEditService()


class AdrAppendRequest(BaseModel):
    adr_field: str = "decision"
    append_text: str



# ============================================================================
# Project CRUD Endpoints
# ============================================================================


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Create a new project"""
    try:
        project = await project_service.create_project(request, db)
    except ValueError as e:
        raise map_value_error(e, default_status=400) from e
    return {"project": project}


@router.get("/projects", response_model=ProjectsListResponse)
async def list_projects(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """List all projects"""
    projects = await project_service.list_projects(db)
    return {"projects": projects}


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
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
) -> dict[str, Any]:
    """Update project requirements"""
    try:
        project = await project_service.update_requirements(project_id, request, db)
    except ValueError as e:
        raise map_value_error(e, default_status=400) from e
    return {"project": project}


@router.delete("/projects/{project_id}", response_model=DeleteResponse)
async def delete_project(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Soft delete a project (sets deleted_at timestamp)"""
    try:
        await project_service.soft_delete_project(project_id, db)
    except ValueError as e:
        raise map_value_error(e, default_status=400) from e
    return {
        "message": "Project deleted successfully",
        "deletedCount": 1,
        "projectIds": [project_id],
    }


@router.post("/projects/bulk-delete", response_model=DeleteResponse)
async def bulk_delete_projects(
    request: BulkDeleteProjectsRequest, db: AsyncSession = Depends(get_db)
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


# ============================================================================
# Document Management Endpoints
# ============================================================================


@router.post("/projects/{project_id}/documents", response_model=DocumentsResponse)
async def upload_documents(
    project_id: str,
    # Frontend sends "documents"; keep backward-compatible support for "files".
    documents: list[UploadFile] | None = File(default=None),
    files: list[UploadFile] | None = File(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Upload documents for a project"""
    selected_files = documents or files
    if not selected_files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    try:
        upload_result = await document_service.upload_documents(project_id, selected_files, db)
    except ValueError as e:
        raise map_value_error(e, default_status=400) from e
    return {
        "documents": upload_result.get("documents", []),
        "uploadSummary": upload_result.get("uploadSummary", {}),
    }


@router.get("/projects/{project_id}/documents/{document_id}/content")
async def get_document_content(
    project_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    payload = await document_content_service.resolve_content(
        project_id=project_id,
        document_id=document_id,
        db=db,
    )

    return FileResponse(
        path=payload["path"],
        media_type=str(payload["media_type"]),
        filename=str(payload["file_name"]),
        content_disposition_type="inline",
    )


@router.post("/projects/{project_id}/analyze-docs", response_model=StateResponse)
async def analyze_documents(project_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Analyze documents and generate initial ProjectState"""
    try:
        state = await project_analysis_service.analyze_documents_with_bootstrap(
            project_id=project_id,
            db=db,
        )
    except ValueError as e:
        raise map_value_error(e, default_status=400) from e
    return {"projectState": state}



# ============================================================================
# Chat & State Management Endpoints
# ============================================================================


@router.get("/projects/{project_id}/state", response_model=StateResponse)
async def get_project_state(project_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Get current project state"""
    try:
        state = await chat_service.get_project_state(project_id, db)
    except ValueError as e:
        raise map_value_error(e, default_status=400) from e
    return {"projectState": state}


@router.get("/projects/{project_id}/messages", response_model=MessagesResponse)
async def get_messages(
    project_id: str,
    before_id: str | None = None,
    since_id: str | None = None,
    limit: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get conversation history with pagination support"""
    if limit is None:
        limit = get_app_settings().messages_pagination_limit
    try:
        messages = await chat_service.get_conversation_messages(
            project_id, db, before_id=before_id, since_id=since_id, limit=limit
        )
    except ValueError as e:
        raise map_value_error(e, default_status=404) from e
    return {"messages": messages}


@router.patch("/projects/{project_id}/adrs/{adr_id}/append", response_model=StateResponse)
async def append_to_adr(
    project_id: str,
    adr_id: str,
    request: AdrAppendRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Human-authored edit: append text to an ADR field.

    This is used by E2E validation to simulate an authoritative human edit
    (US7) so the agent merge rules can surface conflicts instead of overwriting.
    """
    state = await project_state_edit_service.append_to_adr(
        project_id=project_id,
        adr_id=adr_id,
        adr_field=request.adr_field,
        append_text=request.append_text,
        db=db,
    )
    return {"projectState": state}


# ============================================================================
# Architecture Proposal Endpoint (SSE)
# ============================================================================


@router.get("/projects/{project_id}/architecture/proposal")
async def generate_proposal(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    """Generate architecture proposal with Server-Sent Events for progress"""

    return StreamingResponse(
        stream_architecture_proposal(
            document_service=document_service,
            project_id=project_id,
            db=db,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
