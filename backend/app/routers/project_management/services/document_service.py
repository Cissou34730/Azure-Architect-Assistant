import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, ProjectDocument, ProjectState

from .document_parsing import extract_text_from_upload

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

        saved_docs: List[ProjectDocument] = []
        attempted_documents = 0
        parsed_documents = 0
        failures: List[Dict[str, Any]] = []

        for file in files:
            attempted_documents += 1
            content = await file.read()

            extracted_text, failure_reason = extract_text_from_upload(
                file_name=file.filename,
                mime_type=getattr(file, "content_type", None),
                content=content,
            )

            if extracted_text is None:
                failures.append(
                    {
                        "documentId": None,
                        "fileName": file.filename,
                        "reason": failure_reason or "unknown parse failure",
                    }
                )
                extracted_text = ""  # Persist empty text but keep the document record
            else:
                parsed_documents += 1

            doc = ProjectDocument(
                id=str(uuid.uuid4()),
                project_id=project_id,
                file_name=file.filename,
                mime_type=getattr(file, "content_type", "application/octet-stream"),
                raw_text=extracted_text,
                uploaded_at=datetime.now(timezone.utc).isoformat(),
            )

            db.add(doc)
            saved_docs.append(doc)

        await db.commit()

        # Persist ingestion stats into ProjectState (SC-004) without blocking upload.
        try:
            stats_payload = {
                "ingestionStats": {
                    "attemptedDocuments": attempted_documents,
                    "parsedDocuments": parsed_documents,
                    "failedDocuments": max(attempted_documents - parsed_documents, 0),
                    "failures": failures,
                }
            }

            state_result = await db.execute(
                select(ProjectState).where(ProjectState.project_id == project_id)
            )
            state_record = state_result.scalar_one_or_none()

            if state_record:
                import json

                current_state = json.loads(state_record.state)
                current_state.update(stats_payload)
                state_record.state = json.dumps(current_state)
                state_record.updated_at = datetime.now(timezone.utc).isoformat()
            else:
                import json

                db.add(
                    ProjectState(
                        project_id=project_id,
                        state=json.dumps(stats_payload),
                        updated_at=datetime.now(timezone.utc).isoformat(),
                    )
                )

            await db.commit()
        except Exception as exc:
            logger.warning(
                "Failed to persist ingestionStats for project %s (%s)",
                project_id,
                exc,
            )

        logger.info(f"Uploaded {len(saved_docs)} documents for project: {project_id}")
        return [doc.to_dict() for doc in saved_docs]

    async def analyze_documents(
        self, project_id: str, db: AsyncSession
    ) -> Dict[str, Any]:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        result = await db.execute(
            select(ProjectDocument).where(ProjectDocument.project_id == project_id)
        )
        documents = result.scalars().all()

        document_texts = [doc.raw_text for doc in documents if (doc.raw_text or "").strip()]
        if project.text_requirements:
            document_texts.append(project.text_requirements)

        if not document_texts:
            raise ValueError("No documents or text requirements to analyze")

        logger.info(
            f"Analyzing {len(document_texts)} documents for project: {project_id}"
        )
        from app.services.llm_service import get_llm_service

        llm_service = get_llm_service()
        state_data = await llm_service.analyze_documents(document_texts)

        # Always include ingestion stats (SC-004)
        failures = []
        parsed_documents = 0
        for doc in documents:
            if (doc.raw_text or "").strip():
                parsed_documents += 1
            else:
                failures.append(
                    {
                        "documentId": doc.id,
                        "fileName": doc.file_name,
                        "reason": "no extractable text",
                    }
                )

        state_data["ingestionStats"] = {
            "attemptedDocuments": len(documents),
            "parsedDocuments": parsed_documents,
            "failedDocuments": max(len(documents) - parsed_documents, 0),
            "failures": failures,
        }

        state_json = json.dumps(state_data)

        result = await db.execute(
            select(ProjectState).where(ProjectState.project_id == project_id)
        )
        existing_state = result.scalar_one_or_none()

        if existing_state:
            existing_state.state = state_json
            existing_state.updated_at = datetime.now(timezone.utc).isoformat()
        else:
            new_state = ProjectState(
                project_id=project_id,
                state=state_json,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            db.add(new_state)

        await db.commit()

        state_data["projectId"] = project_id
        state_data["lastUpdated"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"Document analysis completed for project: {project_id}")
        return state_data

    async def generate_proposal(
        self, project_id: str, db: AsyncSession, on_progress=None
    ) -> str:
        """Generate architecture proposal for a project."""
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        result = await db.execute(
            select(ProjectState).where(ProjectState.project_id == project_id)
        )
        state_record = result.scalar_one_or_none()
        if not state_record:
            raise ValueError(
                "Project state not initialized. Please analyze documents first."
            )

        state = json.loads(state_record.state)
        llm_service = get_llm_service()
        proposal = await llm_service.generate_architecture_proposal(state, on_progress)
        return proposal
