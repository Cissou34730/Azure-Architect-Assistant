"""
Stage routing and retry nodes for LangGraph workflow.

Phase 5: Add explicit stage routing and retry semantics.
"""

import logging
from enum import Enum
from typing import Any, Literal

from ..state import GraphState

logger = logging.getLogger(__name__)


class ProjectStage(str, Enum):
    """Project workflow stages."""
    CLARIFY = "clarify"
    PROPOSE_CANDIDATE = "propose_candidate"
    MANAGE_ADR = "manage_adr"
    VALIDATE = "validate"
    PRICING = "pricing"
    IAC = "iac"
    EXPORT = "export"


def classify_next_stage(state: GraphState) -> dict[str, Any]:
    """
    Classify which stage should be executed next.
    """
    user_message = (state.get("user_message") or "").lower()
    project_state = state.get("current_project_state") or {}
    agent_output = (state.get("agent_output") or "").lower()

    # 1. Keyword-based intent detection (highest priority)
    next_stage = _detect_intent_from_keywords(user_message, agent_output)

    # 2. State-aware defaults
    if next_stage is None:
        next_stage = _detect_intent_from_state(project_state)

    final_stage = next_stage or ProjectStage.CLARIFY
    logger.info(f"Classified next stage: {final_stage.value}")

    return {
        "next_stage": final_stage.value,
    }


def _detect_intent_from_keywords(user_message: str, agent_output: str) -> ProjectStage | None:
    """Detect intended stage from keywords in user message or agent output."""
    mapping = [
        (["adr", "decision", "record", "architecture decision"], ProjectStage.MANAGE_ADR),
        (["validate", "validation", "waf", "security", "compliance", "benchmark"], ProjectStage.VALIDATE),
        (["cost", "price", "pricing", "budget", "estimate"], ProjectStage.PRICING),
        (["terraform", "bicep", "iac", "infrastructure", "code"], ProjectStage.IAC),
        (["export", "document", "report", "summary"], ProjectStage.EXPORT),
    ]

    for keywords, stage in mapping:
        if any(kw in user_message for kw in keywords):
            return stage

    # Check agent output for proposal intents
    if any(kw in agent_output for kw in ["candidate", "solution", "propose", "suggest"]):
        return ProjectStage.PROPOSE_CANDIDATE

    return None


def _detect_intent_from_state(project_state: dict[str, Any]) -> ProjectStage:
    """Detect next stage based on gaps in current project state."""
    # List of required fields and their corresponding stages
    requirements = [
        ("requirements", ProjectStage.CLARIFY),
        ("candidateArchitectures", ProjectStage.PROPOSE_CANDIDATE),
        ("adrs", ProjectStage.MANAGE_ADR),
    ]

    for field, stage in requirements:
        if not project_state.get(field):
            return stage

    waf = project_state.get("wafChecklist") or {}
    if not project_state.get("findings") or not waf:
        return ProjectStage.VALIDATE

    # Post-validation stages
    post_val = [
        ("costEstimates", ProjectStage.PRICING),
        ("iacArtifacts", ProjectStage.IAC),
    ]

    for field, stage in post_val:
        if not project_state.get(field):
            return stage

    return ProjectStage.CLARIFY


def check_for_retry(state: GraphState) -> Literal["retry", "continue"]:
    """
    Check if agent output requires a retry.

    Phase 5: Detects ERROR: prefixes and suggests retry.

    Args:
        state: Current graph state

    Returns:
        "retry" if error detected, "continue" otherwise
    """
    agent_output = state.get("agent_output", "")
    retry_count = state.get("retry_count", 0)

    # Check for ERROR: prefix
    if agent_output.strip().startswith("ERROR:") and retry_count < 1:
        logger.warning("Error detected in agent output, suggesting retry")
        return "retry"

    return "continue"


def build_retry_prompt(state: GraphState) -> dict[str, Any]:
    """
    Build a retry prompt asking for missing fields.

    Phase 5: Extracts error and asks user to provide missing information.

    Args:
        state: Current graph state

    Returns:
        State update with retry prompt
    """
    agent_output = state.get("agent_output", "")
    retry_count = state.get("retry_count", 0)

    # Extract error message
    error_lines = [line for line in agent_output.split("\n") if line.strip().startswith("ERROR:")]
    error_message = error_lines[0] if error_lines else "An error occurred"

    retry_prompt = (
        f"{error_message}\n\n"
        f"Please provide the missing information or clarify your request."
    )

    logger.info(f"Built retry prompt (attempt {retry_count + 1})")

    return {
        "agent_output": retry_prompt,
        "retry_count": retry_count + 1,
    }


def _generate_next_step_questions(current_state: dict[str, Any]) -> list[str]:
    """Generate high-impact follow-up questions based on missing project artifacts."""
    questions = []
    if not current_state.get("candidateArchitectures"):
        questions.append(
            "Should we propose 1-2 candidate Azure architectures and generate the first C4 L1 diagram?"
        )
    if not current_state.get("adrs"):
        questions.append(
            "Which decisions should be captured as ADRs with WAF or diagram evidence?"
        )
    if not current_state.get("findings") or not current_state.get("wafChecklist"):
        questions.append(
            "Do you want validation against WAF + Azure Security Benchmark now?"
        )
    if not current_state.get("iacArtifacts"):
        questions.append(
            "Should we generate Terraform/Bicep for the proposed components?"
        )
    if not current_state.get("costEstimates"):
        questions.append("Do you need a cost estimate with key usage assumptions?")

    return questions[:5]


def propose_next_step(state: GraphState) -> dict[str, Any]:
    """
    Always propose next step if no artifact was persisted.

    Phase 5: Ensures system returns either persisted update or clarifying questions.

    Args:
        state: Current graph state

    Returns:
        State update with next step questions
    """
    combined_updates = state.get("combined_updates", {})
    final_answer = state.get("final_answer", "")

    # Check if any artifact was persisted
    artifact_keys = [
        "candidateArchitectures",
        "adrs",
        "findings",
        "iacArtifacts",
        "costEstimates",
        "diagrams",
    ]
    if any(combined_updates.get(k) for k in artifact_keys):
        return {}

    # Generate high-impact questions based on project state
    questions = _generate_next_step_questions(state.get("current_project_state", {}))

    if not questions:
        return {}

    next_step_prompt = "\n\n**Next steps to consider:**\n" + "\n".join(
        [f"- {q}" for q in questions]
    )

    logger.info(f"Proposed {len(questions)} next step questions")
    return {
        "final_answer": final_answer + next_step_prompt,
    }

