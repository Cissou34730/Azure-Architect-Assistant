"""Shared section builders used by multiple stage packers."""

from __future__ import annotations

from typing import Any

from .schema import ContextSection

_PROJECT_FACT_NFR_KEYS: tuple[str, ...] = (
    "availability",
    "security",
    "performance",
    "costConstraints",
)


def build_project_facts_section(state: dict[str, Any]) -> ContextSection:
    """Extract core project facts (context, NFRs, constraints)."""
    parts = [
        *_build_context_parts(state),
        *_build_nfr_parts(state),
        *_build_constraint_parts(state),
    ]
    content = "\n".join(parts) if parts else ""
    return ContextSection(name="project_facts", content=content, priority=1)


def _build_context_parts(state: dict[str, Any]) -> list[str]:
    ctx = state.get("context")
    if not ctx:
        return []

    parts: list[str] = []
    summary = ctx.get("summary")
    if summary:
        parts.append(f"Summary: {summary}")

    objectives = ctx.get("objectives")
    if objectives:
        parts.append(f"Objectives: {', '.join(str(objective) for objective in objectives)}")

    scenario_type = ctx.get("scenarioType")
    if scenario_type:
        parts.append(f"Scenario: {scenario_type}")
    return parts


def _build_nfr_parts(state: dict[str, Any]) -> list[str]:
    nfrs = state.get("nfrs")
    if not nfrs:
        return []

    nfr_items = [f"{key}: {nfrs[key]}" for key in _PROJECT_FACT_NFR_KEYS if nfrs.get(key)]
    if not nfr_items:
        return []
    return ["NFRs: " + "; ".join(nfr_items)]


def _build_constraint_parts(state: dict[str, Any]) -> list[str]:
    technical_constraints = state.get("technicalConstraints")
    if not technical_constraints:
        return []

    constraints = technical_constraints.get("constraints", [])
    return [f"Constraint: {constraint}" for constraint in constraints]


def build_requirements_section(state: dict[str, Any]) -> ContextSection:
    """Extract requirements list."""
    reqs = state.get("requirements", [])
    if not reqs:
        return ContextSection(name="requirements", content="", priority=2)
    lines: list[str] = ["REQUIREMENTS:"]
    for req in reqs:
        if isinstance(req, dict):
            cat = req.get("category", "unknown")
            text = req.get("text", "")
            if text:
                lines.append(f"  [{cat}] {text}")
    return ContextSection(name="requirements", content="\n".join(lines), priority=2)


def build_open_questions_section(state: dict[str, Any]) -> ContextSection:
    """Extract open questions."""
    questions = state.get("openQuestions", [])
    if not questions:
        return ContextSection(name="open_questions", content="", priority=3)
    lines = ["OPEN QUESTIONS:"]
    for q in questions[:5]:
        lines.append(f"  - {q}")
    return ContextSection(name="open_questions", content="\n".join(lines), priority=3)


def build_thread_summary_section(thread_summary: str | None) -> ContextSection:
    """Inject compaction summary from prior turns."""
    if not thread_summary:
        return ContextSection(name="thread_summary", content="", priority=2)
    content = f"CONVERSATION CONTEXT:\n{thread_summary}"
    return ContextSection(name="thread_summary", content=content, priority=2)


def build_data_compliance_section(state: dict[str, Any]) -> ContextSection:
    """Extract data compliance information."""
    dc = state.get("dataCompliance")
    if not dc:
        return ContextSection(name="data_compliance", content="", priority=3)
    parts: list[str] = []
    if dc.get("dataTypes"):
        parts.append(f"Data Types: {', '.join(str(d) for d in dc['dataTypes'])}")
    if dc.get("complianceRequirements"):
        parts.append(f"Compliance: {', '.join(str(r) for r in dc['complianceRequirements'])}")
    if dc.get("dataResidency"):
        parts.append(f"Data Residency: {dc['dataResidency']}")
    content = "\n".join(parts) if parts else ""
    return ContextSection(name="data_compliance", content=content, priority=3)
