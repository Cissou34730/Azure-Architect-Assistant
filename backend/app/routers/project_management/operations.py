"""
Business Logic for Project Management Operations
Separated from routing layer for better maintainability
"""

import logging
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models import Project, ProjectDocument, ProjectState, ConversationMessage
from app.services.llm_service import get_llm_service
from app.kb.multi_query import QueryProfile
from app.service_registry import get_multi_query_service

from .models import CreateProjectRequest, UpdateRequirementsRequest, ChatMessageRequest

logger = logging.getLogger(__name__)


class ProjectService:
    """Service layer for project management operations"""
    
    @staticmethod
    async def create_project(request: CreateProjectRequest, db: AsyncSession) -> Dict[str, Any]:
        """
        Create a new project.
        
        Args:
            request: Project creation request
            db: Database session
            
        Returns:
            Dict with project data
            
        Raises:
            ValueError: If validation fails
        """
        if not request.name or not request.name.strip():
            raise ValueError("Project name is required")
        
        project = Project(
            id=str(uuid.uuid4()),
            name=request.name.strip(),
            created_at=datetime.utcnow().isoformat()
        )
        
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        logger.info(f"Project created: {project.id} - {project.name}")
        return project.to_dict()
    
    @staticmethod
    async def list_projects(db: AsyncSession) -> List[Dict[str, Any]]:
        """List all projects"""
        result = await db.execute(select(Project))
        projects = result.scalars().all()
        
        logger.info(f"Listing {len(projects)} projects")
        return [p.to_dict() for p in projects]
    
    @staticmethod
    async def update_requirements(
        project_id: str,
        request: UpdateRequirementsRequest,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Update project requirements"""
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise ValueError("Project not found")
        
        project.text_requirements = request.textRequirements
        await db.commit()
        await db.refresh(project)
        
        logger.info(f"Requirements updated for project: {project_id}")
        return project.to_dict()
    
    @staticmethod
    async def upload_documents(
        project_id: str,
        files: List[Any],
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Upload and process project documents"""
        # Verify project exists
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise ValueError("Project not found")
        
        saved_docs = []
        llm_service = get_llm_service()
        
        for file in files:
            content = await file.read()
            try:
                content_str = content.decode('utf-8')
            except UnicodeDecodeError:
                logger.warning(f"Skipping non-text file: {file.filename}")
                continue
            
            # Extract structured content
            doc_summary = await llm_service.extract_document_content(content_str)
            
            # Save document
            doc = ProjectDocument(
                id=str(uuid.uuid4()),
                project_id=project_id,
                filename=file.filename,
                raw_text=content_str,
                extracted_summary=json.dumps(doc_summary),
                uploaded_at=datetime.utcnow().isoformat()
            )
            
            db.add(doc)
            saved_docs.append(doc)
        
        await db.commit()
        
        logger.info(f"Uploaded {len(saved_docs)} documents for project: {project_id}")
        return [doc.to_dict() for doc in saved_docs]
    
    @staticmethod
    async def analyze_documents(project_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Analyze documents and generate initial ProjectState"""
        # Get project
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise ValueError("Project not found")
        
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
            raise ValueError("No documents or text requirements to analyze")
        
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
        return state_data
    
    @staticmethod
    async def process_chat_message(
        project_id: str,
        request: ChatMessageRequest,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Process a chat message and update project state"""
        if not request.message or not request.message.strip():
            raise ValueError("Message is required")
        
        # Get project
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise ValueError("Project not found")
        
        # Get current state
        result = await db.execute(
            select(ProjectState).where(ProjectState.project_id == project_id)
        )
        state_record = result.scalar_one_or_none()
        
        if not state_record:
            raise ValueError("Project state not initialized. Please analyze documents first.")
        
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
        
        # Check if architecture-related
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
    
    @staticmethod
    async def get_project_state(project_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Get current project state"""
        # Check project exists
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise ValueError("Project not found")
        
        # Get state
        result = await db.execute(
            select(ProjectState).where(ProjectState.project_id == project_id)
        )
        state_record = result.scalar_one_or_none()
        
        if not state_record:
            raise ValueError("Project state not found. Please analyze documents first.")
        
        state_data = json.loads(state_record.state)
        state_data["projectId"] = project_id
        state_data["lastUpdated"] = state_record.updated_at
        
        return state_data
    
    @staticmethod
    async def get_conversation_messages(project_id: str, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get all conversation messages for a project"""
        # Check project exists
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise ValueError("Project not found")
        
        # Get messages
        result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.project_id == project_id)
            .order_by(ConversationMessage.timestamp.asc())
        )
        messages = result.scalars().all()
        
        return [msg.to_dict() for msg in messages]
    
    @staticmethod
    async def generate_proposal(project_id: str, db: AsyncSession, progress_callback=None):
        """
        Generate architecture proposal for a project.
        
        Args:
            project_id: Project ID
            db: Database session
            progress_callback: Optional callback for progress updates (stage, detail)
            
        Returns:
            Proposal data
            
        Raises:
            ValueError: If project/state not found
        """
        # Get project
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise ValueError("Project not found")
        
        # Get state
        result = await db.execute(
            select(ProjectState).where(ProjectState.project_id == project_id)
        )
        state_record = result.scalar_one_or_none()
        
        if not state_record:
            raise ValueError("Project state not initialized. Please analyze documents first.")
        
        state = json.loads(state_record.state)
        
        # Generate proposal with progress tracking
        llm_service = get_llm_service()
        proposal = await llm_service.generate_architecture_proposal(state, progress_callback)
        
        return proposal


# Singleton instance
_project_service = None


def get_project_service() -> ProjectService:
    """Get singleton project service instance"""
    global _project_service
    if _project_service is None:
        _project_service = ProjectService()
    return _project_service
