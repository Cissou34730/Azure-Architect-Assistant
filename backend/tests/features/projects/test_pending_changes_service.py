from __future__ import annotations

from typing import Any

import pytest

from app.features.projects.application.pending_changes_merge_service import (
    PendingChangeConflictError,
)
from app.features.projects.application.pending_changes_service import (
    ProjectPendingChangesService,
)
from app.features.projects.contracts import (
    ArtifactDraftType,
    ChangeSetReviewResultContract,
    ChangeSetStatus,
    PendingChangeSetContract,
)


class _StateProviderStub:
    def __init__(self, state: dict[str, Any] | Exception) -> None:
        self._state = state

    async def get_project_state(self, project_id: str, db: object) -> dict[str, Any]:
        if isinstance(self._state, Exception):
            raise self._state
        return self._state


class _StateStoreStub:
    def __init__(self) -> None:
        self.persisted_state: dict[str, Any] | None = None
        self.calls: list[dict[str, Any]] = []

    async def persist_composed_state(
        self,
        *,
        project_id: str,
        state: dict[str, Any],
        db: object,
        replace_missing: bool,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        self.persisted_state = state
        self.calls.append(
            {
                "project_id": project_id,
                "replace_missing": replace_missing,
                "updated_at": updated_at,
            }
        )
        return state


class _DbStub:
    def __init__(self) -> None:
        self.commit_called = False

    async def commit(self) -> None:
        self.commit_called = True


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


@pytest.mark.asyncio
async def test_approve_pending_change_merges_patch_and_marks_change_set_approved() -> None:
    store = _StateStoreStub()
    db = _DbStub()
    service = ProjectPendingChangesService(
        state_provider=_StateProviderStub(_pending_changes_state()),
        state_store=store,
    )

    result = await service.approve_pending_change(
        project_id="proj-1",
        change_set_id="cs-1",
        db=db,
    )

    assert isinstance(result, ChangeSetReviewResultContract)
    assert result.change_set.status is ChangeSetStatus.APPROVED
    assert result.project_state is not None
    assert result.project_state["requirements"] == [
        {"id": "req-1", "title": "Requirement 1"},
        {"id": "req-2", "title": "Requirement 2"},
    ]
    assert result.project_state["pendingChangeSets"][0]["status"] == "approved"
    assert store.persisted_state is not None
    assert db.commit_called is True


@pytest.mark.asyncio
async def test_approve_pending_change_raises_conflict_without_persisting() -> None:
    conflicting_state = _pending_changes_state()
    conflicting_state["context"] = {"summary": "Existing summary"}
    conflicting_state["pendingChangeSets"][0]["proposedPatch"] = {
        "context": {"summary": "Replacement summary"}
    }
    store = _StateStoreStub()
    db = _DbStub()
    service = ProjectPendingChangesService(
        state_provider=_StateProviderStub(conflicting_state),
        state_store=store,
    )

    with pytest.raises(PendingChangeConflictError) as exc_info:
        await service.approve_pending_change(
            project_id="proj-1",
            change_set_id="cs-1",
            db=db,
        )

    assert exc_info.value.conflicts[0]["path"] == "context.summary"
    assert store.persisted_state is None
    assert db.commit_called is False


@pytest.mark.asyncio
async def test_reject_pending_change_marks_change_set_rejected_without_merging() -> None:
    store = _StateStoreStub()
    db = _DbStub()
    service = ProjectPendingChangesService(
        state_provider=_StateProviderStub(_pending_changes_state()),
        state_store=store,
    )

    result = await service.reject_pending_change(
        project_id="proj-1",
        change_set_id="cs-1",
        reason="Need manual cleanup",
        db=db,
    )

    assert result.change_set.status is ChangeSetStatus.REJECTED
    assert result.change_set.review_reason == "Need manual cleanup"
    assert result.project_state is None
    assert store.persisted_state is not None
    assert store.persisted_state["pendingChangeSets"][0]["status"] == "rejected"
    assert "requirements" not in store.persisted_state


@pytest.mark.asyncio
async def test_revise_pending_change_marks_change_set_superseded() -> None:
    store = _StateStoreStub()
    db = _DbStub()
    service = ProjectPendingChangesService(
        state_provider=_StateProviderStub(_pending_changes_state()),
        state_store=store,
    )

    result = await service.revise_pending_change(
        project_id="proj-1",
        change_set_id="cs-1",
        reason="Architect requested revision",
        db=db,
    )

    assert result.change_set.status is ChangeSetStatus.SUPERSEDED
    assert result.change_set.review_reason == "Architect requested revision"
    assert store.persisted_state is not None
    assert store.persisted_state["pendingChangeSets"][0]["status"] == "superseded"


@pytest.mark.asyncio
async def test_record_pending_change_appends_new_bundle() -> None:
    store = _StateStoreStub()
    db = _DbStub()
    service = ProjectPendingChangesService(
        state_provider=_StateProviderStub(_pending_changes_state()),
        state_store=store,
    )
    change_set = PendingChangeSetContract(
        id="cs-new",
        project_id="proj-1",
        stage="extract_requirements",
        status=ChangeSetStatus.PENDING,
        created_at="2026-04-10T12:00:00Z",
        source_message_id="msg-3",
        bundle_summary="Extracted one additional requirement",
        artifact_drafts=[
            {
                "id": "draft-new",
                "artifactType": ArtifactDraftType.REQUIREMENT,
                "content": {"text": "Support audit exports"},
            }
        ],
        proposed_patch={"requirements": [{"id": "req-3", "title": "Requirement 3"}]},
    )

    recorded = await service.record_pending_change(
        project_id="proj-1",
        change_set=change_set,
        db=db,
    )

    assert recorded.id == "cs-new"
    assert store.persisted_state is not None
    assert store.persisted_state["pendingChangeSets"][-1]["id"] == "cs-new"
