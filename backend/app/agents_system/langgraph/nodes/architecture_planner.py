"""
Architecture Planner Node - Specialized agent for architecture design.

This module provides a specialized sub-agent for handling complex architecture
design requests with NFR analysis and diagram generation.
"""

import logging
from typing import Any

from app.agents_system.config.prompt_loader import PromptLoader
from app.agents_system.runner import get_agent_runner
from app.agents_system.tools.research_tool import normalize_grounded_research_packet

from ..state import GraphState
from .agent_native import run_stage_aware_agent

logger = logging.getLogger(__name__)
_ARCHITECTURE_PLANNER_PROMPT = "architecture_planner_prompt.yaml"


def _append_grounded_evidence_lines(lines: list[str], packet: Any) -> None:
    consulted_sources = getattr(packet, "consulted_sources", [])
    if consulted_sources:
        lines.append(
            "  Consulted sources: "
            + ", ".join(str(source) for source in consulted_sources[:3])
        )

    evidence_items = getattr(packet, "evidence", [])
    if not evidence_items:
        return

    lines.append("  Grounded evidence:")
    for evidence_item in evidence_items[:2]:
        lines.append(f"    - {evidence_item.title}")
        if evidence_item.excerpt:
            lines.append(f"      Excerpt: {evidence_item.excerpt[:180]}")
        if evidence_item.url:
            lines.append(f"      URL: {evidence_item.url}")


def _format_research_evidence_packets(packets: list[dict[str, Any]]) -> str:
    if not packets:
        return "No research evidence packets were prepared."

    lines: list[str] = []
    for raw_packet in packets[:5]:
        packet = normalize_grounded_research_packet(raw_packet)
        if packet is None:
            continue

        lines.append(f"- {packet.packet_id}: {packet.focus}")
        if packet.query:
            lines.append(f"  Query: {packet.query}")
        if packet.requirement_targets:
            lines.append(
                "  Requirement targets: "
                + ", ".join(str(target) for target in packet.requirement_targets[:3])
            )
        if packet.recommended_sources:
            lines.append(
                "  Preferred sources: "
                + ", ".join(str(source) for source in packet.recommended_sources[:3])
            )
        _append_grounded_evidence_lines(lines, packet)

    return "\n".join(lines) if lines else "No research evidence packets were prepared."


def _format_mindmap_delta_targets(mindmap_guidance: dict[str, Any] | None) -> str:
    if not isinstance(mindmap_guidance, dict):
        return "No explicit mind map gaps were provided."

    lines: list[str] = []
    focus_topics = mindmap_guidance.get("focus_topics")
    if isinstance(focus_topics, list) and focus_topics:
        lines.append("Focus topics: " + ", ".join(str(topic) for topic in focus_topics[:5]))

    suggested_prompts = mindmap_guidance.get("suggested_prompts")
    if isinstance(suggested_prompts, list) and suggested_prompts:
        lines.append("Suggested prompts:")
        lines.extend(f"- {prompt}" for prompt in suggested_prompts[:2])

    return "\n".join(lines) if lines else "No explicit mind map gaps were provided."


def _format_waf_snapshot(project_state: dict[str, Any]) -> str:
    waf = project_state.get("wafChecklist")
    if not isinstance(waf, dict):
        return "WAF checklist unavailable."

    raw_items = waf.get("items")
    items = raw_items.values() if isinstance(raw_items, dict) else raw_items
    if not isinstance(items, list):
        return "WAF checklist unavailable."

    total = len(items)
    fixed = 0
    in_progress = 0
    open_items = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        evaluations = item.get("evaluations")
        latest = evaluations[-1] if isinstance(evaluations, list) and evaluations else None
        status = str((latest or {}).get("status") or "open").strip().lower()
        if status in {"fixed", "false_positive"}:
            fixed += 1
        elif status == "in_progress":
            in_progress += 1
        else:
            open_items += 1

    return (
        f"WAF status snapshot: total={total}, fixed={fixed}, "
        f"in_progress={in_progress}, open={open_items}."
    )


def _format_research_execution_artifact(artifact: dict[str, Any] | None) -> str:
    if not isinstance(artifact, dict) or not artifact:
        return "No research execution artifact recorded."

    lines: list[str] = []
    for key in ("status", "stage", "packets_created", "reason"):
        value = artifact.get(key)
        if value is not None:
            lines.append(f"- {key}: {value}")

    return "\n".join(lines) if lines else "No research execution artifact recorded."


def _build_synthesizer_contract(state: GraphState, handoff_context: dict[str, Any]) -> str:
    return (
        "**Required Output Contract:**\n"
        "- Default to exactly 1 candidate unless the user explicitly asks for more.\n"
        "- Use explicit section headings: Executive Recommendation, Workload Classification, Target Topology, "
        "Azure Service-by-Service Rationale, Evidence Packet Consumption, Assumptions linked to requirements, "
        "Trade-offs, Alternatives Rejected, Risks and Mitigations, "
        "System Context Diagram [Target Architecture], Container Diagram [Target Architecture], "
        "NFR Achievement Summary, WAF Pillar Mapping, NFR Achievement Matrix, "
        "Cost Drivers, Operational Model, Security Model, "
        "ADR Candidates, Implementation Phases, "
        "WAF Delta, Mindmap Delta, Citations, Persisted Artifacts Summary.\n"
        "- Executive Recommendation: 1-2 sentences stating the recommended approach and primary reason.\n"
        "- Workload Classification: classify compute type, data tier, integration pattern, deployment model.\n"
        "- Azure Service-by-Service Rationale: for each key service, state why chosen, which NFR it satisfies, and one alternative considered.\n"
        "- Alternatives Rejected: at least 2 alternatives with explicit Azure-specific reasons why rejected.\n"
        "- Risks and Mitigations: at least 3 identified risks with concrete mitigations.\n"
        "- WAF Pillar Mapping: for each of the 5 WAF pillars, state how it is addressed or explicitly deferred.\n"
        "- NFR Achievement Matrix: table mapping each NFR to achieved/partially/deferred.\n"
        "- Cost Drivers: top 3-5 cost drivers with their optimization levers.\n"
        "- Operational Model: deployment pipeline, monitoring, alerting approach.\n"
        "- Security Model: identity, network, data encryption, compliance posture.\n"
        "- ADR Candidates: identify decisions for hosting model, database choice, identity model, "
        "network exposure model, regional/DR strategy, integration pattern, observability approach. "
        "Each candidate must reference the architecture ID and decision domain.\n"
        "- Implementation Phases: at least Phase 1 (Foundation) and Phase 2 (Full Target).\n"
        "- For C4 artifacts, produce Mermaid System Context and Container diagrams whenever the workload boundary is known; "
        "if a diagram is not applicable, say why.\n"
        "- Make assumptions traceable to requirements or evidence packets.\n"
        "- Make trade-offs specific to Azure service choices, not generic pros/cons.\n"
        "- Keep WAF delta specific: name the affected pillar/checklist themes and what changed.\n"
        "- Keep mindmap delta specific: name the uncovered topics addressed now vs. left open.\n"
        "- Persist reviewable artifacts through aaa_create_diagram_set and aaa_generate_candidate_architecture so the pending-change review flow records typed pending-change confirmations.\n"
        "\n"
        "**WAF Snapshot:**\n"
        f"{_format_waf_snapshot(state.get('current_project_state') or {})}\n\n"
        "**Mind Map Delta Targets:**\n"
        f"{_format_mindmap_delta_targets(state.get('mindmap_guidance'))}\n\n"
        "**Research Execution Artifact:**\n"
        f"{_format_research_execution_artifact(handoff_context.get('research_execution_artifact'))}"
    )


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def _build_synthesis_execution_artifact(
    *,
    state: GraphState,
    agent_output: str,
    success: bool,
    error: str | None,
    research_packets_supplied: int,
) -> dict[str, Any]:
    required_sections = {
        # Original sections
        "assumptions": _contains_any(
            agent_output,
            ("## assumptions linked to requirements", "## assumptions"),
        ),
        "trade_offs": _contains_any(
            agent_output,
            ("## trade-offs", "## tradeoffs"),
        ),
        "citations": _contains_any(
            agent_output,
            ("## citations", "source citations"),
        ),
        "waf_delta": _contains_any(
            agent_output,
            ("## waf delta", "waf delta"),
        ),
        "mindmap_delta": _contains_any(
            agent_output,
            ("## mindmap delta", "mind map delta"),
        ),
        "c4_system_context": _contains_any(
            agent_output,
            ("## system context diagram [target architecture]", "## system context diagram", "c4 system context"),
        ),
        "c4_container": _contains_any(
            agent_output,
            ("## container diagram [target architecture]", "## container diagram", "c4 container"),
        ),
        "state_update": "aaa_state_update" in agent_output.lower(),
        # P3: Consulting-quality sections
        "executive_recommendation": _contains_any(
            agent_output,
            ("## executive recommendation",),
        ),
        "workload_classification": _contains_any(
            agent_output,
            ("## workload classification",),
        ),
        "alternatives_rejected": _contains_any(
            agent_output,
            ("## alternatives rejected",),
        ),
        "risks_and_mitigations": _contains_any(
            agent_output,
            ("## risks and mitigations",),
        ),
        "waf_pillar_mapping": _contains_any(
            agent_output,
            ("## waf pillar mapping",),
        ),
        "nfr_achievement_matrix": _contains_any(
            agent_output,
            ("## nfr achievement matrix", "## nfr achievement"),
        ),
        "cost_drivers": _contains_any(
            agent_output,
            ("## cost drivers",),
        ),
        "operational_model": _contains_any(
            agent_output,
            ("## operational model",),
        ),
        "security_model": _contains_any(
            agent_output,
            ("## security model",),
        ),
        # P11: ADR candidate detection
        "adr_candidates": _contains_any(
            agent_output,
            ("## adr candidates",),
        ),
        "implementation_phases": _contains_any(
            agent_output,
            ("## implementation phases", "## implementation phase"),
        ),
    }
    missing_sections = [key for key, present in required_sections.items() if not present]
    artifact = {
        "status": "completed" if success else "failed",
        "stage": state.get("next_stage") or "propose_candidate",
        "prompt": _ARCHITECTURE_PLANNER_PROMPT,
        "review_mode": "postprocess_pending_changes",
        "research_packets_supplied": research_packets_supplied,
        "mindmap_guidance_supplied": bool(state.get("mindmap_guidance")),
        "required_sections": required_sections,
        "missing_sections": missing_sections,
    }
    if error:
        artifact["error"] = error
    return artifact


async def architecture_planner_node(state: GraphState) -> dict[str, Any]:
    """
    Specialized node for architecture planning and diagram generation.

    This node is invoked when:
    - User requests architecture proposal
    - Project stage is "propose_candidate"
    - Complexity threshold exceeded

    The Architecture Planner specializes in:
    - Target architecture design (complete, production-ready)
    - NFR analysis (Scalability, Performance, Security, Reliability, Maintainability)
    - C4 model diagrams (System Context, Container)
    - Functional flow diagrams (user journeys, business processes)
    - Phased delivery planning (MVP when requested)

    Args:
        state: Current graph state with project context

    Returns:
        Updated state with architecture proposal
    """
    logger.info("🏗️ Architecture Planner Agent activated")

    try:
        # Load architecture planner prompt
        prompt_loader = PromptLoader()
        arch_planner_prompt = prompt_loader.load_prompt_file(_ARCHITECTURE_PLANNER_PROMPT)

        # Prepare handoff context for architecture planner
        handoff_context = state.get("agent_handoff_context", {})
        project_context = handoff_context.get("project_context", "")
        requirements = handoff_context.get("requirements", "")
        nfr_summary = handoff_context.get("nfr_summary", "")
        constraints = handoff_context.get("constraints", {})
        previous_decisions = handoff_context.get("previous_decisions", [])
        research_evidence_packets = handoff_context.get("research_evidence_packets", [])
        synthesizer_contract = _build_synthesizer_contract(state, handoff_context)

        # Get user's original request
        user_message = state.get("user_message", "")

        # Construct comprehensive input for architecture planner
        arch_planner_input = f"""
{user_message}

**Context from Main Agent:**

**Project Context:**
{project_context}

**Requirements:**
{requirements}

**Non-Functional Requirements (NFR):**
{nfr_summary}

**Constraints:**
{_format_constraints(constraints)}

**Previous Architectural Decisions (ADRs):**
{_format_previous_decisions(previous_decisions)}

**Research Evidence Packets:**
{_format_research_evidence_packets(research_evidence_packets)}

{synthesizer_contract}

---

**Task:** Design the complete target architecture for this project. Include all mandatory sections:

1. **Executive Recommendation** (1-2 sentences: recommended approach + primary reason)
2. **Workload Classification** (compute type, data tier, integration pattern, deployment model)
3. **Target Topology** (structural pattern)
4. **Azure Service-by-Service Rationale** (why chosen, NFR satisfied, alternative considered)
5. **Exactly 1 evidence-backed candidate by default** (produce more only when the user explicitly requests alternatives)
6. **Evidence Packet Consumption** section mapping packet ids to architecture decisions
7. **Assumptions linked to requirements**
8. **Trade-offs** explicitly stated (Azure-specific, not generic)
9. **Alternatives Rejected** (at least 2, with explicit reasons)
10. **Risks and Mitigations** (at least 3 risks with concrete mitigations)
11. **System Context Diagram** [Target Architecture]
12. **Container Diagram** [Target Architecture]
13. **NFR Achievement Summary**
14. **WAF Pillar Mapping** (all 5 pillars: addressed or deferred)
15. **NFR Achievement Matrix** (table: NFR vs achieved/partially/deferred)
16. **Cost Drivers** (top 3-5 with optimization levers)
17. **Operational Model** (deployment pipeline, monitoring, alerting)
18. **Security Model** (identity, network, data encryption, compliance)
19. **ADR Candidates** (hosting model, database choice, identity model, network exposure, regional/DR strategy, integration pattern, observability)
20. **Implementation Phases** (at least Phase 1: Foundation and Phase 2: Full Target)
21. **WAF Delta** + **Mindmap Delta**
22. **User Journey Flow** (if user-facing system)
23. **NFR Analysis** for each diagram (Scalability, Performance, Security, Reliability, Maintainability, Trade-offs)
24. Persist reviewable artifacts with aaa_create_diagram_set and aaa_generate_candidate_architecture once the proposal is ready
25. After presenting target, ask if user wants MVP path

Ensure all diagrams use valid Mermaid syntax and include comprehensive NFR analysis.
"""

        logger.info("Architecture Planner invoking LangGraph-native agent...")

        runner = await get_agent_runner()
        planner_state: GraphState = dict(state)
        planner_state["user_message"] = arch_planner_input
        planner_state["stage_directives"] = str(arch_planner_prompt.get("system_prompt", ""))

        result = await run_stage_aware_agent(
            planner_state,
            mcp_client=getattr(runner, "mcp_client", None),
            openai_settings=getattr(runner, "openai_settings", None),
        )

        arch_proposal = str(result.get("agent_output", ""))
        intermediate_steps = result.get("intermediate_steps", [])
        success = bool(result.get("success", True))
        error = result.get("error")
        execution_artifact = _build_synthesis_execution_artifact(
            state=state,
            agent_output=arch_proposal,
            success=success,
            error=error if isinstance(error, str) else None,
            research_packets_supplied=len(research_evidence_packets),
        )

        logger.info(f"✅ Architecture Planner completed with {len(intermediate_steps)} tool calls")

        return {
            "agent_output": arch_proposal,
            "intermediate_steps": state.get("intermediate_steps", []) + intermediate_steps,
            "current_agent": "architecture_planner",
            "sub_agent_output": arch_proposal,
            "success": success,
            "error": error,
            "architecture_synthesis_execution_artifact": execution_artifact,
        }

    except Exception as exc:
        logger.error(f"❌ Architecture Planner failed: {exc}", exc_info=True)

        # Graceful fallback: Return error but don't break the workflow
        error_msg = (
            f"Architecture Planner encountered an error: {exc!s}\n\n"
            "Falling back to main agent for architecture planning. "
            "The main agent will provide a best-effort architecture proposal."
        )

        return {
            "agent_output": error_msg,
            "current_agent": "main",  # Fallback to main agent
            "sub_agent_output": None,
            "success": False,
            "error": str(exc),
            "architecture_synthesis_execution_artifact": {
                "status": "failed",
                "stage": state.get("next_stage") or "propose_candidate",
                "prompt": _ARCHITECTURE_PLANNER_PROMPT,
                "reason": "runtime_error",
                "review_mode": "postprocess_pending_changes",
            },
        }


def _format_constraints(constraints: dict[str, Any]) -> str:
    """Format constraints dictionary for display."""
    if not constraints:
        return "No explicit constraints provided."

    formatted = []
    if "budget" in constraints:
        formatted.append(f"- Budget: {constraints['budget']}")
    if "timeline" in constraints:
        formatted.append(f"- Timeline: {constraints['timeline']}")
    if "compliance" in constraints:
        formatted.append(f"- Compliance: {', '.join(constraints['compliance'])}")
    if "regions" in constraints:
        formatted.append(f"- Allowed Regions: {', '.join(constraints['regions'])}")
    if "excluded_services" in constraints:
        formatted.append(f"- Excluded Services: {', '.join(constraints['excluded_services'])}")

    return "\n".join(formatted) if formatted else "No explicit constraints provided."


def _format_previous_decisions(decisions: list[dict[str, Any]]) -> str:
    """Format previous ADRs for display."""
    if not decisions:
        return "No previous architectural decisions recorded."

    formatted = []
    for idx, decision in enumerate(decisions, 1):
        title = decision.get("title", "Untitled Decision")
        rationale = decision.get("rationale", "No rationale provided")
        formatted.append(f"{idx}. **{title}**\n   Rationale: {rationale}")
    return "\n".join(formatted)


