"""Project-scoped entry point for requirements extraction."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.agent.application import RequirementsExtractionWorker
from app.features.projects.contracts import PendingChangeSetContract
from app.models.project import Project, ProjectDocument


class ProjectRequirementsExtractionEntryService:
    """Load parsed project documents and delegate to the extraction worker."""

    def __init__(self, *, worker: RequirementsExtractionWorker) -> None:
        self._worker = worker

    async def extract_pending_requirements(
        self,
        *,
        project_id: str,
        db: AsyncSession,
        source_message_id: str | None = None,
    ) -> PendingChangeSetContract:
        project_result = await db.execute(select(Project).where(Project.id == project_id))
        project = project_result.scalar_one_or_none()
        if project is None:
            raise ValueError("Project not found")

        documents_result = await db.execute(
            select(ProjectDocument).where(
                ProjectDocument.project_id == project_id,
                ProjectDocument.parse_status == "parsed",
            )
        )
        document_payloads = [
            {
                "id": document.id,
                "fileName": document.file_name,
                "rawText": document.raw_text,
            }
            for document in documents_result.scalars().all()
            if (document.raw_text or "").strip()
        ]
        if not document_payloads:
            raise ValueError("No parsed documents available for extraction")

        return await self._worker.extract_and_record_requirements(
            project_id=project_id,
            document_payloads=document_payloads,
            source_message_id=source_message_id,
            db=db,
        )
