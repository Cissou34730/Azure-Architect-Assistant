"""
Projects Router - Main project workflow endpoints.
Migrated from TypeScript backend.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import json
import logging
from datetime import datetime
import uuid

from app.database import get_db
from app.models import Project, ProjectDocument, ProjectState, ConversationMessage
from app.llm_service import get_llm_service
from app.kb.multi_query import MultiSourceQueryService, QueryProfile
from app.services import get_multi_query_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["projects"])


# Pydantic models for requests/responses
class CreateProjectRequest(BaseModel):
    name: str


class UpdateRequirementsRequest(BaseModel):
    textRequirements: str


class ChatMessageRequest(BaseModel):
    message: str


class ProjectResponse(BaseModel):
    project: Dict[str, Any]


class ProjectsListResponse(BaseModel):
    projects: List[Dict[str, Any]]


class DocumentsResponse(BaseModel):
    documents: List[Dict[str, Any]]


class StateResponse(BaseModel):
    projectState: Dict[str, Any]


class MessagesResponse(BaseModel):
    messages: List[Dict[str, Any]]


class ChatResponse(BaseModel):
    message: str
    projectState: Dict[str, Any]
    wafSources: List[Dict[str, Any]] = []


# Endpoints

@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new project."""
    if not request.name or not request.name.strip():
        raise HTTPException(status_code=400, detail="Project name is required")
    
    project = Project(
        id=str(uuid.uuid4()),
        name=request.name.strip(),
        created_at=datetime.utcnow().isoformat()
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    logger.info(f"Project created: {project.id} - {project.name}")
    return {"project": project.to_dict()}


@router.get("/projects", response_model=ProjectsListResponse)
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all projects."""
    result = await db.execute(select(Project))
    projects = result.scalars().all()
    
    logger.info(f"Listing {len(projects)} projects")
    return {"projects": [p.to_dict() for p in projects]}


@router.put("/projects/{project_id}/requirements", response_model=ProjectResponse)
async def update_requirements(
    project_id: str,
    request: UpdateRequirementsRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update project text requirements."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.text_requirements = request.textRequirements.strip() if request.textRequirements else None
    await db.commit()
    await db.refresh(project)
    
    logger.info(f"Updated requirements for project: {project_id}")
    return {"project": project.to_dict()}


@router.post("/projects/{project_id}/documents", response_model=DocumentsResponse)
async def upload_documents(
    project_id: str,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload documents to a project."""
    # Check project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    documents = []
    
    for file in files:
        # Read file content
        content = await file.read()
        
        # Extract text based on MIME type
        if file.content_type and file.content_type.startswith("text/"):
            raw_text = content.decode("utf-8")
        elif file.content_type == "application/pdf":
            raw_text = f"[PDF Document: {file.filename}]\n[Text extraction not implemented in POC - placeholder content]"
        elif file.content_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword"
        ]:
            raw_text = f"[Word Document: {file.filename}]\n[Text extraction not implemented in POC - placeholder content]"
        else:
            raw_text = f"[File: {file.filename}]\n[Unsupported file type for text extraction]"
        
        document = ProjectDocument(
            id=str(uuid.uuid4()),
            project_id=project_id,
            file_name=file.filename or "unknown",
            mime_type=file.content_type or "application/octet-stream",
            raw_text=raw_text,
            uploaded_at=datetime.utcnow().isoformat()
        )
        
        db.add(document)
        documents.append(document)
    
    await db.commit()
    
    logger.info(f"Uploaded {len(documents)} documents to project: {project_id}")
    return {"documents": [d.to_dict() for d in documents]}


@router.post("/projects/{project_id}/analyze-docs", response_model=StateResponse)
async def analyze_documents(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Analyze documents and generate initial ProjectState."""
    # Get project
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get documents
    result = await db.execute(
        select(ProjectDocument).where(ProjectDocument.project_id == project_id)
    )
    documents = result.scalars().all()
    
    # Collect text sources
    document_texts = [doc.raw_text for doc in documents]
    if project.text_requirements:
        document_texts.append(project.text_requirements)
    
    if not document_texts:
        raise HTTPException(
            status_code=400,
            detail="No documents or text requirements to analyze"
        )
    
    logger.info(f"Analyzing {len(document_texts)} documents for project: {project_id}")
    
    # Analyze with LLM
    llm_service = get_llm_service()
    state_data = await llm_service.analyze_documents(document_texts)
    
    # Save state
    state_json = json.dumps(state_data)
    
    # Check if state exists
    result = await db.execute(
        select(ProjectState).where(ProjectState.project_id == project_id)
    )
    existing_state = result.scalar_one_or_none()
    
    if existing_state:
        existing_state.state = state_json
        existing_state.updated_at = datetime.utcnow().isoformat()
    else:
        new_state = ProjectState(
            project_id=project_id,
            state=state_json,
            updated_at=datetime.utcnow().isoformat()
        )
        db.add(new_state)
    
    await db.commit()
    
    # Return state with metadata
    state_data["projectId"] = project_id
    state_data["lastUpdated"] = datetime.utcnow().isoformat()
    
    logger.info(f"Document analysis completed for project: {project_id}")
    return {"projectState": state_data}


@router.post("/projects/{project_id}/chat", response_model=ChatResponse)
async def chat_message(
    project_id: str,
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send a chat message and get response with updated state."""
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")
    
    # Get project
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get current state
    result = await db.execute(
        select(ProjectState).where(ProjectState.project_id == project_id)
    )
    state_record = result.scalar_one_or_none()
    
    if not state_record:
        raise HTTPException(
            status_code=400,
            detail="Project state not initialized. Please analyze documents first."
        )
    
    current_state = json.loads(state_record.state)
    
    # Save user message
    user_message = ConversationMessage(
        id=str(uuid.uuid4()),
        project_id=project_id,
        role="user",
        content=request.message,
        timestamp=datetime.utcnow().isoformat()
    )
    db.add(user_message)
    await db.commit()
    
    # Get recent messages
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.project_id == project_id)
        .order_by(ConversationMessage.timestamp.desc())
        .limit(10)
    )
    recent_messages = list(reversed(result.scalars().all()))
    recent_message_dicts = [msg.to_dict() for msg in recent_messages]
    
    logger.info(f"Processing chat for project: {project_id}")
    
    # Check if architecture-related (simple keyword detection)
    is_architecture_related = any(
        keyword in request.message.lower()
        for keyword in ["azure", "architecture", "service", "security", "availability", "performance"]
    )
    
    # Query KB if architecture-related
    kb_sources = []
    if is_architecture_related:
        logger.info("Architecture question detected, querying KB")
        try:
            multi_query_service = get_multi_query_service()
            kb_result = multi_query_service.query_profile(
                question=request.message,
                profile=QueryProfile.CHAT,
                top_k_per_kb=3
            )
            if kb_result.get('has_results'):
                kb_sources = kb_result.get('sources', [])
        except Exception as e:
            logger.error(f"KB query failed: {e}")
    
    # Process with LLM
    llm_service = get_llm_service()
    response = await llm_service.process_chat_message(
        request.message,
        current_state,
        recent_message_dicts,
        kb_sources if kb_sources else None
    )
    
    # Save assistant message
    assistant_message = ConversationMessage(
        id=str(uuid.uuid4()),
        project_id=project_id,
        role="assistant",
        content=response['assistantMessage'],
        timestamp=datetime.utcnow().isoformat(),
        waf_sources=json.dumps(response.get('sources', [])) if response.get('sources') else None
    )
    db.add(assistant_message)
    
    # Update project state
    state_record.state = json.dumps(response['projectState'])
    state_record.updated_at = datetime.utcnow().isoformat()
    
    await db.commit()
    
    logger.info(f"Chat response generated for project: {project_id}")
    
    return {
        "message": response['assistantMessage'],
        "projectState": response['projectState'],
        "wafSources": response.get('sources', [])
    }


@router.get("/projects/{project_id}/state", response_model=StateResponse)
async def get_project_state(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get current project state."""
    # Check project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get state
    result = await db.execute(
        select(ProjectState).where(ProjectState.project_id == project_id)
    )
    state_record = result.scalar_one_or_none()
    
    if not state_record:
        raise HTTPException(status_code=404, detail="Project state not initialized")
    
    logger.info(f"Returning state for project: {project_id}")
    return {"projectState": state_record.to_dict()}


@router.get("/projects/{project_id}/architecture/proposal")
async def generate_proposal(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Generate architecture proposal with Server-Sent Events for progress."""
    # Get project
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get state
    result = await db.execute(
        select(ProjectState).where(ProjectState.project_id == project_id)
    )
    state_record = result.scalar_one_or_none()
    
    if not state_record:
        raise HTTPException(
            status_code=400,
            detail="Project state not initialized. Please analyze documents first."
        )
    
    state = json.loads(state_record.state)
    
    async def event_generator():
        """Generate SSE events."""
        def send_progress(stage: str, detail: Optional[str] = None):
            data = {
                "stage": stage,
                "detail": detail,
                "timestamp": datetime.utcnow().isoformat()
            }
            return f"data: {json.dumps(data)}\n\n"
        
        yield send_progress("started", "Initializing proposal generation")
        
        try:
            llm_service = get_llm_service()
            
            # Create progress callback
            progress_events = []
            
            def on_progress(stage: str, detail: Optional[str] = None):
                progress_events.append((stage, detail))
            
            # Generate proposal
            proposal = await llm_service.generate_architecture_proposal(state, on_progress)
            
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
            
        except Exception as e:
            logger.error(f"Proposal generation failed: {e}")
            error_data = {
                "stage": "error",
                "error": str(e),
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


@router.get("/projects/{project_id}/messages", response_model=MessagesResponse)
async def get_messages(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get conversation history."""
    # Check project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get messages
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.project_id == project_id)
        .order_by(ConversationMessage.timestamp.asc())
    )
    messages = result.scalars().all()
    
    logger.info(f"Returning {len(messages)} messages for project: {project_id}")
    return {"messages": [msg.to_dict() for msg in messages]}
