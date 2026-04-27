"""Tests for quality gate loop in LangGraph workflow.

Slice 2 of systemic quality improvements:
- Quality check node added BEFORE persist_messages
- Routes back to run_agent when output is incomplete
- Injects quality_retry_reason into state for next agent turn
- Caps retries at configurable limit (default 2)
- retry_prompt no longer goes to END (dead end fixed)
- Existing error-based retry preserved
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Quality check node logic
# ---------------------------------------------------------------------------

class TestQualityCheckNode:
    """Verify completeness_check_node detects incomplete outputs."""

    def _make_state(self, **overrides: Any) -> dict[str, Any]:
        base: dict[str, Any] = {
            "agent_output": "I've analyzed the requirements and persisted them.",
            "artifact_edit_detected": False,
            "quality_retry_count": 0,
            "intermediate_steps": [],
            "handled_by_stage_worker": False,
        }
        base.update(overrides)
        return base

    def test_passes_when_no_artifact_edit(self) -> None:
        """When artifact_edit_detected is False, always pass."""
        from app.agents_system.langgraph.nodes.quality_gate import completeness_check

        state = self._make_state(artifact_edit_detected=False, agent_output="")
        result = completeness_check(state)
        assert result == "continue"

    def test_passes_when_stage_worker_handled(self) -> None:
        """Stage workers bypass quality check."""
        from app.agents_system.langgraph.nodes.quality_gate import completeness_check

        state = self._make_state(
            artifact_edit_detected=True,
            handled_by_stage_worker=True,
        )
        result = completeness_check(state)
        assert result == "continue"

    def test_fails_when_artifact_edit_but_no_tool_calls(self) -> None:
        """artifact_edit_detected=True but no tool calls = incomplete."""
        from app.agents_system.langgraph.nodes.quality_gate import completeness_check

        state = self._make_state(
            artifact_edit_detected=True,
            intermediate_steps=[],
            agent_output="Here are some requirements you should consider...",
        )
        result = completeness_check(state)
        assert result == "retry"

    def test_passes_when_artifact_edit_with_tool_calls(self) -> None:
        """artifact_edit_detected=True with aaa_ tool calls = OK."""
        from app.agents_system.langgraph.nodes.quality_gate import completeness_check

        step = {"tool": "aaa_manage_artifacts", "tool_input": {}, "result": "OK"}
        state = self._make_state(
            artifact_edit_detected=True,
            intermediate_steps=[step],
        )
        result = completeness_check(state)
        assert result == "continue"

    def test_fails_when_artifact_edit_with_only_search_tools(self) -> None:
        """artifact_edit_detected=True but only search tools = incomplete."""
        from app.agents_system.langgraph.nodes.quality_gate import completeness_check

        step = {"tool": "kb_search", "tool_input": {}, "result": "some results"}
        state = self._make_state(
            artifact_edit_detected=True,
            intermediate_steps=[step],
        )
        result = completeness_check(state)
        assert result == "retry"

    def test_caps_retries_at_limit(self) -> None:
        """Don't retry more than quality_retry_max (default 2)."""
        from app.agents_system.langgraph.nodes.quality_gate import completeness_check

        state = self._make_state(
            artifact_edit_detected=True,
            intermediate_steps=[],
            quality_retry_count=2,
        )
        result = completeness_check(state)
        assert result == "continue"  # Gives up after max retries

    def test_fails_on_empty_output(self) -> None:
        """Empty agent_output always triggers retry if under limit."""
        from app.agents_system.langgraph.nodes.quality_gate import completeness_check

        state = self._make_state(
            artifact_edit_detected=True,
            agent_output="",
        )
        result = completeness_check(state)
        assert result == "retry"

    def test_fails_on_error_output(self) -> None:
        """ERROR: prefix in output triggers retry."""
        from app.agents_system.langgraph.nodes.quality_gate import completeness_check

        state = self._make_state(
            agent_output="ERROR: model rejected parameter",
            quality_retry_count=0,
        )
        result = completeness_check(state)
        assert result == "retry"


# ---------------------------------------------------------------------------
# Quality retry node (injects reason into state)
# ---------------------------------------------------------------------------

class TestQualityRetryNode:
    """Verify build_quality_retry builds proper state for retry."""

    def test_increments_retry_count(self) -> None:
        from app.agents_system.langgraph.nodes.quality_gate import build_quality_retry

        state: dict[str, Any] = {
            "quality_retry_count": 0,
            "agent_output": "I couldn't find...",
            "artifact_edit_detected": True,
        }
        result = build_quality_retry(state)
        assert result["quality_retry_count"] == 1

    def test_sets_retry_reason(self) -> None:
        from app.agents_system.langgraph.nodes.quality_gate import build_quality_retry

        state: dict[str, Any] = {
            "quality_retry_count": 0,
            "agent_output": "Here are some ideas...",
            "artifact_edit_detected": True,
        }
        result = build_quality_retry(state)
        assert "quality_retry_reason" in result
        assert len(result["quality_retry_reason"]) > 10


# ---------------------------------------------------------------------------
# Graph state has quality_retry fields
# ---------------------------------------------------------------------------

class TestGraphStateQualityFields:
    """Verify graph state includes quality retry fields."""

    def test_quality_retry_count_in_state(self) -> None:
        from app.agents_system.langgraph.state import GraphState
        assert "quality_retry_count" in GraphState.__annotations__

    def test_quality_retry_reason_in_state(self) -> None:
        from app.agents_system.langgraph.state import GraphState
        assert "quality_retry_reason" in GraphState.__annotations__


# ---------------------------------------------------------------------------
# Graph topology: quality_check is wired before persist
# ---------------------------------------------------------------------------

class TestGraphTopology:
    """Verify the graph factory wires quality gate correctly."""

    def test_quality_check_node_exists(self) -> None:
        """Graph must have a quality_check node."""
        from app.agents_system.langgraph.graph_factory import _build_project_chat_workflow
        from unittest.mock import MagicMock

        db = MagicMock()
        workflow = _build_project_chat_workflow(db, "test-msg-id")
        assert "quality_check" in workflow.nodes

    def test_retry_prompt_does_not_go_to_end(self) -> None:
        """retry_prompt must NOT go to END — must loop back."""
        from app.agents_system.langgraph.graph_factory import _build_project_chat_workflow
        from unittest.mock import MagicMock

        db = MagicMock()
        workflow = _build_project_chat_workflow(db, "test-msg-id")
        # Check that retry_prompt has an edge back to run_agent, not END
        edges = workflow.edges
        retry_edges = [e for e in edges if e[0] == "retry_prompt"]
        # Should go to run_agent, not __end__
        targets = [e[1] for e in retry_edges]
        assert "run_agent" in targets or len(retry_edges) == 0  # conditional edges
        assert "__end__" not in targets


# ---------------------------------------------------------------------------
# Settings for quality retry
# ---------------------------------------------------------------------------

class TestQualityRetrySettings:
    """Verify quality retry settings exist in AppSettings."""

    def test_quality_retry_max_default(self) -> None:
        from app.shared.config.settings.llm_tuning import LLMTuningSettingsMixin
        m = LLMTuningSettingsMixin()
        assert m.quality_retry_max == 2


# ---------------------------------------------------------------------------
# P5: Architecture completeness quality gates (propose_candidate stage)
# ---------------------------------------------------------------------------

class TestArchitectureCompletenessGate:
    """P5 quality gates for propose_candidate stage."""

    def _make_step(self, tool: str) -> Any:
        from unittest.mock import Mock
        m = Mock()
        m.tool = tool
        return m

    def test_weak_architecture_answer_fails_quality_gate(self) -> None:
        """A receipt-only answer should fail quality gate for propose_candidate stage."""
        from app.agents_system.langgraph.nodes.quality_gate import completeness_check
        from unittest.mock import Mock

        step = Mock()
        step.tool = "aaa_generate_candidate_architecture"
        state: dict[str, Any] = {
            "next_stage": "propose_candidate",
            "agent_output": "I have created a pending change set with your architecture.",
            "artifact_edit_detected": True,
            "intermediate_steps": [step],
            "quality_retry_count": 0,
            "handled_by_stage_worker": False,
        }
        result = completeness_check(state)
        assert result == "retry"

    def test_strong_architecture_answer_passes_quality_gate(self) -> None:
        """A complete architecture briefing should pass quality gate."""
        from app.agents_system.langgraph.nodes.quality_gate import completeness_check
        from unittest.mock import Mock

        step = Mock()
        step.tool = "aaa_generate_candidate_architecture"
        state: dict[str, Any] = {
            "next_stage": "propose_candidate",
            "agent_output": (
                "I recommend Azure Container Apps for this workload because it provides "
                "auto-scaling. Trade-offs: vs AKS it has less control. "
                "Risks: cold starts may impact latency. "
                "WAF: reliability pillar covered via zone redundancy. "
                "Reference: learn.microsoft.com/azure/container-apps. "
                "I persisted the candidate architecture aaa_generate_candidate."
            ),
            "artifact_edit_detected": True,
            "intermediate_steps": [step],
            "quality_retry_count": 0,
            "handled_by_stage_worker": False,
        }
        result = completeness_check(state)
        assert result == "continue"

    def test_quality_retry_reason_names_missing_sections(self) -> None:
        """build_quality_retry for propose_candidate names missing sections."""
        from app.agents_system.langgraph.nodes.quality_gate import build_quality_retry
        from unittest.mock import Mock

        step = Mock()
        step.tool = "aaa_generate_candidate_architecture"
        state: dict[str, Any] = {
            "next_stage": "propose_candidate",
            "agent_output": "Architecture persisted as change set.",
            "artifact_edit_detected": True,
            "intermediate_steps": [step],
            "quality_retry_count": 0,
            "handled_by_stage_worker": False,
        }
        result = build_quality_retry(state)
        reason = result["quality_retry_reason"].lower()
        assert "trade-off" in reason or "missing" in reason

    def test_quality_gate_passes_for_non_architecture_stage(self) -> None:
        """Non-architecture stages should not be subject to architecture quality checks."""
        from app.agents_system.langgraph.nodes.quality_gate import completeness_check

        state: dict[str, Any] = {
            "next_stage": "clarify",
            "agent_output": "I have some questions for you.",
            "artifact_edit_detected": False,
            "intermediate_steps": [],
            "quality_retry_count": 0,
            "handled_by_stage_worker": False,
        }
        result = completeness_check(state)
        assert result == "continue"

    def test_generic_receipt_fails_quality_gate(self) -> None:
        """Short receipt-only output fails gate for propose_candidate."""
        from app.agents_system.langgraph.nodes.quality_gate import completeness_check
        from unittest.mock import Mock

        step = Mock()
        step.tool = "aaa_generate_candidate_architecture"
        state: dict[str, Any] = {
            "next_stage": "propose_candidate",
            "agent_output": "Persisted. Change set created.",
            "artifact_edit_detected": True,
            "intermediate_steps": [step],
            "quality_retry_count": 0,
            "handled_by_stage_worker": False,
        }
        result = completeness_check(state)
        assert result == "retry"

    def test_architecture_gate_respects_retry_limit(self) -> None:
        """After exhausting retries, even a weak answer is accepted."""
        from app.agents_system.langgraph.nodes.quality_gate import completeness_check
        from unittest.mock import Mock

        step = Mock()
        step.tool = "aaa_generate_candidate_architecture"
        state: dict[str, Any] = {
            "next_stage": "propose_candidate",
            "agent_output": "Architecture persisted as change set.",
            "artifact_edit_detected": True,
            "intermediate_steps": [step],
            "quality_retry_count": 2,  # at max
            "handled_by_stage_worker": False,
        }
        result = completeness_check(state)
        assert result == "continue"

    def test_check_architecture_answer_quality_returns_missing(self) -> None:
        """_check_architecture_answer_quality lists missing sections."""
        from app.agents_system.langgraph.nodes.quality_gate import _check_architecture_answer_quality

        output = "I have created a pending change set with your architecture. This is a longer string to pass the 100 char threshold for the check."
        missing = _check_architecture_answer_quality(output)
        assert len(missing) > 0
        assert any("trade-off" in m.lower() or "risk" in m.lower() for m in missing)

    def test_is_generic_receipt_detects_receipt(self) -> None:
        """_is_generic_receipt returns True for short receipt-only output."""
        from app.agents_system.langgraph.nodes.quality_gate import _is_generic_receipt

        assert _is_generic_receipt("Change set created and persisted.") is True

    def test_is_generic_receipt_rejects_long_output(self) -> None:
        """_is_generic_receipt returns False for longer architectural answer."""
        from app.agents_system.langgraph.nodes.quality_gate import _is_generic_receipt

        long_output = (
            "I recommend Azure Container Apps because of its scalability. "
            "The trade-offs involve cost vs AKS. Risks include cold starts. "
            "WAF: reliability covered. Change set persisted."
        )
        assert _is_generic_receipt(long_output) is False

    def test_propose_candidate_bypasses_artifact_edit_guard(self) -> None:
        """propose_candidate stage must run architecture checks even when artifact_edit_detected=False."""
        from app.agents_system.langgraph.nodes.quality_gate import completeness_check
        from unittest.mock import Mock

        # Simulate a case where artifact_edit_detected is False but stage is propose_candidate
        # A thin receipt answer with receipt keywords should still be caught by _is_generic_receipt
        step = Mock()
        step.tool = "aaa_generate_candidate_architecture"
        state: dict[str, Any] = {
            "next_stage": "propose_candidate",
            "agent_output": "Architecture persisted as pending change.",  # receipt language
            "artifact_edit_detected": False,  # guard that used to bypass architecture checks
            "intermediate_steps": [step],
            "quality_retry_count": 0,
            "handled_by_stage_worker": False,
        }
        result = completeness_check(state)
        # Must NOT return "continue" — propose_candidate must not bypass architecture quality checks
        assert result == "retry"


# ---------------------------------------------------------------------------
# Graph topology: architecture_planner routes through quality_check (P5/audit fix)
# ---------------------------------------------------------------------------

class TestArchitecturePlannerRouting:
    """Verify architecture_planner routes through quality_check, not directly to persist."""

    def test_architecture_planner_routes_to_quality_check(self) -> None:
        """architecture_planner edge must go to quality_check, not persist_messages."""
        from app.agents_system.langgraph.graph_factory import _build_project_chat_workflow
        from unittest.mock import MagicMock

        db = MagicMock()
        workflow = _build_project_chat_workflow(db, "test-msg-id")
        # edges are (source, target) tuples in the graph
        planner_targets = [e[1] for e in workflow.edges if e[0] == "architecture_planner"]
        assert "quality_check" in planner_targets, (
            "architecture_planner must route to quality_check for P5 gate to apply"
        )
        assert "persist_messages" not in planner_targets, (
            "architecture_planner must NOT bypass quality_check and go directly to persist_messages"
        )
