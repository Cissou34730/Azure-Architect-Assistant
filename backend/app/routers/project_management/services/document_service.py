import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, ProjectDocument, ProjectState
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)


class DocumentService:
    """Handles document upload and analysis for projects."""

    async def upload_documents(
        self,
        project_id: str,
        files: List[Any],
        db: AsyncSession,
    ) -> List[Dict[str, Any]]:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        saved_docs = []
        llm_service = get_llm_service()

        for file in files:
            content = await file.read()
            try:
                content_str = content.decode("utf-8")
            except UnicodeDecodeError:
                logger.warning(f"Skipping non-text file: {file.filename}")
                continue

            doc_summary = await llm_service.extract_document_content(content_str)

            doc = ProjectDocument(
                id=str(uuid.uuid4()),
                project_id=project_id,
                filename=file.filename,
                raw_text=content_str,
                extracted_summary=json.dumps(doc_summary),
                uploaded_at=datetime.utcnow().isoformat(),
            )

            db.add(doc)
            saved_docs.append(doc)

        await db.commit()
        logger.info(f"Uploaded {len(saved_docs)} documents for project: {project_id}")
        return [doc.to_dict() for doc in saved_docs]

    async def analyze_documents(self, project_id: str, db: AsyncSession) -> Dict[str, Any]:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        result = await db.execute(select(ProjectDocument).where(ProjectDocument.project_id == project_id))
        documents = result.scalars().all()

        document_texts = [doc.raw_text for doc in documents]
        if project.text_requirements:
            document_texts.append(project.text_requirements)

        if not document_texts:
            raise ValueError("No documents or text requirements to analyze")

        logger.info(f"Analyzing {len(document_texts)} documents for project: {project_id}")
        llm_service = get_llm_service()
        state_data = await llm_service.analyze_documents(document_texts)
        state_json = json.dumps(state_data)

        result = await db.execute(select(ProjectState).where(ProjectState.project_id == project_id))
        existing_state = result.scalar_one_or_none()

        if existing_state:
            existing_state.state = state_json
            existing_state.updated_at = datetime.utcnow().isoformat()
        else:
            new_state = ProjectState(
                project_id=project_id,
                state=state_json,
                updated_at=datetime.utcnow().isoformat(),
            )
            db.add(new_state)

        await db.commit()

        state_data["projectId"] = project_id
        state_data["lastUpdated"] = datetime.utcnow().isoformat()

        logger.info(f"Document analysis completed for project: {project_id}")
        return state_data

    async def generate_proposal(self, project_id: str, db: AsyncSession, on_progress=None) -> str:
        """Generate architecture proposal for a project."""
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        result = await db.execute(select(ProjectState).where(ProjectState.project_id == project_id))
        state_record = result.scalar_one_or_none()
        if not state_record:
            raise ValueError("Project state not initialized. Please analyze documents first.")

        state = json.loads(state_record.state)
        llm_service = get_llm_service()
        proposal = await llm_service.generate_architecture_proposal(state, on_progress)
        return proposal
