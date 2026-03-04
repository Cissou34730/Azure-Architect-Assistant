"""
FastAPI Router for Project State, Chat & Proposal Endpoints
Handles project state retrieval, conversation history, ADR edits, and proposal streaming.
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.app_settings import get_app_settings
from app.projects_database import get_db
from app.routers.error_utils import map_value_error
from app.services.project.chat_service import ChatService
from app.services.project.document_service import DocumentService
from app.services.project.proposal_stream_service import stream_architecture_proposal
from app.services.project.state_edit_service import ProjectStateEditService

from ._deps import get_chat_service_dep, get_document_service_dep, get_state_edit_service_dep
from .project_models import AdrAppendRequest, MessagesResponse, StateResponse

router = APIRouter(prefix="/api", tags=["projects"])


@router.get("/projects/{project_id}/state", response_model=StateResponse)
async def get_project_state(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service_dep),
) -> dict[str, Any]:
    """Get current project state"""
    try:
        state = await chat_service.get_project_state(project_id, db)
    except ValueError as e:
        raise map_value_error(e, default_status=400) from e
    return {"projectState": state}


@router.get("/projects/{project_id}/messages", response_model=MessagesResponse)
async def get_messages(  # noqa: PLR0913
    project_id: str,
    before_id: str | None = None,
    since_id: str | None = None,
    limit: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service_dep),
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
    project_state_edit_service: ProjectStateEditService = Depends(get_state_edit_service_dep),
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


@router.get("/projects/{project_id}/architecture/proposal")
async def generate_proposal(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    document_service: DocumentService = Depends(get_document_service_dep),
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
