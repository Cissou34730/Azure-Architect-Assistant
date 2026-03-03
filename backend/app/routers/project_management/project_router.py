"""
FastAPI Router for Project Management Endpoints
Clean routing layer - business logic delegated to operations.py
"""

import logging
import mimetypes
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProjectDocument
from app.projects_database import get_db
from app.services.project.chat_service import ChatService
from app.services.project.document_service import DocumentService
from app.services.project.project_service import ProjectService
from app.services.project.proposal_stream_service import stream_architecture_proposal
from app.services.project.state_edit_service import ProjectStateEditService
from app.services.diagram.project_diagram_helpers import (
    append_diagram_reference_to_project_state,
    ensure_initial_c4_context_diagram,
)

from .project_models import (
    BulkDeleteProjectsRequest,
    ChatMessageRequest,
    ChatResponse,
    CreateProjectRequest,
    DeleteResponse,
    DocumentsResponse,
    MessagesResponse,
    ProjectResponse,
    ProjectsListResponse,
    StateResponse,
    UpdateRequirementsRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["projects"])
project_service = ProjectService()
document_service = DocumentService()
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
        return {"project": project}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to create project: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create project: {e!s}"
        ) from e


@router.get("/projects", response_model=ProjectsListResponse)
async def list_projects(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """List all projects"""
    try:
        projects = await project_service.list_projects(db)
        return {"projects": projects}
    except Exception as e:
        logger.error(f"Failed to list projects: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to list projects: {e!s}"
        ) from e


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Get project details"""
    try:
        project = await project_service.get_project(project_id, db)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"project": project}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get project: {e!s}") from e


@router.put("/projects/{project_id}/requirements", response_model=ProjectResponse)
async def update_requirements(
    project_id: str,
    request: UpdateRequirementsRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update project requirements"""
    try:
        project = await project_service.update_requirements(project_id, request, db)
        return {"project": project}
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 400, detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Failed to update requirements: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to update requirements: {e!s}"
        ) from e


@router.delete("/projects/{project_id}", response_model=DeleteResponse)
async def delete_project(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Soft delete a project (sets deleted_at timestamp)"""
    try:
        await project_service.soft_delete_project(project_id, db)
        return {
            "message": "Project deleted successfully",
            "deletedCount": 1,
            "projectIds": [project_id],
        }
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 400, detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Failed to delete project: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to delete project: {e!s}"
        ) from e


@router.post("/projects/bulk-delete", response_model=DeleteResponse)
async def bulk_delete_projects(
    request: BulkDeleteProjectsRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Bulk soft delete multiple projects"""
    try:
        result = await project_service.bulk_soft_delete_projects(
            request.project_ids, db
        )
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
    except Exception as e:
        logger.error(f"Failed to bulk delete projects: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to bulk delete projects: {e!s}"
        ) from e


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
    try:
        selected_files = documents or files
        if not selected_files:
            raise HTTPException(status_code=400, detail="No files uploaded")

        upload_result = await document_service.upload_documents(
            project_id, selected_files, db
        )
        return {
            "documents": upload_result.get("documents", []),
            "uploadSummary": upload_result.get("uploadSummary", {}),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 400, detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Failed to upload documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to upload documents: {e!s}"
        ) from e


@router.get("/projects/{project_id}/documents/{document_id}/content")
async def get_document_content(
    project_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    result = await db.execute(
        select(ProjectDocument).where(
            ProjectDocument.id == document_id,
            ProjectDocument.project_id == project_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    stored_path = (document.stored_path or "").strip()
    if stored_path == "":
        raise HTTPException(status_code=404, detail="Document content unavailable")

    resolved_path = Path(stored_path)
    if not resolved_path.is_file():
        raise HTTPException(status_code=404, detail="Document file missing")

    media_type = (document.mime_type or "").strip()
    if media_type == "" or media_type == "application/octet-stream":
        guessed_media_type, _ = mimetypes.guess_type(document.file_name or "")
        if guessed_media_type:
            media_type = guessed_media_type
    if media_type == "":
        media_type = "application/octet-stream"

    return FileResponse(
        path=resolved_path,
        media_type=media_type,
        filename=document.file_name,
        content_disposition_type="inline",
    )


@router.post("/projects/{project_id}/analyze-docs", response_model=StateResponse)
async def analyze_documents(project_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Analyze documents and generate initial ProjectState"""
    try:
        state = await document_service.analyze_documents(project_id, db)

        # US1/T016: Generate/store initial C4 Level 1 diagram link via existing diagram flow.
        try:
            diagram_ref = await ensure_initial_c4_context_diagram(project_id, state)
            if diagram_ref is not None:
                state = await append_diagram_reference_to_project_state(
                    project_id, state, diagram_ref, db
                )
        except Exception:
            # Best-effort: do not block requirement extraction if diagram generation
            # fails due to missing credentials/timeouts.
            logger.exception(
                "C4 context diagram generation skipped for project %s",
                project_id,
            )

        return {"projectState": state}
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 400, detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Failed to analyze documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze documents: {e!s}"
        ) from e



# ============================================================================
# Chat & State Management Endpoints
# ============================================================================


@router.post("/projects/{project_id}/chat", response_model=ChatResponse)
async def chat_message(
    project_id: str, request: ChatMessageRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Legacy endpoint (disabled).

    The application uses the LangGraph agent chat endpoint:
      POST /api/agent/projects/{project_id}/chat
    """
    raise HTTPException(
        status_code=410,
        detail=(
            "Project chat endpoint is disabled. Use POST /api/agent/projects/{project_id}/chat "
            "(LangGraph) instead."
        ),
    )


@router.get("/projects/{project_id}/state", response_model=StateResponse)
async def get_project_state(project_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Get current project state"""
    try:
        state = await chat_service.get_project_state(project_id, db)
        return {"projectState": state}
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 400, detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Failed to get project state: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get project state: {e!s}"
        ) from e


@router.get("/projects/{project_id}/messages", response_model=MessagesResponse)
async def get_messages(
    project_id: str,
    before_id: str | None = None,
    since_id: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get conversation history with pagination support"""
    try:
        messages = await chat_service.get_conversation_messages(
            project_id, db, before_id=before_id, since_id=since_id, limit=limit
        )
        return {"messages": messages}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to get messages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {e!s}") from e


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
    try:
        state = await project_state_edit_service.append_to_adr(
            project_id=project_id,
            adr_id=adr_id,
            adr_field=request.adr_field,
            append_text=request.append_text,
            db=db,
        )
        return {"projectState": state}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to append to ADR: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to append to ADR: {e!s}"
        ) from e


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

