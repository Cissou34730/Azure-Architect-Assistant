"""Project state and proposal endpoints owned by the projects feature."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.projects.application.chat_service import ChatService
from app.features.projects.application.document_service import DocumentService
from app.features.projects.application.proposal_stream_service import (
    stream_architecture_proposal,
)
from app.features.projects.application.state_edit_service import ProjectStateEditService
from app.features.projects.contracts.workspace import workspace_view_to_project_state
from app.shared.config.app_settings import get_app_settings
from app.shared.db.projects_database import get_db
from app.shared.http.error_utils import map_value_error

from ._deps import (
    get_chat_service_dep,
    get_document_service_dep,
    get_state_edit_service_dep,
    get_workspace_composer_dep,
)
from .project_models import AdrAppendRequest, MessagesResponse, StateResponse

router = APIRouter(prefix="/api", tags=["projects"])
_STATE_DEPRECATION_SUNSET = "2026-06-01"


@dataclass(frozen=True)
class MessageQueryParams:
    before_id: str | None = None
    since_id: str | None = None
    limit: int | None = Query(default=None)

    def resolve_limit(self) -> int:
        if self.limit is not None:
            return self.limit
        return get_app_settings().messages_pagination_limit


@router.get("/projects/{project_id}/state", response_model=StateResponse)
async def get_project_state(
    project_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
    workspace_composer=Depends(get_workspace_composer_dep),
) -> dict[str, Any]:
    """Get current project state."""
    try:
        workspace = await workspace_composer.compose(project_id=project_id, db=db)
    except ValueError as exc:
        raise map_value_error(exc, default_status=400) from exc

    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = _STATE_DEPRECATION_SUNSET
    response.headers["Link"] = (
        f'</api/projects/{project_id}/workspace>; rel="successor-version"'
    )
    return {"projectState": workspace_view_to_project_state(workspace)}


@router.get("/projects/{project_id}/messages", response_model=MessagesResponse)
async def get_messages(
    project_id: str,
    params: Annotated[MessageQueryParams, Depends()],
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service_dep),
) -> dict[str, Any]:
    """Get conversation history with pagination support."""
    try:
        messages = await chat_service.get_conversation_messages(
            project_id,
            db,
            before_id=params.before_id,
            since_id=params.since_id,
            limit=params.resolve_limit(),
        )
    except ValueError as exc:
        raise map_value_error(exc, default_status=404) from exc
    return {"messages": messages}


@router.patch("/projects/{project_id}/adrs/{adr_id}/append", response_model=StateResponse)
async def append_to_adr(
    project_id: str,
    adr_id: str,
    request: AdrAppendRequest,
    db: AsyncSession = Depends(get_db),
    project_state_edit_service: ProjectStateEditService = Depends(get_state_edit_service_dep),
) -> dict[str, Any]:
    """Append text to an ADR field."""
    state = await project_state_edit_service.append_to_adr(
        project_id=project_id,
        adr_id=adr_id,
        adr_field=request.adr_field,
        append_text=request.append_text,
        db=db,
    )
    return {"projectState": state}


@router.get("/projects/{project_id}/architecture/proposal")
async def generate_proposal(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    document_service: DocumentService = Depends(get_document_service_dep),
) -> StreamingResponse:
    """Generate an architecture proposal as server-sent events."""
    return StreamingResponse(
        stream_architecture_proposal(
            document_service=document_service,
            project_id=project_id,
            db=db,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
