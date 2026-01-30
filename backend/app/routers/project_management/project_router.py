"""
FastAPI Router for Project Management Endpoints
Clean routing layer - business logic delegated to operations.py
"""

import json
import logging
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProjectState
from app.models.diagram import Diagram, DiagramSet, DiagramType
from app.projects_database import get_db
from app.services.diagram.database import get_diagram_session
from app.services.diagram.diagram_generator import DiagramGenerator
from app.services.diagram.llm_client import DiagramLLMClient

from .project_models import (
    ChatMessageRequest,
    ChatResponse,
    CreateProjectRequest,
    DocumentsResponse,
    MessagesResponse,
    ProjectResponse,
    ProjectsListResponse,
    StateResponse,
    UpdateRequirementsRequest,
)
from .services import ChatService, DocumentService, ProjectService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["projects"])
project_service = ProjectService()
document_service = DocumentService()
chat_service = ChatService()


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

        saved = await document_service.upload_documents(project_id, selected_files, db)
        return {"documents": saved}
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 400, detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Failed to upload documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to upload documents: {e!s}"
        ) from e


@router.post("/projects/{project_id}/analyze-docs", response_model=StateResponse)
async def analyze_documents(project_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Analyze documents and generate initial ProjectState"""
    try:
        state = await document_service.analyze_documents(project_id, db)

        # US1/T016: Generate/store initial C4 Level 1 diagram link via existing diagram flow.
        try:
            diagram_ref = await _ensure_initial_c4_context_diagram(project_id, state)
            if diagram_ref is not None:
                state = await _append_diagram_reference_to_project_state(
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


def _build_diagram_input_description(state: dict[str, Any]) -> str:
    context_raw = state.get("context")
    context = context_raw if isinstance(context_raw, dict) else {}
    summary = (context.get("summary") or "").strip()

    requirements_raw = state.get("requirements")
    requirements = requirements_raw if isinstance(requirements_raw, list) else []

    parts: list[str] = []
    if summary:
        parts.append(f"Project summary: {summary}")

    for category in ["business", "functional", "nfr"]:
        lines = _get_requirement_lines_by_category(requirements, category)
        if lines:
            title = f"{category.capitalize()} requirements:"
            parts.append(f"{title}\n" + "\n".join(lines))

    # Fall back to a safe minimal description to satisfy diagram generator input constraints.
    if not parts:
        parts.append(
            "Generate a C4 Context diagram for the system described by the project documents."
        )

    return "\n\n".join(parts)


def _get_requirement_lines_by_category(
    requirements: list[Any], category: str
) -> list[str]:
    """Helper to extract requirement lines for a specific category."""
    lines: list[str] = []
    for r in requirements:
        if (
            isinstance(r, dict)
            and (r.get("category") or "").strip().lower() == category
        ):
            text = (r.get("text") or "").strip()
            if text:
                lines.append(f"- {text}")
    return lines


async def _ensure_initial_c4_context_diagram(
    project_id: str, state: dict[str, Any]
) -> dict[str, Any] | None:
    """Generate a C4 Context diagram and return a reference payload.

    Uses the diagram DB + DiagramGenerator (same components as /api/v1/diagram-sets).
    """

    description = _build_diagram_input_description(state)
    llm_client = DiagramLLMClient()
    generator = DiagramGenerator(llm_client)

    async for session in get_diagram_session():
        diagram_set = DiagramSet(
            adr_id=None,
            input_description=description,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(diagram_set)
        await session.flush()

        result = await generator.generate_c4_context(description=description)
        if not result.success or not result.source_code:
            raise RuntimeError(
                f"C4 context diagram generation failed after {result.attempts} attempts: {result.error}"
            )

        diagram = Diagram(
            diagram_set_id=diagram_set.id,
            diagram_type=DiagramType.C4_CONTEXT.value,
            source_code=result.source_code,
            rendered_svg=None,
            rendered_png=None,
            version="1.0.0",
            previous_version_id=None,
            created_at=datetime.now(timezone.utc),
        )
        session.add(diagram)
        await session.flush()

        # get_diagram_session() will commit for us after yielding.
        return {
            "id": diagram.id,
            "type": "c4_context",
            "source": diagram.source_code,
            "version": diagram.version,
            "diagramSetId": diagram_set.id,
            "url": f"/api/v1/diagram-sets/{diagram_set.id}",
            "updatedAt": diagram.created_at.isoformat(),
        }

    return None


async def _append_diagram_reference_to_project_state(
    project_id: str,
    state: dict[str, Any],
    diagram_ref: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """Persist a diagram reference into ProjectState.state and return updated state."""

    result = await db.execute(
        select(ProjectState).where(ProjectState.project_id == project_id)
    )
    state_record = result.scalar_one_or_none()
    if not state_record:
        # Should not happen (analyze-docs just created it), but be defensive.
        state_record = ProjectState(
            project_id=project_id,
            state=json.dumps(state),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        db.add(state_record)
        await db.flush()

    persisted = json.loads(state_record.state)
    diagrams = persisted.get("diagrams")
    if not isinstance(diagrams, list):
        diagrams = []

    # Do not duplicate if already present
    if not any(isinstance(d, dict) and d.get("id") == diagram_ref.get("id") for d in diagrams):
        diagrams.append(diagram_ref)

    persisted["diagrams"] = diagrams
    state_record.state = json.dumps(persisted)
    state_record.updated_at = datetime.now(timezone.utc).isoformat()
    await db.commit()

    # Return merged view
    updated = dict(state)
    updated["diagrams"] = diagrams
    return updated


# ============================================================================
# Chat & State Management Endpoints
# ============================================================================


@router.post("/projects/{project_id}/chat", response_model=ChatResponse)
async def chat_message(
    project_id: str, request: ChatMessageRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Send a chat message and get response with updated state"""
    try:
        result = await chat_service.process_chat_message(
            project_id, request.message, db
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 400, detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Failed to process chat message: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to process chat message: {e!s}"
        ) from e


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
        field = (request.adr_field or "").strip()
        if field not in {"context", "decision", "consequences", "title"}:
            raise HTTPException(status_code=400, detail=f"Unsupported adrField: {field}")

        result = await db.execute(
            select(ProjectState).where(ProjectState.project_id == project_id)
        )
        state_record = result.scalar_one_or_none()
        if not state_record:
            raise HTTPException(status_code=404, detail="Project state not found")

        state = json.loads(state_record.state)
        adrs = state.get("adrs")
        if not isinstance(adrs, list):
            raise HTTPException(status_code=400, detail="No ADRs present in state")

        target = None
        for adr in adrs:
            if isinstance(adr, dict) and str(adr.get("id")) == adr_id:
                target = adr
                break
        if target is None:
            raise HTTPException(status_code=404, detail="ADR not found")

        append_text = (request.append_text or "").strip()
        if not append_text:
            raise HTTPException(status_code=400, detail="appendText is required")

        existing_val = str(target.get(field) or "").rstrip()
        new_val = (existing_val + "\n" if existing_val else "") + append_text
        target[field] = new_val

        state_record.state = json.dumps(state)
        state_record.updated_at = datetime.now(timezone.utc).isoformat()
        await db.commit()

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

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events"""

        def send_progress(stage: str, detail: str | None = None) -> str:
            data = {
                "stage": stage,
                "detail": detail,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            return f"data: {json.dumps(data)}\n\n"

        yield send_progress("started", "Initializing proposal generation")

        try:
            # Track progress events
            progress_events: list[tuple[str, str | None]] = []

            def on_progress(stage: str, detail: str | None = None) -> None:
                progress_events.append((stage, detail))

            # Generate proposal
            proposal = await document_service.generate_proposal(
                project_id, db, on_progress
            )

            # Send accumulated progress
            for stage, detail in progress_events:
                yield send_progress(stage, detail)

            yield send_progress("completed", "Proposal generated successfully")

            # Send final result
            final_data = {
                "stage": "done",
                "proposal": proposal,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            yield f"data: {json.dumps(final_data)}\n\n"

        except ValueError as e:
            logger.error(f"Proposal generation failed: {e}")
            error_data = {
                "stage": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            yield f"data: {json.dumps(error_data)}\n\n"
        except Exception as e:
            logger.error(f"Proposal generation failed: {e}", exc_info=True)
            error_data = {
                "stage": "error",
                "error": f"Internal server error: {e!s}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )

