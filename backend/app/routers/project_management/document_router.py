"""
FastAPI Router for Project Document Endpoints
Handles document upload, retrieval, and analysis.
"""

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.projects_database import get_db
from app.routers.error_utils import map_value_error
from app.services.project.document_content_service import DocumentContentService
from app.services.project.document_service import DocumentService
from app.services.project.project_analysis_service import ProjectAnalysisService

from ._deps import (
    get_document_content_service_dep,
    get_document_service_dep,
    get_project_analysis_service_dep,
)
from .project_models import DocumentsResponse, StateResponse

router = APIRouter(prefix="/api", tags=["projects"])


@router.post("/projects/{project_id}/documents", response_model=DocumentsResponse)
async def upload_documents(
    project_id: str,
    # Frontend sends "documents"; keep backward-compatible support for "files".
    documents: list[UploadFile] | None = File(default=None),
    files: list[UploadFile] | None = File(default=None),
    db: AsyncSession = Depends(get_db),
    document_service: DocumentService = Depends(get_document_service_dep),
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


@router.get(
    "/projects/{project_id}/documents/{document_id}/content",
    response_class=FileResponse,
)
async def get_document_content(
    project_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    document_content_service: DocumentContentService = Depends(get_document_content_service_dep),
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
async def analyze_documents(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    project_analysis_service: ProjectAnalysisService = Depends(get_project_analysis_service_dep),
) -> dict[str, Any]:
    """Analyze documents and generate initial ProjectState"""
    try:
        state = await project_analysis_service.analyze_documents_with_bootstrap(
            project_id=project_id,
            db=db,
        )
    except ValueError as e:
        raise map_value_error(e, default_status=400) from e
    return {"projectState": state}
