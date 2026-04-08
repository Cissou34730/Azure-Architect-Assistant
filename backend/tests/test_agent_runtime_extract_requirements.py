from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.agents_system.langgraph.nodes import extract_requirements as extract_requirements_module
from app.agents_system.langgraph.nodes import manage_adr as manage_adr_module
from app.agents_system.langgraph.nodes.extract_requirements import (
    execute_extract_requirements_node,
)
from app.agents_system.langgraph.nodes.manage_adr import (
    execute_manage_adr_stage_worker_node,
)
from app.features.projects.contracts import ChangeSetStatus, PendingChangeSetContract


class _RequirementsExtractionEntryServiceStub:
    def __init__(self, *, change_set: PendingChangeSetContract) -> None:
        self.change_set = change_set
        self.calls: list[dict[str, object]] = []

    async def extract_pending_requirements(
        self,
        *,
        project_id: str,
        db: object,
        source_message_id: str | None = None,
    ) -> PendingChangeSetContract:
        self.calls.append(
            {
                "project_id": project_id,
                "db": db,
                "source_message_id": source_message_id,
            }
        )
        return self.change_set


def _build_pending_change_set() -> PendingChangeSetContract:
    return PendingChangeSetContract(
        id="cs-req-1",
        project_id="proj-1",
        stage="extract_requirements",
        status=ChangeSetStatus.PENDING,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_message_id=None,
        bundle_summary="Extracted 2 requirement(s) from 2 document(s)",
        proposed_patch={
            "requirements": [
                {"text": "Support SSO for internal users"},
                {"text": "Retain audit logs for 90 days"},
            ]
        },
        artifact_drafts=[],
    )


@pytest.mark.asyncio
async def test_execute_extract_requirements_node_records_pending_bundle(monkeypatch) -> None:
    change_set = _build_pending_change_set()
    service = _RequirementsExtractionEntryServiceStub(change_set=change_set)
    refreshed_state = {"pendingChangeSets": [{"id": change_set.id}]}
    state_loader = AsyncMock(return_value=refreshed_state)
    emitted_events: list[tuple[str, dict[str, object]]] = []

    async def _capture_event(event_type: str, payload: dict[str, object]) -> None:
        emitted_events.append((event_type, payload))

    monkeypatch.setattr(extract_requirements_module, "read_project_state", state_loader)

    result = await execute_extract_requirements_node(
        {
            "project_id": "proj-1",
            "user_message": "Analyze the uploaded documents",
            "next_stage": "extract_requirements",
            "current_project_state": {},
            "event_callback": _capture_event,
        },
        db=object(),
        entry_service=service,
    )

    assert service.calls == [
        {
            "project_id": "proj-1",
            "db": service.calls[0]["db"],
            "source_message_id": None,
        }
    ]
    state_loader.assert_awaited_once()
    assert result["success"] is True
    assert result["handled_by_stage_worker"] is True
    assert result["updated_project_state"] == refreshed_state
    assert "cs-req-1" in result["agent_output"]
    assert "review and approve" in result["agent_output"].lower()
    assert emitted_events == [
        ("message_start", {"role": "assistant"}),
        ("token", {"text": result["agent_output"]}),
    ]


@pytest.mark.asyncio
async def test_execute_extract_requirements_node_skips_other_stages() -> None:
    result = await execute_extract_requirements_node(
        {
            "project_id": "proj-1",
            "user_message": "Continue",
            "next_stage": "clarify",
        },
        db=object(),
        entry_service=_RequirementsExtractionEntryServiceStub(change_set=_build_pending_change_set()),
    )

    assert result == {}


@pytest.mark.asyncio
async def test_execute_extract_requirements_node_surfaces_errors() -> None:
    class _FailingRequirementsExtractionEntryService:
        async def extract_pending_requirements(
            self,
            *,
            project_id: str,
            db: object,
            source_message_id: str | None = None,
        ) -> PendingChangeSetContract:
            raise ValueError("No parsed documents available for extraction")

    result = await execute_extract_requirements_node(
        {
            "project_id": "proj-1",
            "user_message": "Analyze the uploaded documents",
            "next_stage": "extract_requirements",
        },
        db=object(),
        entry_service=_FailingRequirementsExtractionEntryService(),
    )

    assert result["success"] is False
    assert result["error"] == "No parsed documents available for extraction"
    assert result["agent_output"] == "ERROR: No parsed documents available for extraction"


class _ADRManagementWorkerStub:
    def __init__(self, *, change_set: PendingChangeSetContract) -> None:
        self.change_set = change_set
        self.calls: list[dict[str, object]] = []

    async def draft_and_record_pending_change(
        self,
        *,
        project_id: str,
        user_message: str,
        project_state: dict[str, object],
        db: object,
        source_message_id: str | None = None,
    ) -> PendingChangeSetContract:
        self.calls.append(
            {
                "project_id": project_id,
                "user_message": user_message,
                "project_state": project_state,
                "source_message_id": source_message_id,
                "db": db,
            }
        )
        return self.change_set


def _build_adr_pending_change_set() -> PendingChangeSetContract:
    return PendingChangeSetContract(
        id="cs-adr-1",
        project_id="proj-1",
        stage="manage_adr",
        status=ChangeSetStatus.PENDING,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_message_id="msg-1",
        bundle_summary="Drafted one ADR",
        proposed_patch={
            "_adrLifecycle": {
                "action": "create",
                "adrPayload": {"title": "Azure SQL Database"},
            }
        },
        artifact_drafts=[],
    )


@pytest.mark.asyncio
async def test_execute_manage_adr_stage_worker_records_pending_bundle(monkeypatch) -> None:
    change_set = _build_adr_pending_change_set()
    worker = _ADRManagementWorkerStub(change_set=change_set)
    refreshed_state = {"pendingChangeSets": [{"id": change_set.id}]}
    state_loader = AsyncMock(return_value=refreshed_state)
    emitted_events: list[tuple[str, dict[str, object]]] = []

    async def _capture_event(event_type: str, payload: dict[str, object]) -> None:
        emitted_events.append((event_type, payload))

    monkeypatch.setattr(manage_adr_module, "read_project_state", state_loader)

    result = await execute_manage_adr_stage_worker_node(
        {
            "project_id": "proj-1",
            "user_message": "Create an ADR for the database choice.",
            "next_stage": "manage_adr",
            "current_project_state": {},
            "user_message_id": "msg-1",
            "event_callback": _capture_event,
        },
        db=object(),
        worker=worker,
    )

    assert worker.calls == [
        {
            "project_id": "proj-1",
            "user_message": "Create an ADR for the database choice.",
            "project_state": {},
            "source_message_id": "msg-1",
            "db": worker.calls[0]["db"],
        }
    ]
    state_loader.assert_awaited_once()
    assert result["success"] is True
    assert result["handled_by_stage_worker"] is True
    assert result["updated_project_state"] == refreshed_state
    assert "pending change set `cs-adr-1`" in result["agent_output"]
    assert "review and approve" in result["agent_output"].lower()
    assert emitted_events == [
        ("message_start", {"role": "assistant"}),
        ("token", {"text": result["agent_output"]}),
    ]


@pytest.mark.asyncio
async def test_execute_manage_adr_stage_worker_skips_other_stages() -> None:
    result = await execute_manage_adr_stage_worker_node(
        {
            "project_id": "proj-1",
            "user_message": "Continue",
            "next_stage": "clarify",
        },
        db=object(),
        worker=_ADRManagementWorkerStub(change_set=_build_adr_pending_change_set()),
    )

    assert result == {}
