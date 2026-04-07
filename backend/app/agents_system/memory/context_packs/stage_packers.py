"""Per-stage context pack builders.

Each function returns the ordered list of ContextSections appropriate
for that workflow stage, with priorities for budget-based dropping.
"""

from __future__ import annotations

from typing import Any

from .schema import ContextSection
from .shared_sections import (
    build_data_compliance_section,
    build_open_questions_section,
    build_project_facts_section,
    build_requirements_section,
    build_thread_summary_section,
)

_MAX_INCOMPLETE_WAF_ITEMS = 5


def build_clarify_sections(
    state: dict[str, Any], thread_summary: str | None = None,
) -> list[ContextSection]:
    """Context for clarification stage: focus on gaps and ambiguities."""
    sections = [
        build_project_facts_section(state),
        build_thread_summary_section(thread_summary),
        build_open_questions_section(state),
        _build_clarification_questions_section(state),
        build_requirements_section(state),
    ]
    return [s for s in sections if s.content.strip()]


def build_propose_candidate_sections(
    state: dict[str, Any], thread_summary: str | None = None,
) -> list[ContextSection]:
    """Context for architecture proposal: full requirements + constraints."""
    sections = [
        build_project_facts_section(state),
        build_thread_summary_section(thread_summary),
        build_requirements_section(state),
        _build_constraints_section(state),
        build_data_compliance_section(state),
        build_open_questions_section(state),
    ]
    return [s for s in sections if s.content.strip()]


def build_manage_adr_sections(
    state: dict[str, Any], thread_summary: str | None = None,
) -> list[ContextSection]:
    """Context for ADR management: decisions and trade-offs."""
    sections = [
        build_project_facts_section(state),
        build_thread_summary_section(thread_summary),
        _build_decisions_section(state),
        build_requirements_section(state),
        _build_constraints_section(state),
    ]
    return [s for s in sections if s.content.strip()]


def build_validate_sections(
    state: dict[str, Any], thread_summary: str | None = None,
) -> list[ContextSection]:
    """Context for validation: WAF deltas, risks, checklist."""
    sections = [
        build_project_facts_section(state),
        build_thread_summary_section(thread_summary),
        _build_waf_checklist_section(state),
        build_open_questions_section(state),
        build_requirements_section(state),
    ]
    return [s for s in sections if s.content.strip()]


def build_pricing_sections(
    state: dict[str, Any], thread_summary: str | None = None,
) -> list[ContextSection]:
    """Context for pricing: services, assumptions, budget."""
    sections = [
        build_project_facts_section(state),
        build_thread_summary_section(thread_summary),
        _build_pricing_assumptions_section(state),
        build_requirements_section(state),
    ]
    return [s for s in sections if s.content.strip()]


def build_iac_sections(
    state: dict[str, Any], thread_summary: str | None = None,
) -> list[ContextSection]:
    """Context for IaC generation: finalized design choices."""
    sections = [
        build_project_facts_section(state),
        build_thread_summary_section(thread_summary),
        _build_constraints_section(state),
        build_data_compliance_section(state),
        _build_decisions_section(state),
        build_requirements_section(state),
    ]
    return [s for s in sections if s.content.strip()]


# ── Private helpers ──────────────────────────────────────────────────────────

def _build_clarification_questions_section(state: dict[str, Any]) -> ContextSection:
    questions = state.get("clarificationQuestions", [])
    if not questions:
        return ContextSection(name="clarification_questions", content="", priority=2)
    lines = ["CLARIFICATION QUESTIONS:"]
    for q in questions:
        if isinstance(q, dict):
            text = q.get("question", "")
            priority = q.get("priority")
            if text:
                prefix = f"  [P{priority}]" if priority else "  -"
                lines.append(f"{prefix} {text}")
        elif isinstance(q, str):
            lines.append(f"  - {q}")
    return ContextSection(name="clarification_questions", content="\n".join(lines), priority=2)


def _build_constraints_section(state: dict[str, Any]) -> ContextSection:
    tc = state.get("technicalConstraints")
    if not tc:
        return ContextSection(name="constraints", content="", priority=2)
    parts: list[str] = ["TECHNICAL CONSTRAINTS:"]
    for c in tc.get("constraints", []):
        parts.append(f"  - {c}")
    assumptions = tc.get("assumptions", [])
    if assumptions:
        parts.append("ASSUMPTIONS:")
        for a in assumptions:
            parts.append(f"  - {a}")
    return ContextSection(name="constraints", content="\n".join(parts), priority=2)


def _build_decisions_section(state: dict[str, Any]) -> ContextSection:
    """Extract architecture decisions / ADRs if present in state."""
    decisions = state.get("architectureDecisions", [])
    if not decisions:
        return ContextSection(name="decisions", content="", priority=2)
    lines = ["ARCHITECTURE DECISIONS:"]
    for d in decisions:
        if isinstance(d, dict):
            title = d.get("title", "Untitled")
            status = d.get("status", "proposed")
            lines.append(f"  [{status}] {title}")
        elif isinstance(d, str):
            lines.append(f"  - {d}")
    return ContextSection(name="decisions", content="\n".join(lines), priority=2)


def _build_waf_checklist_section(state: dict[str, Any]) -> ContextSection:
    """Extract WAF checklist summary for validation stage."""
    waf = state.get("wafChecklist")
    if not waf:
        return ContextSection(name="waf_checklist", content="", priority=1)
    items = waf.get("items", [])
    if not items:
        return ContextSection(name="waf_checklist", content="", priority=1)
    total = len(items)
    done = sum(1 for i in items if isinstance(i, dict) and i.get("status") == "done")
    lines = [f"WAF CHECKLIST: {done}/{total} items completed"]
    incomplete = [i for i in items if isinstance(i, dict) and i.get("status") != "done"]
    visible_incomplete_items = incomplete[:_MAX_INCOMPLETE_WAF_ITEMS]
    for item in visible_incomplete_items:
        lines.append(
            f"  [ ] {item.get('title', 'Unnamed')} ({item.get('pillar', 'unknown')})"
        )
    remaining_count = len(incomplete) - len(visible_incomplete_items)
    if remaining_count > 0:
        lines.append(f"  ... and {remaining_count} more")
    return ContextSection(name="waf_checklist", content="\n".join(lines), priority=1)


def _build_pricing_assumptions_section(state: dict[str, Any]) -> ContextSection:
    """Extract pricing-related context."""
    nfrs = state.get("nfrs", {})
    cost = nfrs.get("costConstraints", "")
    if not cost:
        return ContextSection(name="pricing_assumptions", content="", priority=2)
    content = f"BUDGET/COST CONSTRAINTS:\n  {cost}"
    return ContextSection(name="pricing_assumptions", content=content, priority=2)
