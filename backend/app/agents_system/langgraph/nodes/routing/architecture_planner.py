"""Architecture Planner routing and handoff logic."""

import logging
from typing import Any

from ...state import GraphState
from ..stage_routing import (
    _NON_ARCH_INTENT_KEYWORDS,
    COMPLEXITY_THRESHOLD,
    ProjectStage,
)
from ._helpers import format_requirements

logger = logging.getLogger(__name__)


def should_route_to_architecture_planner(state: GraphState) -> bool:
    """
    Determine if request should go to Architecture Planner sub-agent.

    Route to Architecture Planner when:
    - User explicitly requests "architecture", "design", "proposal"
    - Project stage suggests architecture planning needed
    - Complexity indicators detected (multi-region, HA, DR, compliance)

    Args:
        state: Current graph state

    Returns:
        True if should route to architecture planner
    """
    user_message = (state.get("user_message") or "").lower()
    next_stage = state.get("next_stage")

    # Stage guard: if workflow stage already indicates a non-architecture task,
    # do not hijack routing with complexity heuristics.
    blocked_stages = {
        ProjectStage.VALIDATE.value,
        ProjectStage.MANAGE_ADR.value,
        ProjectStage.PRICING.value,
        ProjectStage.IAC.value,
        ProjectStage.EXPORT.value,
    }
    if next_stage in blocked_stages:
        logger.info(
            "Skipping Architecture Planner routing: stage=%s indicates a non-architecture task",
            next_stage,
        )
        return False

    # Intent guard: explicit WAF/validation/checklist/pricing/IaC requests
    # should not be routed to Architecture Planner.
    if any(keyword in user_message for keyword in _NON_ARCH_INTENT_KEYWORDS):
        logger.info(
            "Skipping Architecture Planner routing: explicit non-architecture intent detected"
        )
        return False

    # Explicit architecture request keywords
    arch_keywords = [
        "architecture", "design the architecture", "propose architecture",
        "candidate architecture", "architecture proposal", "system design",
        "how should i architect", "what should the architecture look like",
        "design solution", "propose solution", "architecture diagram",
    ]

    if any(keyword in user_message for keyword in arch_keywords):
        logger.info("🎯 Routing to Architecture Planner: explicit request detected")
        return True

    # Check project stage
    if next_stage == ProjectStage.PROPOSE_CANDIDATE.value and any(
        kw in user_message for kw in ["architecture", "design", "propose", "solution"]
    ):
        logger.info("🎯 Routing to Architecture Planner: proposal stage + design request")
        return True

    # Check complexity indicators
    context_summary = state.get("context_summary") or ""
    project_state = state.get("current_project_state") or {}

    # Extract NFR requirements from project state
    requirements = project_state.get("requirements") or {}
    nfr_text = (context_summary + " " + str(requirements)).lower()

    complexity_indicators = [
        "multi-region", "high availability", "disaster recovery",
        "compliance", "soc 2", "hipaa", "gdpr", "pci dss",
        "microservices", "event-driven", "real-time",
        "99.9%", "99.95%", "99.99%",  # SLA indicators
        "global", "worldwide", "distributed",
    ]

    complexity_count = sum(1 for indicator in complexity_indicators if indicator in nfr_text)
    has_design_language = any(
        kw in user_message for kw in ["architecture", "design", "propose", "solution"]
    )
    if complexity_count >= COMPLEXITY_THRESHOLD and (
        next_stage == ProjectStage.PROPOSE_CANDIDATE.value or has_design_language
    ):
        logger.info(
            f"🎯 Routing to Architecture Planner: complexity threshold "
            f"({complexity_count} indicators)"
        )
        return True

    return False


def prepare_architecture_planner_handoff(state: GraphState) -> dict[str, Any]:
    """
    Prepare handoff context for Architecture Planner sub-agent.

    Extracts requirements, NFR constraints, and project context to pass
    to the specialized architecture planning agent.

    Args:
        state: Current graph state

    Returns:
        State update with agent_handoff_context
    """
    project_state = state.get("current_project_state") or {}
    context_summary = state.get("context_summary") or ""

    # Extract requirements (handle legacy dict or modern artifact list)
    requirements = project_state.get("requirements") or {}

    # Normalize for parameter extraction
    req_params = requirements if isinstance(requirements, dict) else {}

    requirements_text = format_requirements(requirements)

    # Extract NFR summary (handles both types)
    nfr_summary = _extract_nfr_summary(requirements, context_summary)

    # Extract constraints
    constraints = {
        "budget": req_params.get("budget"),
        "timeline": req_params.get("timeline"),
        "compliance": req_params.get("compliance", []),
        "regions": req_params.get("allowedRegions", []),
        "excluded_services": req_params.get("excludedServices", []),
    }
    # Remove None values
    constraints = {k: v for k, v in constraints.items() if v}

    # Extract previous architectural decisions
    previous_decisions = project_state.get("adrs") or []

    handoff_context = {
        "project_context": context_summary,
        "requirements": requirements_text,
        "nfr_summary": nfr_summary,
        "constraints": constraints,
        "previous_decisions": previous_decisions,
        "user_request": state.get("user_message", ""),
        "routing_reason": "Complex architecture design required with NFR analysis",
    }

    logger.info(
        f"Prepared Architecture Planner handoff context: "
        f"{len(nfr_summary)} chars NFR, {len(previous_decisions)} ADRs"
    )

    return {
        "agent_handoff_context": handoff_context,
        "current_agent": "architecture_planner",
    }


def _extract_nfr_summary(requirements: Any, context: str) -> str:
    """Extract non-functional requirements summary."""
    nfr_parts = _build_nfr_sections(requirements)
    return "\n".join(nfr_parts) if nfr_parts else "No explicit NFR requirements provided."


def _build_nfr_sections(requirements: Any) -> list[str]:
    """Build formatted NFR sections from requirements."""
    nfr_parts = []

    # Normalize for parameter extraction
    req_params = requirements if isinstance(requirements, dict) else {}

    performance = req_params.get("sla")
    if performance:
        nfr_parts.append(f"**Performance:** SLA target: {performance}")

    scale_info = _format_keyed_values(requirements, [("Users", "expectedUsers"), ("Data", "dataVolume")])
    if scale_info:
        nfr_parts.append(f"**Scalability:** {scale_info}")

    reliability_info = _format_keyed_values(requirements, [("RTO", "rto"), ("RPO", "rpo")])
    if reliability_info:
        nfr_parts.append(f"**Reliability:** {reliability_info}")

    compliance_list = req_params.get("compliance", []) if isinstance(req_params.get("compliance", []), list) else []
    if compliance_list:
        nfr_parts.append(f"**Security/Compliance:** {', '.join(compliance_list)}")

    budget = req_params.get("budget")
    if budget:
        nfr_parts.append(f"**Cost:** Budget constraint: {budget}")

    return nfr_parts


def _format_keyed_values(requirements: Any, labels: list[tuple[str, str]]) -> str | None:
    """Format a list of requirement keys as labeled values."""
    if not isinstance(requirements, dict):
        return None

    parts = []
    for label, key in labels:
        value = requirements.get(key)
        if value:
            parts.append(f"{label}: {value}")
    return ", ".join(parts) if parts else None
