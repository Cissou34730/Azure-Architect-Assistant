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

DISCOVERY_STAGES = {
    ProjectStage.CLARIFY.value,
    ProjectStage.PROPOSE_CANDIDATE.value,
}
MINDMAP_PROMPT_BUDGET = 2


def _mindmap_gaps(mindmap_coverage: dict[str, Any]) -> list[str]:
    topics: list[str] = []
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


def _waf_snapshot(state: GraphState) -> str:
    project_state = state.get("current_project_state") or {}
    waf = project_state.get("wafChecklist")
    if not isinstance(waf, dict):
        return "WAF checklist unavailable."

    items_raw = waf.get("items")
    items = items_raw.values() if isinstance(items_raw, dict) else items_raw
    if not isinstance(items, list):
        return "WAF checklist unavailable."

    total = len(items)
    fixed = 0
    in_progress = 0
    open_items = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        evals = item.get("evaluations")
        latest = evals[-1] if isinstance(evals, list) and evals else None
        status = str((latest or {}).get("status", "open")).lower()
        if status in {"fixed", "false_positive"}:
            fixed += 1
        elif status == "in_progress":
            in_progress += 1
        else:
            open_items += 1
    return (
        "WAF status snapshot: "
        f"total={total}, fixed={fixed}, in_progress={in_progress}, open={open_items}."
    )


def _build_mindmap_guidance(
    stage_value: str,
    mindmap_coverage: dict[str, Any],
) -> dict[str, Any] | None:
    gaps = _mindmap_gaps(mindmap_coverage)
    if not gaps:
        return None

    is_discovery = stage_value in DISCOVERY_STAGES
    prompts = []
    for topic in gaps[:MINDMAP_PROMPT_BUDGET]:
        if is_discovery:
            prompts.append(
                f"To de-risk the architecture early, should we confirm the '{topic}' domain next?"
            )
        else:
            prompts.append(
                f"Optional architecture follow-up: would you like to review '{topic}' after this step?"
            )

    return {
        "mode": "advisory",
        "non_blocking": True,
        "priority": "high" if is_discovery else "balanced",
        "focus_topics": gaps,
        "suggested_prompts": prompts,
    }


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

    mindmap_guidance = _build_mindmap_guidance(stage_value, mindmap_cov)

    stage_directives = (
        f"Stage: {stage_value}. Always execute at least one MCP search and one MCP fetch "
        f"aligned to the research plan, then cite the exact document names/URLs and WAF/ASB topics. "
        f"Never refuse; if data is missing, ask focused clarifications and propose 2-3 options with trade-offs."
    )
    stage_directives += (
        "\nChecklist-first rule: Treat WAF checklist as a first-class artifact. "
        "When the user reports completion/progress/regression for a pillar or topic, persist checklist updates in AAA_STATE_UPDATE "
        "using aaa_record_validation_results (or deterministic shortcut if available), and include a risk warning when evidence is weak. "
        "If analysis suggests a legitimate checklist status change, apply it proactively; if evidence is not enough, ask for the missing status/evidence explicitly."
    )
    stage_directives += f"\n{_waf_snapshot(state)}"
    stage_directives += (
        "\nGuidance policy: mindmap prompts are advisory only and must never block the workflow. "
        "When validation or checklist execution is active, checklist persistence and evidence handling take priority."
    )

    if stage_value == ProjectStage.VALIDATE.value:
        stage_directives += (
            "\n\nValidation persistence requirements (mandatory):\n"
            "- Consult the WAF knowledge base using kb_search or kb_search_agent (at least one query).\n"
            "- Then call aaa_record_validation_results with a NON-EMPTY payload.wafEvaluations array.\n"
            "- Use status values: fixed | in_progress | open.\n"
            "- findings may be empty; if you include findings, each finding must include at least one sourceCitations entry.\n\n"
            "Example payload (minimum):\n"
            "{\n"
            "  \"wafEvaluations\": [\n"
            "    {\n"
            "      \"itemId\": \"waf-security-identity-1\",\n"
            "      \"pillar\": \"Security\",\n"
            "      \"topic\": \"Identity and access management\",\n"
            "      \"status\": \"in_progress\",\n"
            "      \"evidence\": \"Current design mentions Entra ID SSO but lacks conditional access and MFA enforcement details.\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )

    logger.info(
        "Built research plan (stage=%s, items=%d)", stage_value, len(plan)
    )
    return {
        "research_plan": plan,
        "stage_directives": stage_directives,
        "mindmap_guidance": mindmap_guidance,
    }


def _format_requirement_targets(requirements: Any) -> list[str]:
    if isinstance(requirements, list):
        targets = []
        for requirement in requirements:
            if isinstance(requirement, dict):
                title = requirement.get("title") or requirement.get("text") or requirement.get("id")
                if title:
                    targets.append(str(title))
            elif requirement:
                targets.append(str(requirement))
        return targets[:5]

    if isinstance(requirements, dict):
        targets = []
        for key in ("workloadType", "sla", "rto", "rpo", "dataVolume", "expectedUsers"):
            value = requirements.get(key)
            if value:
                targets.append(f"{key}: {value}")
        return targets[:5]

    return []


def _preferred_sources_for_stage(stage_value: str) -> list[str]:
    if stage_value == ProjectStage.PROPOSE_CANDIDATE.value:
        return [
            "Azure Architecture Center",
            "Azure Well-Architected Framework",
            "Service-specific Microsoft Learn guidance",
        ]
    return [
        "Azure Well-Architected Framework",
        "Microsoft Learn",
    ]


def _build_evidence_packet(
    *,
    index: int,
    plan_item: str,
    stage_value: str,
    state: GraphState,
) -> dict[str, Any]:
    project_state = state.get("current_project_state") or {}
    requirements = project_state.get("requirements") or []
    mindmap_topics = _mindmap_gaps(state.get("mindmap_coverage") or {})
    context_summary = str(state.get("context_summary") or "")

    packet_id = f"research-packet-{index}"
    query = f"{stage_value.replace('_', ' ')}: {plan_item}"
    if context_summary:
        query = f"{query} | context: {context_summary[:160]}"

    expected_evidence = [
        "Document the Azure service or pattern decision this packet should justify.",
        "Capture at least one authoritative Microsoft or WAF source for the packet topic.",
        "Record trade-offs or constraints the architecture synthesizer must preserve.",
    ]
    if mindmap_topics:
        expected_evidence.append(
            f"Address these uncovered mind map topics when relevant: {', '.join(mindmap_topics[:3])}."
        )

    return {
        "packet_id": packet_id,
        "focus": plan_item,
        "query": query,
        "stage": stage_value,
        "requirement_targets": _format_requirement_targets(requirements),
        "mindmap_topics": mindmap_topics,
        "recommended_sources": _preferred_sources_for_stage(stage_value),
        "expected_evidence": expected_evidence,
        "consumer_guidance": (
            "Use this packet to ground architecture choices in explicit evidence, "
            "not generic Azure defaults."
        ),
    }


async def execute_research_worker_node(state: GraphState) -> dict[str, Any]:
    """Materialize research plan items into concrete evidence packets for synthesis."""
    stage_value = state.get("next_stage") or ProjectStage.CLARIFY.value
    plan = state.get("research_plan") or []

    if stage_value != ProjectStage.PROPOSE_CANDIDATE.value:
        return {
            "research_evidence_packets": [],
            "research_execution_artifact": {
                "status": "skipped",
                "reason": "unsupported_stage",
                "stage": stage_value,
                "packets_created": 0,
            },
        }

    if not plan:
        return {
            "research_evidence_packets": [],
            "research_execution_artifact": {
                "status": "skipped",
                "reason": "no_research_plan",
                "stage": stage_value,
                "packets_created": 0,
            },
        }

    packets = [
        _build_evidence_packet(
            index=index,
            plan_item=plan_item,
            stage_value=stage_value,
            state=state,
        )
        for index, plan_item in enumerate(plan, start=1)
    ]

    logger.info(
        "Built research worker evidence packets (stage=%s, packets=%d)",
        stage_value,
        len(packets),
    )
    return {
        "research_evidence_packets": packets,
        "research_execution_artifact": {
            "status": "completed",
            "stage": stage_value,
            "packets_created": len(packets),
            "plan_items": len(plan),
        },
    }

