"""Project document endpoints owned by the projects feature."""

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.projects.application.document_content_service import DocumentContentService
from app.features.projects.application.document_service import DocumentService
from app.features.projects.application.project_analysis_service import ProjectAnalysisService
from app.shared.db.projects_database import get_db
from app.shared.http.error_utils import map_value_error

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
    documents: list[UploadFile] | None = File(default=None),
    files: list[UploadFile] | None = File(default=None),
    db: AsyncSession = Depends(get_db),
    document_service: DocumentService = Depends(get_document_service_dep),
) -> dict[str, Any]:
    """Upload documents for a project."""
    selected_files = documents or files
    if not selected_files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    try:
        upload_result = await document_service.upload_documents(project_id, selected_files, db)
    except ValueError as exc:
        raise map_value_error(exc, default_status=400) from exc
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
) -> Response:
    payload = await document_content_service.resolve_content(
        project_id=project_id,
        document_id=document_id,
        db=db,
    )
    if payload["kind"] == "inline":
        return Response(
            content=str(payload["content"]),
            media_type=str(payload["media_type"]),
            headers={
                "Content-Disposition": (
                    f'inline; filename="{payload["file_name"]!s}.html"'
                )
            },
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
    """Analyze documents and generate initial project state."""
    try:
        state = await project_analysis_service.analyze_documents_with_bootstrap(
            project_id=project_id,
            db=db,
        )
    except ValueError as exc:
        raise map_value_error(exc, default_status=400) from exc
    return {"projectState": state}
