"""
FastAPI Router for Project Management Endpoints
Clean routing layer - business logic delegated to operations.py
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import json
import logging
from datetime import datetime

from app.projects_database import get_db

from .project_models import (
    CreateProjectRequest,
    UpdateRequirementsRequest,
    ChatMessageRequest,
    ProjectResponse,
    ProjectsListResponse,
    DocumentsResponse,
    StateResponse,
    MessagesResponse,
    ChatResponse
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
    request: CreateProjectRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new project"""
    try:
        project = await project_service.create_project(request, db)
        return {"project": project}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.get("/projects", response_model=ProjectsListResponse)
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all projects"""
    try:
        projects = await project_service.list_projects(db)
        return {"projects": projects}
    except Exception as e:
        logger.error(f"Failed to list projects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")


@router.put("/projects/{project_id}/requirements", response_model=ProjectResponse)
async def update_requirements(
    project_id: str,
    request: UpdateRequirementsRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update project requirements"""
    try:
        project = await project_service.update_requirements(project_id, request, db)
        return {"project": project}
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e).lower() else 400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update requirements: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update requirements: {str(e)}")


# ============================================================================
# Document Management Endpoints
# ============================================================================

@router.post("/projects/{project_id}/documents", response_model=DocumentsResponse)
async def upload_documents(
    project_id: str,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload documents for a project"""
    try:
        documents = await document_service.upload_documents(project_id, files, db)
        return {"documents": documents}
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e).lower() else 400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to upload documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload documents: {str(e)}")


@router.post("/projects/{project_id}/analyze-docs", response_model=StateResponse)
async def analyze_documents(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Analyze documents and generate initial ProjectState"""
    try:
        state = await document_service.analyze_documents(project_id, db)
        return {"projectState": state}
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e).lower() else 400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to analyze documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze documents: {str(e)}")


# ============================================================================
# Chat & State Management Endpoints
# ============================================================================

@router.post("/projects/{project_id}/chat", response_model=ChatResponse)
async def chat_message(
    project_id: str,
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send a chat message and get response with updated state"""
    try:
        result = await chat_service.process_chat_message(project_id, request.message, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e).lower() else 400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to process chat message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process chat message: {str(e)}")


@router.get("/projects/{project_id}/state", response_model=StateResponse)
async def get_project_state(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get current project state"""
    try:
        state = await chat_service.get_project_state(project_id, db)
        return {"projectState": state}
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e).lower() else 400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get project state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get project state: {str(e)}")


@router.get("/projects/{project_id}/messages", response_model=MessagesResponse)
async def get_messages(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
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
async def generate_proposal(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Generate architecture proposal with Server-Sent Events for progress"""
    
    async def event_generator():
        """Generate SSE events"""
        def send_progress(stage: str, detail: Optional[str] = None):
            data = {
                "stage": stage,
                "detail": detail,
                "timestamp": datetime.utcnow().isoformat()
            }
            return f"data: {json.dumps(data)}\n\n"
        
        yield send_progress("started", "Initializing proposal generation")
        
        try:
            # Track progress events
            progress_events = []
            
            def on_progress(stage: str, detail: Optional[str] = None):
                progress_events.append((stage, detail))
            
            # Generate proposal
            proposal = await document_service.generate_proposal(project_id, db, on_progress)
            
            # Send accumulated progress
            for stage, detail in progress_events:
                yield send_progress(stage, detail)
            
            yield send_progress("completed", "Proposal generated successfully")
            
            # Send final result
            final_data = {
                "stage": "done",
                "proposal": proposal,
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(final_data)}\n\n"
            
        except ValueError as e:
            logger.error(f"Proposal generation failed: {e}")
            error_data = {
                "stage": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(error_data)}\n\n"
        except Exception as e:
            logger.error(f"Proposal generation failed: {e}", exc_info=True)
            error_data = {
                "stage": "error",
                "error": f"Internal server error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )
