from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from app.agents_system.langgraph.nodes import clarify as clarify_module
from app.agents_system.langgraph.nodes.clarify import (
    _user_wants_to_proceed,
    execute_clarification_planner_node,
)
from app.features.agent.contracts import (
    ClarificationPlanningResultContract,
    ClarificationQuestionContract,
    ClarificationQuestionGroupContract,
)
from app.features.projects.contracts import ChangeSetStatus, PendingChangeSetContract
from app.features.projects.infrastructure.project_state_components_repository import (
    PROJECT_STATE_COMPONENT_SOURCES,
)


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
                "kind": "resolve",
                "project_id": project_id,
                "user_message": user_message,
                "project_state": project_state,
                "source_message_id": source_message_id,
                "db": db,
            }
        )
        return self.change_set

    async def proceed_with_defaults(
        self,
        *,
        project_id: str,
        project_state: dict[str, object],
        db: object,
        source_message_id: str | None = None,
    ) -> PendingChangeSetContract:
        self.calls.append(
            {
                "kind": "proceed_with_defaults",
                "project_id": project_id,
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
            "kind": "resolve",
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


def test_user_wants_to_proceed_detection() -> None:
    assert _user_wants_to_proceed("yes, proceed with the defaults")
    assert _user_wants_to_proceed("proceed")
    assert _user_wants_to_proceed("use defaults please")
    assert _user_wants_to_proceed("continue with assumptions")
    assert _user_wants_to_proceed("continue with defaults")
    assert not _user_wants_to_proceed("what is Azure Container Apps?")
    assert not _user_wants_to_proceed("Partners authenticate with their own Entra tenants.")
    assert not _user_wants_to_proceed("continue")


@pytest.mark.asyncio
async def test_execute_clarification_planner_node_proceeds_with_defaults(
    monkeypatch,
) -> None:
    """When user wants to proceed, default assumptions are persisted as pending changes."""
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
            "user_message": "proceed with defaults",
            "user_message_id": "msg-proceed-1",
            "next_stage": "clarify",
            "current_project_state": {
                "clarificationQuestions": [
                    {
                        "id": "q-auth",
                        "question": "Do partners use their own tenant or a shared tenant?",
                        "status": "open",
                        "defaultAssumption": "Partners use their own Entra tenant (B2B).",
                        "relatedRequirementIds": ["req-auth"],
                    }
                ],
            },
            "event_callback": _capture_event,
        },
        db=object(),
        resolution_worker=worker,
    )

    # proceed_with_defaults must be called, not resolve_and_record_pending_change
    assert len(worker.calls) == 1
    assert worker.calls[0]["kind"] == "proceed_with_defaults"
    assert worker.calls[0]["project_id"] == "proj-1"
    assert worker.calls[0]["source_message_id"] == "msg-proceed-1"

    assert result["success"] is True
    assert result["handled_by_stage_worker"] is True
    assert result["updated_project_state"] == refreshed_state
    assert "pending change set `cs-clarify-1`" in result["agent_output"]
    assert "review and approve" in result["agent_output"].lower()
    assert emitted_events[0] == ("message_start", {"role": "assistant"})


# ── Q0.4 failing tests for architect question artifact persistence ──────────────


def test_architect_questions_registered_in_component_sources() -> None:
    """architectQuestions must be a durable artifact family in PROJECT_STATE_COMPONENT_SOURCES.

    EXPECTED FAILURE: 'architectQuestions' key is not yet registered.
    """
    assert "architectQuestions" in PROJECT_STATE_COMPONENT_SOURCES


def test_architect_question_contract_shape() -> None:
    """ArchitectQuestionContract must validate all lifecycle fields correctly.

    EXPECTED FAILURE: ArchitectQuestionContract does not exist in clarification_planner yet.
    """
    from app.features.agent.contracts.clarification_planner import (  # noqa: PLC0415
        ArchitectQuestionContract,
    )

    q = ArchitectQuestionContract(
        question="Should we use zone-redundant storage for blob data?",
        designDecision="Storage tier selection",
        coverageSources=["mindmap/storage", "mindmap/resilience"],
        riskIfUnanswered="May fail HA requirements silently",
        recommendedEvidence=["SLA spec", "disaster-recovery-runbook.pdf"],
        status="open",
        answer=None,
        answeredAt=None,
        answerSource=None,
    )
    assert q.question == "Should we use zone-redundant storage for blob data?"
    assert q.status == "open"
    assert q.answer is None
    assert q.answeredAt is None


@pytest.mark.asyncio
async def test_execute_clarification_planner_node_structured_payload_includes_architect_questions() -> None:
    """When the planner returns architect question groups, structured_payload must expose them.

    EXPECTED FAILURE: ClarificationPlanningResultContract does not yet support
    architect_question_groups and the node does not populate architect questions
    in the structured_payload.
    """
    from app.features.agent.contracts.clarification_planner import (  # noqa: PLC0415
        ArchitectQuestionGroupContract,
    )

    plan = ClarificationPlanningResultContract(
        question_groups=[
            ClarificationQuestionGroupContract(
                theme="Security",
                questions=[
                    ClarificationQuestionContract(
                        question="Do partner users sign in with their own tenant?",
                        why_it_matters="Drives tenant and RBAC decisions.",
                        architectural_impact="high",
                        priority=1,
                        related_requirement_ids=["req-auth"],
                    )
                ],
            )
        ],
        architect_question_groups=[
            ArchitectQuestionGroupContract(
                theme="Storage",
                architect_questions=[
                    {
                        "question": "Should we use zone-redundant storage?",
                        "designDecision": "Storage tier selection",
                        "coverageSources": ["mindmap/storage"],
                        "riskIfUnanswered": "May miss HA requirements",
                        "recommendedEvidence": ["SLA doc"],
                        "status": "open",
                    }
                ],
            )
        ],
    )

    emitted_events: list[tuple[str, dict[str, object]]] = []

    async def _capture_event(event_type: str, payload: dict[str, object]) -> None:
        emitted_events.append((event_type, payload))

    worker = _ClarificationPlannerWorkerStub(result=plan)

    result = await execute_clarification_planner_node(
        {
            "project_id": "proj-1",
            "user_message": "Continue",
            "next_stage": "clarify",
            "current_project_state": {},
            "event_callback": _capture_event,
        },
        worker=worker,
    )

    assert result["success"] is True
    payload = result["structured_payload"]
    assert payload["type"] == "clarification_questions"
    # Architect questions must be present alongside customer questions
    assert "architect_questions" in payload


@pytest.mark.asyncio
async def test_execute_clarification_planner_node_architect_questions_as_pending_artifacts() -> None:
    """Architect questions must flow into pending artifact drafts so they can be persisted.

    EXPECTED FAILURE: The clarify node does not yet create pending artifact drafts
    for architect questions returned by the planning worker.
    """
    from app.features.agent.contracts.clarification_planner import (  # noqa: PLC0415
        ArchitectQuestionGroupContract,
    )

    plan = ClarificationPlanningResultContract(
        question_groups=[
            ClarificationQuestionGroupContract(
                theme="Networking",
                questions=[
                    ClarificationQuestionContract(
                        question="Will this service be internet-facing?",
                        why_it_matters="Determines perimeter and WAF needs.",
                        architectural_impact="high",
                        priority=1,
                        related_requirement_ids=["req-net"],
                    )
                ],
            )
        ],
        architect_question_groups=[
            ArchitectQuestionGroupContract(
                theme="Identity",
                architect_questions=[
                    {
                        "question": "Which identity provider handles service-to-service auth?",
                        "designDecision": "Service identity mechanism",
                        "coverageSources": ["mindmap/identity"],
                        "riskIfUnanswered": "Service auth could be misconfigured",
                        "recommendedEvidence": ["Identity architecture doc"],
                        "status": "open",
                    }
                ],
            )
        ],
    )

    emitted_events: list[tuple[str, dict[str, object]]] = []

    async def _capture_event(event_type: str, payload: dict[str, object]) -> None:
        emitted_events.append((event_type, payload))

    worker = _ClarificationPlannerWorkerStub(result=plan)

    result = await execute_clarification_planner_node(
        {
            "project_id": "proj-1",
            "user_message": "Continue",
            "next_stage": "clarify",
            "current_project_state": {},
            "event_callback": _capture_event,
        },
        worker=worker,
    )

    assert result["success"] is True
    # Architect questions must appear as pending artifact drafts for the approval flow
    artifact_drafts = result.get("artifact_drafts", [])
    assert any(
        draft.get("artifact_family") == "architectQuestions" for draft in artifact_drafts
    ), "Expected at least one pending artifact draft for architectQuestions"
