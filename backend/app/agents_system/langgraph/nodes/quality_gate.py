"""Quality gate node for LangGraph workflow.

Checks output completeness BEFORE persist_messages to avoid saving
bad/incomplete responses. Routes back to run_agent when the quality
gate fails, up to a configurable retry limit.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from app.shared.config.app_settings import get_app_settings

from ..state import GraphState

logger = logging.getLogger(__name__)

_AAA_PERSISTENCE_TOOLS = frozenset({
    "aaa_manage_artifacts",
    "aaa_generate_candidate_architecture",
    "aaa_manage_adr",
    "aaa_record_validation_results",
    "aaa_record_iac_artifacts",
    "aaa_record_cost_estimate",
    "aaa_create_diagram_set",
    "aaa_export_state",
})


def _get_quality_retry_max() -> int:
    """Read quality_retry_max from AppSettings."""
    try:
        return int(get_app_settings().quality_retry_max)
    except Exception:
        return 2


def _has_aaa_tool_calls(intermediate_steps: list[Any]) -> bool:
    """Check if any AAA persistence tool was called in intermediate steps."""
    for step in intermediate_steps:
        tool_name = ""
        if isinstance(step, dict):
            tool_name = str(step.get("tool", ""))
        elif isinstance(step, (list, tuple)) and len(step) >= 1:
            action = step[0]
            tool_name = getattr(action, "tool", "") or ""
        if tool_name in _AAA_PERSISTENCE_TOOLS:
            return True
    return False


def completeness_check(state: GraphState) -> Literal["retry", "continue"]:
    """Evaluate whether the agent output is complete enough to persist.

    Returns "retry" when:
    - artifact_edit_detected but no AAA tool was called
    - agent_output is empty or starts with ERROR:
    - quality_retry_count is below the limit

    Returns "continue" otherwise (pass through to persist).
    """
    artifact_edit = bool(state.get("artifact_edit_detected"))
    handled_by_worker = bool(state.get("handled_by_stage_worker"))
    agent_output = str(state.get("agent_output", "")).strip()
    intermediate_steps = state.get("intermediate_steps") or []
    retry_count = int(state.get("quality_retry_count", 0))
    max_retries = _get_quality_retry_max()

    # Stage workers have their own quality checks — skip
    if handled_by_worker:
        return "continue"

    # Already exhausted retries — accept whatever we have
    if retry_count >= max_retries:
        if agent_output or intermediate_steps:
            logger.info(
                "Quality gate: accepting output after %d retries", retry_count
            )
        return "continue"

    # ERROR prefix — always retry if under limit
    if agent_output.startswith("ERROR:"):
        logger.warning("Quality gate: error detected in output, retrying")
        return "retry"

    # No artifact edit expected — only retry on empty output or errors
    if not artifact_edit:
        return "continue"

    # Empty output when artifact edit expected — retry
    if not agent_output:
        logger.warning("Quality gate: empty agent output, retrying")
        return "retry"

    # Artifact edit was expected but no AAA tool was called
    if not _has_aaa_tool_calls(intermediate_steps):
        logger.warning(
            "Quality gate: artifact_edit_detected but no AAA tool called, retrying"
        )
        return "retry"

    return "continue"


def build_quality_retry(state: GraphState) -> dict[str, Any]:
    """Build state updates for a quality retry.

    Increments quality_retry_count and sets quality_retry_reason so
    the next agent invocation knows why it's being retried.
    """
    retry_count = int(state.get("quality_retry_count", 0))
    agent_output = str(state.get("agent_output", "")).strip()
    artifact_edit = bool(state.get("artifact_edit_detected"))

    reasons: list[str] = []
    if agent_output.startswith("ERROR:"):
        reasons.append(f"Previous attempt failed with: {agent_output[:200]}")
    elif not agent_output:
        reasons.append("Previous attempt produced empty output.")
    elif artifact_edit:
        reasons.append(
            "Previous attempt did not call any AAA persistence tool. "
            "You MUST use the appropriate aaa_ tool to persist artifacts."
        )

    reason = " ".join(reasons) if reasons else "Output quality was insufficient."

    logger.info(
        "Quality retry %d: %s", retry_count + 1, reason[:100]
    )

    return {
        "quality_retry_count": retry_count + 1,
        "quality_retry_reason": reason,
    }
