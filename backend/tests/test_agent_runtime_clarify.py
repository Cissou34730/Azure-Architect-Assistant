from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from app.agents_system.langgraph.nodes import clarify as clarify_module
from app.agents_system.langgraph.nodes.clarify import (
    execute_clarification_planner_node,
)
from app.features.agent.contracts import (
    ClarificationPlanningResultContract,
    ClarificationQuestionContract,
    ClarificationQuestionGroupContract,
)
from app.features.projects.contracts import ChangeSetStatus, PendingChangeSetContract


class _ClarificationPlannerWorkerStub:
    def __init__(self, *, result: ClarificationPlanningResultContract) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    async def plan_questions(
        self,
        *,
        user_message: str,
        current_state: dict[str, Any],
        mindmap_coverage: dict[str, Any] | None,
    ) -> ClarificationPlanningResultContract:
        self.calls.append(
            {
                "user_message": user_message,
                "current_state": current_state,
                "mindmap_coverage": mindmap_coverage,
            }
        )
        return self.result


class _ClarificationResolutionWorkerStub:
    def __init__(self, *, change_set: PendingChangeSetContract) -> None:
        self.change_set = change_set
        self.calls: list[dict[str, object]] = []

    async def resolve_and_record_pending_change(
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


def _build_plan() -> ClarificationPlanningResultContract:
    return ClarificationPlanningResultContract(
        question_groups=[
            ClarificationQuestionGroupContract(
                theme="Security",
                questions=[
                    ClarificationQuestionContract(
                        question="Do partner users sign in with their own tenant or a shared enterprise tenant?",
                        why_it_matters="Identity boundaries drive tenant, RBAC, and networking decisions.",
                        architectural_impact="high",
                        priority=1,
                        related_requirement_ids=["req-auth"],
                    )
                ],
            ),
            ClarificationQuestionGroupContract(
                theme="Operations",
                questions=[
                    ClarificationQuestionContract(
                        question="What recovery time objective is required for the platform?",
                        why_it_matters="Recovery objectives influence region design and backup strategy.",
                        architectural_impact="high",
                        priority=2,
                        related_requirement_ids=["req-dr"],
                    )
                ],
            ),
        ]
    )


def _build_clarification_change_set() -> PendingChangeSetContract:
    return PendingChangeSetContract(
        id="cs-clarify-1",
        project_id="proj-1",
        stage="clarify",
        status=ChangeSetStatus.PENDING,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_message_id="msg-clarify-1",
        bundle_summary="Resolved clarification answers",
        proposed_patch={
            "_clarificationResolution": {
                "requirements": [
                    {
                        "id": "req-auth",
                        "text": "Support partner sign-in with Microsoft Entra B2B collaboration.",
                        "ambiguity": {"isAmbiguous": False, "notes": ""},
                    }
                ],
                "clarificationQuestions": [{"id": "q-auth", "status": "answered"}],
                "assumptions": [
                    {
                        "id": "assumption-1",
                        "text": "Partners authenticate from their own Microsoft Entra tenants.",
                        "status": "open",
                        "relatedRequirementIds": ["req-auth"],
                    }
                ],
            }
        },
        artifact_drafts=[],
    )


@pytest.mark.asyncio
async def test_execute_clarification_planner_node_formats_grouped_questions() -> None:
    emitted_events: list[tuple[str, dict[str, object]]] = []

    async def _capture_event(event_type: str, payload: dict[str, object]) -> None:
        emitted_events.append((event_type, payload))

    worker = _ClarificationPlannerWorkerStub(result=_build_plan())

    result = await execute_clarification_planner_node(
        {
            "project_id": "proj-1",
            "user_message": "Continue",
            "next_stage": "clarify",
            "current_project_state": {"requirements": [{"id": "req-auth"}]},
            "mindmap_coverage": {"topics": {"operations": {"status": "not-addressed"}}},
            "event_callback": _capture_event,
        },
        worker=worker,
    )

    assert worker.calls == [
        {
            "user_message": "Continue",
            "current_state": {"requirements": [{"id": "req-auth"}]},
            "mindmap_coverage": {"topics": {"operations": {"status": "not-addressed"}}},
        }
    ]
    assert result["success"] is True
    assert result["handled_by_stage_worker"] is True
    assert "Clarification planning complete." in result["final_answer"]
    assert "**Security**" in result["final_answer"]
    assert "Why it matters:" in result["final_answer"]
    assert result["structured_payload"] == {
        "type": "clarification_questions",
        "questions": [
            {
                "id": "security-1",
                "text": "Do partner users sign in with their own tenant or a shared enterprise tenant?",
                "theme": "Security",
                "whyItMatters": "Identity boundaries drive tenant, RBAC, and networking decisions.",
                "architecturalImpact": "high",
                "priority": 1,
                "relatedRequirementIds": ["req-auth"],
            },
            {
                "id": "operations-1",
                "text": "What recovery time objective is required for the platform?",
                "theme": "Operations",
                "whyItMatters": "Recovery objectives influence region design and backup strategy.",
                "architecturalImpact": "high",
                "priority": 2,
                "relatedRequirementIds": ["req-dr"],
            },
        ],
    }
    assert emitted_events == [
        ("message_start", {"role": "assistant"}),
        ("token", {"text": result["final_answer"]}),
    ]


@pytest.mark.asyncio
async def test_execute_clarification_planner_node_records_pending_bundle_for_answers(
    monkeypatch,
) -> None:
    change_set = _build_clarification_change_set()
    worker = _ClarificationResolutionWorkerStub(change_set=change_set)
    refreshed_state = {"pendingChangeSets": [{"id": change_set.id}]}
    state_loader = pytest.importorskip("unittest.mock").AsyncMock(return_value=refreshed_state)
    emitted_events: list[tuple[str, dict[str, object]]] = []

    async def _capture_event(event_type: str, payload: dict[str, object]) -> None:
        emitted_events.append((event_type, payload))

    monkeypatch.setattr(clarify_module, "read_project_state", state_loader)

    result = await execute_clarification_planner_node(
        {
            "project_id": "proj-1",
            "user_message": "Partners authenticate with their own Entra tenants.",
            "user_message_id": "msg-clarify-1",
            "next_stage": "clarify",
            "current_project_state": {
                "requirements": [
                    {
                        "id": "req-auth",
                        "text": "Support partner sign-in",
                        "ambiguity": {"isAmbiguous": True, "notes": "Identity boundary is unclear."},
                    }
                ],
                "clarificationQuestions": [
                    {
                        "id": "q-auth",
                        "question": "Do partners use their own tenant or a shared tenant?",
                        "status": "open",
                        "relatedRequirementIds": ["req-auth"],
                    }
                ],
            },
            "event_callback": _capture_event,
        },
        db=object(),
        resolution_worker=worker,
    )

    assert worker.calls == [
        {
            "project_id": "proj-1",
            "user_message": "Partners authenticate with their own Entra tenants.",
            "project_state": {
                "requirements": [
                    {
                        "id": "req-auth",
                        "text": "Support partner sign-in",
                        "ambiguity": {"isAmbiguous": True, "notes": "Identity boundary is unclear."},
                    }
                ],
                "clarificationQuestions": [
                    {
                        "id": "q-auth",
                        "question": "Do partners use their own tenant or a shared tenant?",
                        "status": "open",
                        "relatedRequirementIds": ["req-auth"],
                    }
                ],
            },
            "source_message_id": "msg-clarify-1",
            "db": worker.calls[0]["db"],
        }
    ]
    state_loader.assert_awaited_once()
    assert result["success"] is True
    assert result["handled_by_stage_worker"] is True
    assert result["updated_project_state"] == refreshed_state
    assert "pending change set `cs-clarify-1`" in result["agent_output"]
    assert "review and approve" in result["agent_output"].lower()
    assert emitted_events == [
        ("message_start", {"role": "assistant"}),
        ("token", {"text": result["agent_output"]}),
    ]


@pytest.mark.asyncio
async def test_execute_clarification_planner_node_skips_other_stages() -> None:
    result = await execute_clarification_planner_node(
        {
            "project_id": "proj-1",
            "user_message": "Continue",
            "next_stage": "propose_candidate",
        }
    )

    assert result == {}


@pytest.mark.asyncio
async def test_execute_clarification_planner_node_surfaces_errors() -> None:
    class _FailingClarificationPlannerWorker:
        async def plan_questions(
            self,
            *,
            user_message: str,
            current_state: dict[str, Any],
            mindmap_coverage: dict[str, Any] | None,
        ) -> ClarificationPlanningResultContract:
            raise ValueError("Clarification planner returned no actionable clarification questions")

    result = await execute_clarification_planner_node(
        {
            "project_id": "proj-1",
            "user_message": "Continue",
            "next_stage": "clarify",
        },
        worker=_FailingClarificationPlannerWorker(),
    )

    assert result["success"] is False
    assert (
        result["error"]
        == "Clarification planner returned no actionable clarification questions"
    )
    assert (
        result["agent_output"]
        == "ERROR: Clarification planner returned no actionable clarification questions"
    )
