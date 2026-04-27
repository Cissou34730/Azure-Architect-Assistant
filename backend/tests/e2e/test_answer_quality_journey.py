"""P14: End-to-End Journey Tests for agent answer quality.

Tests the full lifecycle for 4 key scenarios using mocks/stubs — no real LLM calls.
Each test verifies that the workflow routing, structured payloads, and quality gates
behave correctly across clarification, architecture proposal, cost estimation,
and quality-gate retry paths.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.agents_system.langgraph.adapter import _build_workflow_result
from app.agents_system.langgraph.nodes.clarify import execute_clarification_planner_node
from app.agents_system.langgraph.nodes.quality_gate import (
    completeness_check,
    quality_gate_node,
)
from app.features.agent.contracts import (
    ClarificationPlanningResultContract,
    ClarificationQuestionContract,
    ClarificationQuestionGroupContract,
)

# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

_AAA_STEP: dict[str, Any] = {"tool": "aaa_generate_candidate_architecture"}

_RICH_ARCHITECTURE_ANSWER = (
    "I recommend Azure App Service because it offers scalability and availability "
    "for web workloads. "
    "Key trade-offs include a drawback of limited container orchestration control. "
    "Main risk is performance degradation under extreme load — a concern for high-traffic scenarios. "
    "WAF well-architected pillar review confirms this meets the reliability pillar. "
    "Evidence: Microsoft documentation and reference architectures support this decision. "
    "The candidate architecture has been persisted to the project state."
)


class _ClarificationPlannerWorkerStub:
    """Stub that returns a pre-configured ClarificationPlanningResultContract."""

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


# ---------------------------------------------------------------------------
# Test 1: Clarification Journey
# ---------------------------------------------------------------------------


class TestClarificationJourney:
    """When a vague request hits the clarify stage, the agent returns structured
    questions with decision_impact (affectedDecision) and default_assumption
    (defaultAssumption) fields populated.
    """

    async def test_vague_request_returns_structured_questions_with_decision_fields(
        self,
    ) -> None:
        plan = ClarificationPlanningResultContract(
            question_groups=[
                ClarificationQuestionGroupContract(
                    theme="Business Context",
                    questions=[
                        ClarificationQuestionContract(
                            question="What is the primary purpose of this solution?",
                            why_it_matters=(
                                "Purpose drives architectural choices and compliance requirements."
                            ),
                            architectural_impact="high",
                            affected_decision="Service tier and compliance scope",
                            default_assumption="General-purpose internal web application",
                        )
                    ],
                )
            ]
        )
        stub = _ClarificationPlannerWorkerStub(result=plan)
        state: dict[str, Any] = {
            "next_stage": "clarify",
            "user_message": "I need an Azure solution for my company",
        }

        result = await execute_clarification_planner_node(state, worker=stub)

        assert result["success"] is True
        assert result["handled_by_stage_worker"] is True

        structured = result.get("structured_payload")
        assert structured is not None, "structured_payload must be present"
        assert structured["type"] == "clarification_questions"

        questions = structured.get("questions", [])
        assert len(questions) >= 1, "At least one clarification question expected"

        first_q = questions[0]
        assert first_q.get("affectedDecision"), "affectedDecision must be populated"
        assert first_q.get("defaultAssumption"), "defaultAssumption must be populated"

    async def test_clarification_node_skipped_for_non_clarify_stage(self) -> None:
        state: dict[str, Any] = {
            "next_stage": "propose_candidate",
            "user_message": "I need an architecture",
        }
        result = await execute_clarification_planner_node(state)
        assert result == {}, "Node must return empty dict when stage is not clarify"


# ---------------------------------------------------------------------------
# Test 2: Architecture Proposal Journey
# ---------------------------------------------------------------------------


class TestArchitectureProposalJourney:
    """The propose_candidate stage returns a WorkflowStageResult with the
    required structure and the quality gate correctly distinguishes rich
    answers from thin receipts.
    """

    def test_workflow_result_has_required_keys(self) -> None:
        state: dict[str, Any] = {
            "next_stage": "propose_candidate",
            "agent_output": _RICH_ARCHITECTURE_ANSWER,
            "intermediate_steps": [_AAA_STEP],
            "success": True,
        }
        result = _build_workflow_result(result_state=state, summary=_RICH_ARCHITECTURE_ANSWER)

        assert "stage" in result
        assert "summary" in result
        assert "nextStep" in result
        assert "reasoningSummary" in result
        assert result["stage"] == "propose_candidate"
        assert result["summary"] == _RICH_ARCHITECTURE_ANSWER

    def test_quality_gate_passes_rich_architecture_answer(self) -> None:
        state: dict[str, Any] = {
            "next_stage": "propose_candidate",
            "agent_output": _RICH_ARCHITECTURE_ANSWER,
            "artifact_edit_detected": True,
            "intermediate_steps": [_AAA_STEP],
            "quality_retry_count": 0,
            "handled_by_stage_worker": False,
        }
        assert completeness_check(state) == "continue"

    def test_quality_gate_retries_thin_receipt(self) -> None:
        state: dict[str, Any] = {
            "next_stage": "propose_candidate",
            "agent_output": "I've created a change set.",
            "artifact_edit_detected": True,
            "intermediate_steps": [],
            "quality_retry_count": 0,
            "handled_by_stage_worker": False,
        }
        assert completeness_check(state) == "retry"


# ---------------------------------------------------------------------------
# Test 3: Cost Estimation Journey
# ---------------------------------------------------------------------------


class TestCostEstimationJourney:
    """The pricing stage returns a workflow result with the correct structure,
    and a cost-estimation answer with confidence/drivers/assumptions passes
    the quality gate.
    """

    _COST_ANSWER = (
        "Estimated monthly cost: ~$2,400 with high confidence. "
        "Key cost drivers: Compute (40%), Storage (20%), Networking (15%). "
        "Assumptions: 3 app service instances, 500 GB storage, 1 TB egress. "
        "Optimization opportunities: reserved instances reduce compute by ~30%."
    )

    def test_pricing_stage_result_has_required_structure(self) -> None:
        state: dict[str, Any] = {
            "next_stage": "pricing",
            "agent_output": self._COST_ANSWER,
            "intermediate_steps": [],
            "success": True,
        }
        result = _build_workflow_result(result_state=state, summary=self._COST_ANSWER)

        assert "stage" in result
        assert "summary" in result
        assert "nextStep" in result
        assert result["stage"] == "pricing"

    def test_quality_gate_accepts_cost_answer_when_no_artifact_edit(self) -> None:
        """Cost estimation without artifact_edit_detected passes through unconditionally."""
        state: dict[str, Any] = {
            "next_stage": "pricing",
            "agent_output": self._COST_ANSWER,
            "artifact_edit_detected": False,
            "intermediate_steps": [],
            "quality_retry_count": 0,
            "handled_by_stage_worker": False,
        }
        assert completeness_check(state) == "continue"

    def test_quality_gate_accepts_cost_answer_with_aaa_tool_call(self) -> None:
        state: dict[str, Any] = {
            "next_stage": "pricing",
            "agent_output": self._COST_ANSWER,
            "artifact_edit_detected": True,
            "intermediate_steps": [{"tool": "aaa_record_cost_estimate"}],
            "quality_retry_count": 0,
            "handled_by_stage_worker": False,
        }
        assert completeness_check(state) == "continue"


# ---------------------------------------------------------------------------
# Test 4: Quality Gate Retry Journey
# ---------------------------------------------------------------------------


class TestQualityGateRetryJourney:
    """The quality gate detects thin receipts, increments retry_count, and sets
    a specific retry_reason. Enriched answers that include all required
    architectural sections pass through.
    """

    _THIN_RECEIPT = "I've created a pending change set for candidate architecture."

    def test_thin_receipt_triggers_retry(self) -> None:
        state: dict[str, Any] = {
            "next_stage": "propose_candidate",
            "agent_output": self._THIN_RECEIPT,
            "artifact_edit_detected": True,
            "intermediate_steps": [],
            "quality_retry_count": 0,
            "handled_by_stage_worker": False,
        }
        assert completeness_check(state) == "retry"

    def test_quality_gate_node_increments_retry_count(self) -> None:
        state: dict[str, Any] = {
            "next_stage": "propose_candidate",
            "agent_output": self._THIN_RECEIPT,
            "artifact_edit_detected": True,
            "intermediate_steps": [],
            "quality_retry_count": 0,
            "handled_by_stage_worker": False,
        }
        updates = quality_gate_node(state)

        assert updates["quality_retry_count"] == 1
        assert updates.get("quality_retry_reason"), "quality_retry_reason must be set"

    def test_quality_gate_node_sets_architectural_reason_on_propose_stage(self) -> None:
        state: dict[str, Any] = {
            "next_stage": "propose_candidate",
            "agent_output": "Pending change set created.",
            "artifact_edit_detected": True,
            "intermediate_steps": [_AAA_STEP],
            "quality_retry_count": 0,
            "handled_by_stage_worker": False,
        }
        updates = quality_gate_node(state)

        assert "Architecture answer is incomplete" in updates["quality_retry_reason"]

    def test_enriched_answer_passes_quality_gate(self) -> None:
        """When artifact_edit_detected is False the gate passes unconditionally
        (no write expected, text-only response path).
        """
        state: dict[str, Any] = {
            "next_stage": "propose_candidate",
            "agent_output": _RICH_ARCHITECTURE_ANSWER,
            "artifact_edit_detected": False,
            "intermediate_steps": [],
            "quality_retry_count": 0,
            "handled_by_stage_worker": False,
        }
        assert completeness_check(state) == "continue"

    def test_enriched_answer_with_aaa_call_passes_quality_gate(self) -> None:
        """Rich answer + AAA tool call + propose_candidate stage passes the gate."""
        state: dict[str, Any] = {
            "next_stage": "propose_candidate",
            "agent_output": _RICH_ARCHITECTURE_ANSWER,
            "artifact_edit_detected": True,
            "intermediate_steps": [_AAA_STEP],
            "quality_retry_count": 0,
            "handled_by_stage_worker": False,
        }
        assert completeness_check(state) == "continue"
