from __future__ import annotations

from typing import Any

import pytest

from app.features.projects.application.pending_changes_service import (
    ProjectPendingChangesService,
)
from app.features.projects.contracts import ChangeSetStatus, PendingChangeSetContract


class _StateProviderStub:
    def __init__(self, state: dict[str, Any] | Exception) -> None:
        self._state = state

    async def get_project_state(self, project_id: str, db: object) -> dict[str, Any]:
        if isinstance(self._state, Exception):
            raise self._state
        return self._state


def _pending_changes_state() -> dict[str, Any]:
    return {
        "projectId": "proj-1",
        "pendingChangeSets": [
            {
                "id": "cs-1",
                "projectId": "proj-1",
                "stage": "extract_requirements",
                "status": "pending",
                "createdAt": "2026-04-10T10:00:00Z",
                "sourceMessageId": "msg-1",
                "bundleSummary": "Extracted two candidate requirements",
                "proposedPatch": {
                    "requirements": [
                        {"id": "req-1", "title": "Requirement 1"},
                        {"id": "req-2", "title": "Requirement 2"},
                    ]
                },
                "artifactDrafts": [
                    {
                        "id": "draft-1",
                        "artifactType": "requirement",
                        "artifactId": "req-1",
                        "content": {"id": "req-1", "title": "Requirement 1"},
                    },
                    {
                        "id": "draft-2",
                        "artifactType": "requirement",
                        "artifactId": "req-2",
                        "content": {"id": "req-2", "title": "Requirement 2"},
                    },
                ],
            },
            {
                "id": "cs-2",
                "projectId": "proj-1",
                "stage": "manage_adr",
                "status": "approved",
                "createdAt": "2026-04-10T11:00:00Z",
                "sourceMessageId": "msg-2",
                "bundleSummary": "Captured ADR draft",
                "artifactDrafts": [
                    {
                        "id": "draft-3",
                        "artifactType": "adr",
                        "artifactId": "adr-1",
                        "content": {"id": "adr-1", "title": "Use ACA"},
                    }
                ],
            },
        ],
    }


@pytest.mark.asyncio
async def test_list_pending_changes_parses_typed_summaries() -> None:
    service = ProjectPendingChangesService(state_provider=_StateProviderStub(_pending_changes_state()))

    changes = await service.list_pending_changes(project_id="proj-1", db=object())

    assert [change.id for change in changes] == ["cs-1", "cs-2"]
    assert changes[0].artifact_count == 2
    assert changes[0].status is ChangeSetStatus.PENDING
    assert changes[1].artifact_count == 1


@pytest.mark.asyncio
async def test_list_pending_changes_filters_by_status() -> None:
    service = ProjectPendingChangesService(state_provider=_StateProviderStub(_pending_changes_state()))

    changes = await service.list_pending_changes(
        project_id="proj-1",
        db=object(),
        status=ChangeSetStatus.PENDING,
    )

    assert [change.id for change in changes] == ["cs-1"]


@pytest.mark.asyncio
async def test_get_pending_change_returns_full_contract() -> None:
    service = ProjectPendingChangesService(state_provider=_StateProviderStub(_pending_changes_state()))

    change = await service.get_pending_change(project_id="proj-1", change_set_id="cs-1", db=object())

    assert isinstance(change, PendingChangeSetContract)
    assert change.proposed_patch == {
        "requirements": [
            {"id": "req-1", "title": "Requirement 1"},
            {"id": "req-2", "title": "Requirement 2"},
        ]
    }
    assert [draft.artifact_id for draft in change.artifact_drafts] == ["req-1", "req-2"]


@pytest.mark.asyncio
async def test_get_pending_change_raises_for_missing_change_set() -> None:
    service = ProjectPendingChangesService(state_provider=_StateProviderStub(_pending_changes_state()))

    with pytest.raises(ValueError, match="Change set not found"):
        await service.get_pending_change(project_id="proj-1", change_set_id="missing", db=object())
