from __future__ import annotations

from typing import Any

import pytest

from app.features.agent.application.requirements_extraction_worker import (
    RequirementsExtractionWorker,
)
from app.features.projects.contracts import ChangeSetStatus, PendingChangeSetContract


class _PendingChangeRecorderStub:
    def __init__(self) -> None:
        self.recorded_change_set: PendingChangeSetContract | None = None

    async def record_pending_change(
        self,
        *,
        project_id: str,
        change_set: PendingChangeSetContract,
        db: object,
    ) -> PendingChangeSetContract:
        self.recorded_change_set = change_set
        return change_set


@pytest.mark.asyncio
async def test_extract_and_record_requirements_creates_pending_change_set() -> None:
    recorder = _PendingChangeRecorderStub()
    seen_payloads: list[list[str]] = []

    async def _analyzer(document_payloads: list[str]) -> dict[str, Any]:
        seen_payloads.append(document_payloads)
        return {
            "requirements": [
                {
                    "text": "Support SSO for internal users",
                    "category": "functional",
                    "ambiguity": {"isAmbiguous": False, "notes": ""},
                    "sources": [
                        {
                            "documentId": "doc-1",
                            "excerpt": "Support SSO for internal users",
                            "location": "p2",
                        }
                    ],
                },
                {
                    "text": "Support SSO for internal users",
                    "category": "functional",
                    "ambiguity": {"isAmbiguous": True, "notes": "Need IdP details"},
                    "sources": [
                        {
                            "documentId": "doc-2",
                            "excerpt": "Authenticate with Entra ID",
                            "location": "p4",
                        }
                    ],
                },
            ],
            "technicalConstraints": {
                "assumptions": ["Identity provider is Microsoft Entra ID"],
            },
        }

    worker = RequirementsExtractionWorker(
        analyzer=_analyzer,
        pending_change_recorder=recorder,
    )

    change_set = await worker.extract_and_record_requirements(
        project_id="proj-1",
        document_payloads=[
            {
                "id": "doc-1",
                "fileName": "rfp.txt",
                "rawText": "Support SSO for internal users",
            },
            {
                "id": "doc-2",
                "fileName": "appendix.txt",
                "rawText": "Authenticate with Entra ID",
            },
        ],
        source_message_id="msg-100",
        db=object(),
    )

    assert seen_payloads
    assert "DocumentId: doc-1" in seen_payloads[0][0]
    assert change_set.status is ChangeSetStatus.PENDING
    assert change_set.stage == "extract_requirements"
    assert len(change_set.artifact_drafts) == 1
    assert change_set.proposed_patch["requirements"][0]["text"] == "Support SSO for internal users"
    assert change_set.proposed_patch["requirements"][0]["ambiguity"]["isAmbiguous"] is True
    assert recorder.recorded_change_set is not None


@pytest.mark.asyncio
async def test_extract_and_record_requirements_requires_documents() -> None:
    worker = RequirementsExtractionWorker(
        analyzer=lambda payloads: payloads,  # type: ignore[arg-type]
        pending_change_recorder=_PendingChangeRecorderStub(),
    )

    with pytest.raises(ValueError, match="No parsed documents available"):
        await worker.extract_and_record_requirements(
            project_id="proj-1",
            document_payloads=[],
            db=object(),
        )
