"""
Research planning node for LangGraph workflow.

Builds a minimal research plan and stage directives to nudge the agent
to consult required references and MCP servers before answering.
"""

import logging
from typing import Any

from ..state import GraphState
from .stage_routing import ProjectStage

logger = logging.getLogger(__name__)


def _mindmap_gaps(mindmap_coverage: dict[str, Any]) -> list[str]:
    topics = []
    if not mindmap_coverage:
        return topics
    cov_topics = mindmap_coverage.get("topics")
    if not isinstance(cov_topics, dict):
        return topics
    for key, val in cov_topics.items():
        status = (val or {}).get("status")
        if status == "not-addressed":
            topics.append(key)
    return topics[:5]


async def build_research_plan_node(state: GraphState) -> dict[str, Any]:
    """
    Create a research plan and stage directives for the agent.

    Ensures every turn asks for at least one MCP lookup and at least one
    authoritative Azure reference citation.
    """
    state.get("user_message", "")
    stage_value = state.get("next_stage") or ProjectStage.CLARIFY.value
    mindmap_cov = state.get("mindmap_coverage") or {}

    plan: list[str] = []

    if stage_value == ProjectStage.PROPOSE_CANDIDATE.value:
        plan = [
            "Azure Architecture Center pattern relevant to the workload",
            "Azure Well-Architected Framework pillar alignment (reliability/security/cost)",
        ]
    elif stage_value == ProjectStage.MANAGE_ADR.value:
        plan = [
            "Azure decision trade-offs for the chosen services",
            "WAF checklist item evidence for this decision",
        ]
    elif stage_value == ProjectStage.VALIDATE.value:
        plan = [
            "Azure Well-Architected Framework checklist for the impacted pillar",
            "Azure Security Benchmark control mapping for the component",
        ]
    elif stage_value == ProjectStage.PRICING.value:
        plan = [
            "Azure Pricing meters/SKUs for involved services",
            "Cost optimization guidance from WAF cost pillar",
        ]
    elif stage_value == ProjectStage.IAC.value:
        plan = [
            "Bicep or Terraform examples for the core resources",
            "Required validations or linters for the chosen IaC",
        ]
    else:
        plan = [
            "Architecture Center overview for the workload type",
            "WAF pillar checklist starting point",
        ]

    gaps = _mindmap_gaps(mindmap_cov)
    if gaps:
        plan.append(f"Mind map gaps to cover: {', '.join(gaps)}")

    stage_directives = (
        f"Stage: {stage_value}. Always execute at least one MCP search and one MCP fetch "
        f"aligned to the research plan, then cite the exact document names/URLs and WAF/ASB topics. "
        f"Never refuse; if data is missing, ask focused clarifications and propose 2-3 options with trade-offs."
    )

    logger.info(
        "Built research plan (stage=%s, items=%d)", stage_value, len(plan)
    )
    return {
        "research_plan": plan,
        "stage_directives": stage_directives,
    }

