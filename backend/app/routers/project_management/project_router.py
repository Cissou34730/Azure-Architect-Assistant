"""
FastAPI Router for Project Management Endpoints
Clean routing layer - business logic delegated to operations.py
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional
import json
import logging
from datetime import datetime, timezone

from app.projects_database import get_db
from app.models import ProjectState

from app.services.diagram.database import get_diagram_session
from app.services.diagram.diagram_generator import DiagramGenerator
from app.services.diagram.llm_client import DiagramLLMClient
from app.models.diagram import Diagram, DiagramSet, DiagramType

from .project_models import (
    CreateProjectRequest,
    UpdateRequirementsRequest,
    ChatMessageRequest,
    ProjectResponse,
    ProjectsListResponse,
    DocumentsResponse,
    StateResponse,
    MessagesResponse,
    ChatResponse,
)
from .services import ProjectService, DocumentService, ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["projects"])
project_service = ProjectService()
document_service = DocumentService()
chat_service = ChatService()


# ============================================================================
# Project CRUD Endpoints
# ============================================================================


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest, db: AsyncSession = Depends(get_db)
):
    """Create a new project"""
    try:
        project = await project_service.create_project(request, db)
        return {"project": project}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create project: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create project: {str(e)}"
        )


@router.get("/projects", response_model=ProjectsListResponse)
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all projects"""
    try:
        projects = await project_service.list_projects(db)
        return {"projects": projects}
    except Exception as e:
        logger.error(f"Failed to list projects: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to list projects: {str(e)}"
        )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
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
        raise HTTPException(status_code=500, detail=f"Failed to get project: {str(e)}")


@router.put("/projects/{project_id}/requirements", response_model=ProjectResponse)
async def update_requirements(
    project_id: str,
    request: UpdateRequirementsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update project requirements"""
    try:
        project = await project_service.update_requirements(project_id, request, db)
        return {"project": project}
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 400, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update requirements: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to update requirements: {str(e)}"
        )


# ============================================================================
# Document Management Endpoints
# ============================================================================


@router.post("/projects/{project_id}/documents", response_model=DocumentsResponse)
async def upload_documents(
    project_id: str,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload documents for a project"""
    try:
        documents = await document_service.upload_documents(project_id, files, db)
        return {"documents": documents}
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 400, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to upload documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to upload documents: {str(e)}"
        )


@router.post("/projects/{project_id}/analyze-docs", response_model=StateResponse)
async def analyze_documents(project_id: str, db: AsyncSession = Depends(get_db)):
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
        except Exception as exc:
            # Best-effort: do not block requirement extraction if diagram generation
            # fails due to missing credentials/timeouts.
            logger.warning(
                "C4 context diagram generation skipped for project %s (%s)",
                project_id,
                exc,
            )

        return {"projectState": state}
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 400, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to analyze documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze documents: {str(e)}"
        )


def _build_diagram_input_description(state: Dict[str, Any]) -> str:
    context = state.get("context") if isinstance(state.get("context"), dict) else {}
    summary = (context.get("summary") or "").strip()

    requirements = state.get("requirements") if isinstance(state.get("requirements"), list) else []

    def _lines_for(category: str) -> List[str]:
        lines: List[str] = []
        for r in requirements:
            if not isinstance(r, dict):
                continue
            if (r.get("category") or "").strip().lower() != category:
                continue
            text = (r.get("text") or "").strip()
            if text:
                lines.append(f"- {text}")
        return lines

    parts: List[str] = []
    if summary:
        parts.append(f"Project summary: {summary}")

    business = _lines_for("business")
    functional = _lines_for("functional")
    nfr = _lines_for("nfr")

    if business:
        parts.append("Business requirements:\n" + "\n".join(business))
    if functional:
        parts.append("Functional requirements:\n" + "\n".join(functional))
    if nfr:
        parts.append("Non-functional requirements:\n" + "\n".join(nfr))

    # Fall back to a safe minimal description to satisfy diagram generator input constraints.
    if not parts:
        parts.append("Generate a C4 Context diagram for the system described by the project documents.")

    return "\n\n".join(parts)


async def _ensure_initial_c4_context_diagram(
    project_id: str, state: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
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
    state: Dict[str, Any],
    diagram_ref: Dict[str, Any],
    db: AsyncSession,
) -> Dict[str, Any]:
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
):
    """Send a chat message and get response with updated state"""
    try:
        result = await chat_service.process_chat_message(
            project_id, request.message, db
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 400, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to process chat message: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to process chat message: {str(e)}"
        )


@router.get("/projects/{project_id}/state", response_model=StateResponse)
async def get_project_state(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get current project state"""
    try:
        state = await chat_service.get_project_state(project_id, db)
        return {"projectState": state}
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 400, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get project state: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get project state: {str(e)}"
        )


@router.get("/projects/{project_id}/messages", response_model=MessagesResponse)
async def get_messages(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get conversation history"""
    try:
        messages = await chat_service.get_conversation_messages(project_id, db)
        return {"messages": messages}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get messages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")


# ============================================================================
# Architecture Proposal Endpoint (SSE)
# ============================================================================


@router.get("/projects/{project_id}/architecture/proposal")
async def generate_proposal(project_id: str, db: AsyncSession = Depends(get_db)):
    """Generate architecture proposal with Server-Sent Events for progress"""

    async def event_generator():
        """Generate SSE events"""

        def send_progress(stage: str, detail: Optional[str] = None):
            data = {
                "stage": stage,
                "detail": detail,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            return f"data: {json.dumps(data)}\n\n"

        yield send_progress("started", "Initializing proposal generation")

        try:
            # Track progress events
            progress_events = []

            def on_progress(stage: str, detail: Optional[str] = None):
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
                "error": f"Internal server error: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
