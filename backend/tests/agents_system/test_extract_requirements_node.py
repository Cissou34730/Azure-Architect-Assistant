from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.agents_system.langgraph.nodes import extract_requirements as extract_requirements_node
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
                "db": db,
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
            bundle_summary="Extracted 2 requirement(s) from 1 document(s)",
            proposed_patch={
                "requirements": [
                    {"id": "req-1", "text": "Support SSO"},
                    {"id": "req-2", "text": "Support audit logging"},
                ]
            },
            artifact_drafts=[],
        )


@pytest.mark.asyncio
async def test_execute_extract_requirements_node_runs_worker_and_refreshes_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _ExtractionEntryServiceStub()
    events: list[tuple[str, dict[str, object]]] = []
    refreshed_state = {"pendingChangeSets": [{"id": "cs-1"}]}

    async def _callback(event_type: str, payload: dict[str, object]) -> None:
        events.append((event_type, payload))

    async def _fake_read_project_state(project_id: str, db: object) -> dict[str, object]:
        assert project_id == "proj-1"
        assert db is test_db
        return refreshed_state

    test_db = object()
    monkeypatch.setattr(
        extract_requirements_node,
        "read_project_state",
        _fake_read_project_state,
    )

    result = await extract_requirements_node.execute_extract_requirements_node(
        {
            "project_id": "proj-1",
            "next_stage": "extract_requirements",
            "user_message_id": "msg-1",
            "event_callback": _callback,
        },
        db=test_db,
        entry_service=service,
    )

    assert service.calls == [
        {
            "project_id": "proj-1",
            "db": test_db,
            "source_message_id": "msg-1",
        }
    ]
    assert result["handled_by_stage_worker"] is True
    assert result["updated_project_state"] == refreshed_state
    assert result["final_answer"] == result["agent_output"]
    assert "cs-1" in result["agent_output"]
    assert "2 requirement draft(s)" in result["agent_output"]
    assert events == [
        ("message_start", {"role": "assistant"}),
        ("token", {"text": result["agent_output"]}),
    ]


@pytest.mark.asyncio
async def test_execute_extract_requirements_node_returns_empty_for_other_stages() -> None:
    service = _ExtractionEntryServiceStub()

    result = await extract_requirements_node.execute_extract_requirements_node(
        {
            "project_id": "proj-1",
            "next_stage": "clarify",
        },
        db=object(),
        entry_service=service,
    )

    assert result == {}
    assert service.calls == []


@pytest.mark.asyncio
async def test_execute_extract_requirements_node_surfaces_stage_errors() -> None:
    service = _ExtractionEntryServiceStub(error=ValueError("No parsed documents available"))

    result = await extract_requirements_node.execute_extract_requirements_node(
        {
            "project_id": "proj-1",
            "next_stage": "extract_requirements",
        },
        db=object(),
        entry_service=service,
    )

    assert result["handled_by_stage_worker"] is True
    assert result["success"] is False
    assert result["error"] == "No parsed documents available"
    assert result["final_answer"].startswith("ERROR: No parsed documents available")
