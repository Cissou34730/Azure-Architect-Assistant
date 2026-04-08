from __future__ import annotations

from typing import Any

import pytest

from app.agents_system.langgraph.nodes.clarify import (
    execute_clarification_planner_node,
)
from app.features.agent.contracts import (
    ClarificationPlanningResultContract,
    ClarificationQuestionContract,
    ClarificationQuestionGroupContract,
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
    assert emitted_events == [
        ("message_start", {"role": "assistant"}),
        ("token", {"text": result["final_answer"]}),
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
