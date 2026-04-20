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
    decisions = state.get("adrs") or state.get("architectureDecisions", [])
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
    items_raw = waf.get("items", [])
    if isinstance(items_raw, dict):
        items = [item for item in items_raw.values() if isinstance(item, dict)]
    elif isinstance(items_raw, list):
        items = [item for item in items_raw if isinstance(item, dict)]
    else:
        items = []
    if not items:
        return ContextSection(name="waf_checklist", content="", priority=1)
    total = len(items)
    done = sum(1 for item in items if _is_completed_waf_item(item))
    lines = [f"WAF CHECKLIST: {done}/{total} items completed"]
    incomplete = [item for item in items if not _is_completed_waf_item(item)]
    visible_incomplete_items = incomplete[:_MAX_INCOMPLETE_WAF_ITEMS]
    for item in visible_incomplete_items:
        title = str(item.get("title") or item.get("topic") or "Unnamed")
        pillar = str(item.get("pillar") or "unknown")
        lines.append(
            f"  [ ] {title} ({pillar})"
        )
    remaining_count = len(incomplete) - len(visible_incomplete_items)
    if remaining_count > 0:
        lines.append(f"  ... and {remaining_count} more")
    return ContextSection(name="waf_checklist", content="\n".join(lines), priority=1)


def _is_completed_waf_item(item: dict[str, Any]) -> bool:
    status = str(item.get("status") or "").strip().lower()
    if status == "done":
        return True

    evaluations = item.get("evaluations")
    if not isinstance(evaluations, list) or not evaluations:
        return False

    latest = next(
        (
            evaluation
            for evaluation in reversed(evaluations)
            if isinstance(evaluation, dict)
        ),
        None,
    )
    if latest is None:
        return False

    latest_status = str(latest.get("status") or "").strip().lower()
    return latest_status in {"fixed", "done", "false_positive"}


def _build_pricing_assumptions_section(state: dict[str, Any]) -> ContextSection:
    """Extract pricing-related context."""
    nfrs = state.get("nfrs", {})
    cost = nfrs.get("costConstraints", "")
    if not cost:
        return ContextSection(name="pricing_assumptions", content="", priority=2)
    content = f"BUDGET/COST CONSTRAINTS:\n  {cost}"
    return ContextSection(name="pricing_assumptions", content=content, priority=2)


def build_general_sections(
    state: dict[str, Any], thread_summary: str | None = None,
) -> list[ContextSection]:
    """Context for general stage: requirements + assumptions + document summaries."""
    sections = [
        build_project_facts_section(state),
        build_thread_summary_section(thread_summary),
        build_requirements_section(state),
        _build_assumptions_section(state),
        _build_document_summaries_section(state),
        build_open_questions_section(state),
    ]
    return [s for s in sections if s.content.strip()]


def _build_assumptions_section(state: dict[str, Any]) -> ContextSection:
    """Extract assumptions from project state."""
    assumptions = state.get("assumptions", [])
    if not assumptions:
        return ContextSection(name="assumptions", content="", priority=3)
    lines = ["ASSUMPTIONS:"]
    for a in assumptions:
        if isinstance(a, dict):
            text = a.get("text") or a.get("description", "")
            status = a.get("status", "")
            prefix = f"  [{status}]" if status else "  -"
            if text:
                lines.append(f"{prefix} {text}")
        elif isinstance(a, str):
            lines.append(f"  - {a}")
    return ContextSection(name="assumptions", content="\n".join(lines), priority=3)


def _build_document_summaries_section(state: dict[str, Any]) -> ContextSection:
    """Include uploaded document titles and summaries in the context pack."""
    docs = state.get("referenceDocuments", [])
    if not docs:
        return ContextSection(name="document_summaries", content="", priority=2)
    lines = ["UPLOADED DOCUMENTS:"]
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        title = doc.get("title") or doc.get("fileName") or "Untitled"
        summary = doc.get("summary") or doc.get("analysisSummary") or ""
        line = f"  - {title}"
        if summary:
            line += f": {str(summary)[:500]}"
        lines.append(line)
    return ContextSection(name="document_summaries", content="\n".join(lines), priority=2)
