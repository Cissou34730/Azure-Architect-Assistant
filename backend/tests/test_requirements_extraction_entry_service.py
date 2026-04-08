from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.features.projects.application.requirements_extraction_entry_service import (
    ProjectRequirementsExtractionEntryService,
)
from app.features.projects.contracts import ChangeSetStatus, PendingChangeSetContract
from app.models.project import Project, ProjectDocument


class _WorkerStub:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def extract_and_record_requirements(
        self,
        *,
        project_id: str,
        document_payloads: list[dict[str, object]],
        source_message_id: str | None = None,
        db: object,
    ) -> PendingChangeSetContract:
        self.calls.append(
            {
                "project_id": project_id,
                "document_payloads": document_payloads,
                "source_message_id": source_message_id,
            }
        )
        return PendingChangeSetContract(
            id="cs-1",
            project_id=project_id,
            stage="extract_requirements",
            status=ChangeSetStatus.PENDING,
            created_at=datetime.now(timezone.utc).isoformat(),
            source_message_id=source_message_id,
            bundle_summary="Extracted one requirement",
            proposed_patch={"requirements": [{"text": "Support SSO"}]},
            artifact_drafts=[],
        )


@pytest.mark.asyncio
async def test_extract_pending_requirements_loads_parsed_documents(test_db_session) -> None:
    project = Project(id="proj-1", name="Project One")
    test_db_session.add(project)
    test_db_session.add_all(
        [
            ProjectDocument(
                id="doc-1",
                project_id=project.id,
                file_name="rfp.txt",
                mime_type="text/plain",
                raw_text="Support SSO",
                parse_status="parsed",
            ),
            ProjectDocument(
                id="doc-2",
                project_id=project.id,
                file_name="empty.txt",
                mime_type="text/plain",
                raw_text="",
                parse_status="parsed",
            ),
            ProjectDocument(
                id="doc-3",
                project_id=project.id,
                file_name="failed.txt",
                mime_type="text/plain",
                raw_text="Should not be used",
                parse_status="parse_failed",
            ),
        ]
    )
    await test_db_session.commit()

    worker = _WorkerStub()
    service = ProjectRequirementsExtractionEntryService(worker=worker)

    result = await service.extract_pending_requirements(
        project_id="proj-1",
        db=test_db_session,
        source_message_id="msg-1",
    )

    assert result.id == "cs-1"
    assert len(worker.calls) == 1
    assert worker.calls[0]["source_message_id"] == "msg-1"
    assert worker.calls[0]["document_payloads"] == [
        {
            "id": "doc-1",
            "fileName": "rfp.txt",
            "rawText": "Support SSO",
        }
    ]


@pytest.mark.asyncio
async def test_extract_pending_requirements_raises_for_missing_project(test_db_session) -> None:
    service = ProjectRequirementsExtractionEntryService(worker=_WorkerStub())

    with pytest.raises(ValueError, match="Project not found"):
        await service.extract_pending_requirements(
            project_id="missing",
            db=test_db_session,
        )


@pytest.mark.asyncio
async def test_extract_pending_requirements_raises_when_no_parsed_documents(test_db_session) -> None:
    project = Project(id="proj-2", name="Project Two")
    test_db_session.add(project)
    await test_db_session.commit()

    service = ProjectRequirementsExtractionEntryService(worker=_WorkerStub())

    with pytest.raises(ValueError, match="No parsed documents available"):
        await service.extract_pending_requirements(
            project_id="proj-2",
            db=test_db_session,
        )
