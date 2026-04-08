from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.features.projects.api.document_router import extract_requirements
from app.features.projects.contracts import ChangeSetStatus, PendingChangeSetContract


class _ExtractionEntryServiceStub:
    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.calls: list[dict[str, object]] = []

    async def extract_pending_requirements(
        self,
        *,
        project_id: str,
        db: object,
        source_message_id: str | None = None,
    ) -> PendingChangeSetContract:
        if self._error is not None:
            raise self._error
        self.calls.append(
            {
                "project_id": project_id,
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
async def test_extract_requirements_route_returns_pending_change_set() -> None:
    service = _ExtractionEntryServiceStub()

    payload = await extract_requirements(
        project_id="proj-1",
        db=object(),
        requirements_extraction_entry_service=service,
    )

    assert payload.stage == "extract_requirements"
    assert payload.status is ChangeSetStatus.PENDING
    assert service.calls == [{"project_id": "proj-1", "source_message_id": None}]


@pytest.mark.asyncio
async def test_extract_requirements_route_maps_value_errors() -> None:
    service = _ExtractionEntryServiceStub(error=ValueError("No parsed documents available for extraction"))

    with pytest.raises(HTTPException) as exc_info:
        await extract_requirements(
            project_id="proj-1",
            db=object(),
            requirements_extraction_entry_service=service,
        )

    assert exc_info.value.status_code == 400
