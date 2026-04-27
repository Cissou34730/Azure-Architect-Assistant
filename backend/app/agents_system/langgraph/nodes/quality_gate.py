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


_RECEIPT_KEYWORDS = frozenset({
    "change set", "changeset", "created", "persisted", "pending change",
})

_ARCHITECTURE_CHECKS: list[tuple[str, list[str]]] = [
    ("Recommendation (recommend/suggest/propose)", ["recommend", "suggest", "propose"]),
    ("Service rationale (because/rationale/chosen/selected)", ["because", "rationale", "chosen", "selected"]),
    ("NFR mapping (nfr/availability/scalability/reliability/performance)", ["nfr", "availability", "scalability", "reliability", "performance"]),
    ("Trade-offs (trade-off/tradeoff/trade off/compromise/drawback)", ["trade-off", "tradeoff", "trade off", "compromise", "drawback"]),
    ("Risks (risk/concern/caveat/limitation)", ["risk", "concern", "caveat", "limitation"]),
    ("WAF impact (waf/well-architected/pillar)", ["waf", "well-architected", "pillar"]),
    ("Citations/evidence (citation/evidence/reference/microsoft/learn.microsoft)", ["citation", "evidence", "reference", "microsoft", "learn.microsoft"]),
    ("Persisted artifact (aaa_generate_candidate/candidate architecture/pending change/persisted)", ["aaa_generate_candidate", "candidate architecture", "pending change", "persisted"]),
]


def _is_propose_candidate_stage(state: GraphState) -> bool:
    """Return True when the current stage is propose_candidate."""
    return state.get("next_stage") == "propose_candidate"


def _check_architecture_answer_quality(agent_output: str) -> list[str]:
    """Return list of missing section labels for architecture quality checks.

    Only runs when the output is longer than 100 chars (short outputs are
    clearly receipt-only and handled separately by _is_generic_receipt).
    """
    if len(agent_output) <= 100:
        return []
    lower = agent_output.lower()
    missing: list[str] = []
    for label, keywords in _ARCHITECTURE_CHECKS:
        if not any(kw in lower for kw in keywords):
            missing.append(label)
    return missing


def _is_generic_receipt(agent_output: str) -> bool:
    """Return True when output is a short change-set receipt with no architecture.

    Criteria: shorter than 200 chars AND contains receipt language WITHOUT
    any architectural explanation.
    """
    if len(agent_output) >= 200:
        return False
    lower = agent_output.lower()
    has_receipt = any(kw in lower for kw in _RECEIPT_KEYWORDS)
    # If it also contains architectural explanation keywords, not a pure receipt
    arch_signals = ["recommend", "because", "trade-off", "tradeoff", "risk", "waf", "pillar", "scalab", "availab"]
    has_arch = any(kw in lower for kw in arch_signals)
    return has_receipt and not has_arch


def _has_aaa_tool_calls(intermediate_steps: list[Any]) -> bool:
    """Check if any AAA persistence tool was called in intermediate steps."""
    for step in intermediate_steps:
        tool_name = ""
        if isinstance(step, dict):
            tool_name = str(step.get("tool", ""))
        elif isinstance(step, (list, tuple)) and len(step) >= 1:
            action = step[0]
            tool_name = getattr(action, "tool", "") or ""
        else:
            # Direct action object (e.g. AgentAction or similar)
            tool_name = str(getattr(step, "tool", "") or "")
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

    # propose_candidate stage: check architecture answer quality
    if _is_propose_candidate_stage(state):
        missing = _check_architecture_answer_quality(agent_output)
        if missing:
            logger.warning(
                "Quality gate: architecture answer missing sections: %s", missing
            )
            return "retry"
        if _is_generic_receipt(agent_output):
            logger.warning("Quality gate: architecture answer is a generic receipt")
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

    # propose_candidate: give specific missing-sections feedback
    if _is_propose_candidate_stage(state):
        missing = _check_architecture_answer_quality(agent_output)
        if missing or _is_generic_receipt(agent_output):
            missing_str = ", ".join(missing) if missing else "all required sections"
            reason = (
                f"Architecture answer is incomplete. Missing sections: [{missing_str}]. "
                "Your response MUST include: Recommendation, Why this fits the project, "
                "Key trade-offs, Main risks and mitigations, WAF impact, Cost drivers. "
                "Do NOT just return a receipt. Provide a decision-quality architectural briefing."
            )
            logger.info("Quality retry %d: %s", retry_count + 1, reason[:100])
            return {
                "quality_retry_count": retry_count + 1,
                "quality_retry_reason": reason,
            }

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
