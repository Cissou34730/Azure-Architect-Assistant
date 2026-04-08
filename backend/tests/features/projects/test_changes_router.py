from __future__ import annotations

import pytest
from fastapi import HTTPException, Response

from app.features.projects.api.changes_router import (
    ChangeSetReviewRequest,
    ChangesQueryParams,
    approve_project_change,
    get_project_change,
    list_project_changes,
    reject_project_change,
    revise_project_change,
)
from app.features.projects.application.pending_changes_merge_service import (
    PendingChangeConflictError,
)
from app.features.projects.contracts import (
    ArtifactDraftContract,
    ArtifactDraftType,
    ChangeSetReviewResultContract,
    ChangeSetStatus,
    PendingChangeSetContract,
    PendingChangeSetSummaryContract,
)


class _PendingChangesServiceStub:
    def __init__(
        self,
        *,
        changes: list[PendingChangeSetSummaryContract] | None = None,
        detail: PendingChangeSetContract | None = None,
        error: Exception | None = None,
    ) -> None:
        self._changes = changes or []
        self._detail = detail
        self._error = error

    async def list_pending_changes(self, *, project_id: str, db: object, status: ChangeSetStatus | None = None):
        if self._error is not None:
            raise self._error
        return self._changes

    async def get_pending_change(self, *, project_id: str, change_set_id: str, db: object):
        if self._error is not None:
            raise self._error
        if self._detail is None:
            raise ValueError("Change set not found")
        return self._detail

    async def approve_pending_change(
        self,
        *,
        project_id: str,
        change_set_id: str,
        reason: str | None = None,
        db: object,
    ):
        if self._error is not None:
            raise self._error
        return ChangeSetReviewResultContract(change_set=_change_detail(), project_state={"projectId": project_id})

    async def reject_pending_change(
        self,
        *,
        project_id: str,
        change_set_id: str,
        reason: str | None = None,
        db: object,
    ):
        if self._error is not None:
            raise self._error
        detail = _change_detail().model_copy(update={"status": ChangeSetStatus.REJECTED, "review_reason": reason})
        return ChangeSetReviewResultContract(change_set=detail, project_state=None)

    async def revise_pending_change(
        self,
        *,
        project_id: str,
        change_set_id: str,
        reason: str | None = None,
        db: object,
    ):
        if self._error is not None:
            raise self._error
        detail = _change_detail().model_copy(update={"status": ChangeSetStatus.SUPERSEDED, "review_reason": reason})
        return ChangeSetReviewResultContract(change_set=detail, project_state=None)


def _change_summary() -> PendingChangeSetSummaryContract:
    return PendingChangeSetSummaryContract(
        id="cs-1",
        project_id="proj-1",
        stage="clarify",
        status=ChangeSetStatus.PENDING,
        created_at="2026-04-10T10:00:00Z",
        source_message_id="msg-1",
        bundle_summary="Need clarification on workload scale",
        artifact_count=1,
    )


def _change_detail() -> PendingChangeSetContract:
    return PendingChangeSetContract(
        id="cs-1",
        project_id="proj-1",
        stage="clarify",
        status=ChangeSetStatus.PENDING,
        created_at="2026-04-10T10:00:00Z",
        source_message_id="msg-1",
        bundle_summary="Need clarification on workload scale",
        review_reason=None,
        artifact_drafts=[
            ArtifactDraftContract(
                id="draft-1",
                artifact_type=ArtifactDraftType.CLARIFICATION_QUESTION,
                content={"question": "What is the peak TPS?"},
            )
        ],
    )


@pytest.mark.asyncio
async def test_list_project_changes_returns_service_results() -> None:
    response = Response()

    payload = await list_project_changes(
        project_id="proj-1",
        params=ChangesQueryParams(status=ChangeSetStatus.PENDING),
        response=response,
        db=object(),
        pending_changes_service=_PendingChangesServiceStub(changes=[_change_summary()]),
    )

    assert payload == [_change_summary()]
    assert "Deprecation" not in response.headers


@pytest.mark.asyncio
async def test_get_project_change_returns_detail() -> None:
    payload = await get_project_change(
        project_id="proj-1",
        change_set_id="cs-1",
        db=object(),
        pending_changes_service=_PendingChangesServiceStub(detail=_change_detail()),
    )

    assert payload.id == "cs-1"
    assert payload.artifact_drafts[0].artifact_type is ArtifactDraftType.CLARIFICATION_QUESTION


@pytest.mark.asyncio
async def test_changes_router_maps_missing_project_or_change_to_http_404() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await list_project_changes(
            project_id="proj-1",
            params=ChangesQueryParams(status=None),
            response=Response(),
            db=object(),
            pending_changes_service=_PendingChangesServiceStub(error=ValueError("Project state not found")),
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_approve_project_change_returns_review_result() -> None:
    payload = await approve_project_change(
        project_id="proj-1",
        change_set_id="cs-1",
        request=ChangeSetReviewRequest(reason="Looks good"),
        db=object(),
        pending_changes_service=_PendingChangesServiceStub(detail=_change_detail()),
    )

    assert payload.change_set.id == "cs-1"
    assert payload.project_state == {"projectId": "proj-1"}


@pytest.mark.asyncio
async def test_reject_and_revise_routes_delegate_to_service() -> None:
    reject_payload = await reject_project_change(
        project_id="proj-1",
        change_set_id="cs-1",
        request=ChangeSetReviewRequest(reason="Need more evidence"),
        db=object(),
        pending_changes_service=_PendingChangesServiceStub(detail=_change_detail()),
    )
    revise_payload = await revise_project_change(
        project_id="proj-1",
        change_set_id="cs-1",
        request=ChangeSetReviewRequest(reason="Update the proposal"),
        db=object(),
        pending_changes_service=_PendingChangesServiceStub(detail=_change_detail()),
    )

    assert reject_payload.change_set.status is ChangeSetStatus.REJECTED
    assert revise_payload.change_set.status is ChangeSetStatus.SUPERSEDED


@pytest.mark.asyncio
async def test_approve_route_maps_conflicts_to_http_409() -> None:
    conflict = PendingChangeConflictError(
        conflicts=[{"path": "context.summary", "existing": "old", "incoming": "new"}]
    )

    with pytest.raises(HTTPException) as exc_info:
        await approve_project_change(
            project_id="proj-1",
            change_set_id="cs-1",
            request=ChangeSetReviewRequest(),
            db=object(),
            pending_changes_service=_PendingChangesServiceStub(error=conflict),
        )

    assert exc_info.value.status_code == 409
