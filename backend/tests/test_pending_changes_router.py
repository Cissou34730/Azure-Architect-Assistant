from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features.projects.api.changes_router import (
    get_pending_changes_service_dep,
    router,
)
from app.features.projects.contracts import (
    ChangeSetReviewResultContract,
    ChangeSetStatus,
    PendingChangeSetContract,
    PendingChangeSetSummaryContract,
)
from app.shared.db.projects_database import get_db


class _PendingChangesServiceStub:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def list_pending_changes(
        self,
        *,
        project_id: str,
        db: object,
        status: ChangeSetStatus | None = None,
    ) -> list[PendingChangeSetSummaryContract]:
        self.calls.append(
            {
                "method": "list",
                "project_id": project_id,
                "status": status,
            }
        )
        return [
            PendingChangeSetSummaryContract(
                id="cs-1",
                project_id=project_id,
                stage="clarify",
                status=ChangeSetStatus.PENDING,
                created_at=datetime.now(timezone.utc).isoformat(),
                source_message_id="msg-1",
                bundle_summary="Clarification updates",
                artifact_count=1,
            )
        ]

    async def get_pending_change(
        self,
        *,
        project_id: str,
        change_set_id: str,
        db: object,
    ) -> PendingChangeSetContract:
        self.calls.append(
            {
                "method": "detail",
                "project_id": project_id,
                "change_set_id": change_set_id,
            }
        )
        return PendingChangeSetContract(
            id=change_set_id,
            project_id=project_id,
            stage="clarify",
            status=ChangeSetStatus.PENDING,
            created_at=datetime.now(timezone.utc).isoformat(),
            source_message_id="msg-1",
            bundle_summary="Clarification updates",
            proposed_patch={"requirements": [{"id": "req-1", "text": "Support SSO"}]},
            artifact_drafts=[],
        )

    async def approve_pending_change(
        self,
        *,
        project_id: str,
        change_set_id: str,
        reason: str | None = None,
        db: object,
    ) -> ChangeSetReviewResultContract:
        self.calls.append(
            {
                "method": "approve",
                "project_id": project_id,
                "change_set_id": change_set_id,
                "reason": reason,
            }
        )
        return ChangeSetReviewResultContract(
            change_set=PendingChangeSetContract(
                id=change_set_id,
                project_id=project_id,
                stage="clarify",
                status=ChangeSetStatus.APPROVED,
                created_at=datetime.now(timezone.utc).isoformat(),
                source_message_id="msg-1",
                bundle_summary="Clarification updates",
                proposed_patch={},
                artifact_drafts=[],
                review_reason=reason,
            ),
            project_state={"pendingChangeSets": []},
            conflicts=[],
        )

    async def reject_pending_change(
        self,
        *,
        project_id: str,
        change_set_id: str,
        reason: str | None = None,
        db: object,
    ) -> ChangeSetReviewResultContract:
        self.calls.append(
            {
                "method": "reject",
                "project_id": project_id,
                "change_set_id": change_set_id,
                "reason": reason,
            }
        )
        return ChangeSetReviewResultContract(
            change_set=PendingChangeSetContract(
                id=change_set_id,
                project_id=project_id,
                stage="clarify",
                status=ChangeSetStatus.REJECTED,
                created_at=datetime.now(timezone.utc).isoformat(),
                source_message_id="msg-1",
                bundle_summary="Clarification updates",
                proposed_patch={},
                artifact_drafts=[],
                review_reason=reason,
            ),
            project_state=None,
            conflicts=[],
        )

    async def revise_pending_change(self, **_: Any) -> ChangeSetReviewResultContract:
        raise AssertionError("revise route should not call the service")

    async def record_pending_change(
        self,
        *,
        project_id: str,
        change_set: PendingChangeSetContract,
        db: object,
    ) -> PendingChangeSetContract:
        self.calls.append(
            {
                "method": "record",
                "project_id": project_id,
                "change_set": change_set,
            }
        )
        return change_set


def _build_client(service: _PendingChangesServiceStub) -> TestClient:
    app = FastAPI()
    app.include_router(router)

    async def _get_db_override():
        yield object()

    app.dependency_overrides[get_pending_changes_service_dep] = lambda: service
    app.dependency_overrides[get_db] = _get_db_override
    return TestClient(app)


def test_openapi_exposes_canonical_pending_changes_routes_only() -> None:
    service = _PendingChangesServiceStub()

    with _build_client(service) as client:
        paths = client.get("/openapi.json").json()["paths"]

    assert "/api/projects/{project_id}/pending-changes" in paths
    assert "/api/projects/{project_id}/pending-changes/{change_set_id}" in paths
    assert "/api/projects/{project_id}/pending-changes/{change_set_id}/approve" in paths
    assert "/api/projects/{project_id}/pending-changes/{change_set_id}/reject" in paths
    assert "/api/projects/{project_id}/changes" not in paths
    assert "/api/projects/{project_id}/changes/{change_set_id}" not in paths
    assert all("revise" not in path for path in paths)


@pytest.mark.parametrize("route_prefix", ["pending-changes", "changes"])
def test_list_routes_support_canonical_and_legacy_paths(route_prefix: str) -> None:
    service = _PendingChangesServiceStub()

    with _build_client(service) as client:
        response = client.get(
            f"/api/projects/proj-1/{route_prefix}",
            params={"status": "pending"},
        )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "cs-1",
            "projectId": "proj-1",
            "stage": "clarify",
            "status": "pending",
            "createdAt": response.json()[0]["createdAt"],
            "sourceMessageId": "msg-1",
            "bundleSummary": "Clarification updates",
            "artifactCount": 1,
        }
    ]
    assert service.calls == [
        {
            "method": "list",
            "project_id": "proj-1",
            "status": ChangeSetStatus.PENDING,
        }
    ]


@pytest.mark.parametrize("route_prefix", ["pending-changes", "changes"])
def test_detail_routes_support_canonical_and_legacy_paths(route_prefix: str) -> None:
    service = _PendingChangesServiceStub()

    with _build_client(service) as client:
        response = client.get(f"/api/projects/proj-1/{route_prefix}/cs-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "cs-1"
    assert payload["projectId"] == "proj-1"
    assert payload["proposedPatch"] == {
        "requirements": [{"id": "req-1", "text": "Support SSO"}]
    }
    assert service.calls == [
        {
            "method": "detail",
            "project_id": "proj-1",
            "change_set_id": "cs-1",
        }
    ]


@pytest.mark.parametrize("route_prefix", ["pending-changes", "changes"])
@pytest.mark.parametrize(
    ("action", "expected_status"),
    [("approve", "approved"), ("reject", "rejected")],
)
def test_review_routes_support_canonical_and_legacy_paths(
    route_prefix: str,
    action: str,
    expected_status: str,
) -> None:
    service = _PendingChangesServiceStub()

    with _build_client(service) as client:
        response = client.post(
            f"/api/projects/proj-1/{route_prefix}/cs-1/{action}",
            json={"reason": "reviewed"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["changeSet"]["status"] == expected_status
    assert payload["changeSet"]["reviewReason"] == "reviewed"
    assert service.calls == [
        {
            "method": action,
            "project_id": "proj-1",
            "change_set_id": "cs-1",
            "reason": "reviewed",
        }
    ]


def test_legacy_revise_route_is_disabled() -> None:
    service = _PendingChangesServiceStub()

    with _build_client(service) as client:
        response = client.post(
            "/api/projects/proj-1/changes/cs-1/revise",
            json={"reason": "needs edits"},
        )

    assert response.status_code == 410
    assert response.json()["detail"] == "Revise is deferred to v2. Use approve or reject for pending changes in v1."
    assert service.calls == []


def test_answer_architect_question_returns_pending_change_set() -> None:
    service = _PendingChangesServiceStub()

    with _build_client(service) as client:
        response = client.post(
            "/api/projects/proj-1/architect-questions/q-1/answer",
            json={"status": "answered", "answer": "Use zone-redundant storage."},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["projectId"] == "proj-1"
    assert payload["stage"] == "architect_questions"
    assert payload["status"] == "pending"
    updates = payload["proposedPatch"]["_architectQuestions"]["updates"]
    assert len(updates) == 1
    assert updates[0]["id"] == "q-1"
    assert updates[0]["status"] == "answered"
    assert updates[0]["answer"] == "Use zone-redundant storage."


def test_answer_architect_question_deferred_status() -> None:
    service = _PendingChangesServiceStub()

    with _build_client(service) as client:
        response = client.post(
            "/api/projects/proj-1/architect-questions/q-2/answer",
            json={"status": "deferred"},
        )

    assert response.status_code == 200
    payload = response.json()
    updates = payload["proposedPatch"]["_architectQuestions"]["updates"]
    assert updates[0]["status"] == "deferred"
    assert updates[0]["answer"] is None
