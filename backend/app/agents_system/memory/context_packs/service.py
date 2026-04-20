"""Context pack service.

Selects the right stage packer, assembles sections, applies budget,
and returns a ready-to-inject ContextPack.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.agents_system.memory.token_counter import TokenCounter

from .schema import ContextPack, ContextSection
from .stage_packers import (
    build_clarify_sections,
    build_general_sections,
    build_iac_sections,
    build_manage_adr_sections,
    build_pricing_sections,
    build_propose_candidate_sections,
    build_validate_sections,
)

_STAGE_REGISTRY: dict[str, Callable[..., list[ContextSection]]] = {
    "clarify": build_clarify_sections,
    "general": build_general_sections,
    "propose_candidate": build_propose_candidate_sections,
    "manage_adr": build_manage_adr_sections,
    "validate": build_validate_sections,
    "pricing": build_pricing_sections,
    "iac": build_iac_sections,
}


def build_context_pack(
    stage: str,
    state: dict[str, Any],
    *,
    budget_tokens: int = 4000,
    thread_summary: str | None = None,
    model: str = "gpt-4o",
) -> ContextPack:
    """Build a context pack for *stage* within *budget_tokens*.

    If the stage is not registered, falls back to ``clarify`` packer.
    Sections that would exceed the budget are dropped
    lowest-priority-first (highest number = lowest priority).
    """
    counter = TokenCounter(model_name=model)
    packer = _STAGE_REGISTRY.get(stage, build_clarify_sections)
    raw_sections = packer(state, thread_summary=thread_summary)

    # Count tokens per section
    for section in raw_sections:
        section.token_count = counter.count_tokens(section.content)

    # Sort by priority ascending (1 = most important, included first)
    sorted_sections = sorted(raw_sections, key=lambda s: s.priority)

    kept: list[ContextSection] = []
    used = 0
    dropped: list[str] = []

    for section in sorted_sections:
        if used + section.token_count <= budget_tokens:
            kept.append(section)
            used += section.token_count
        else:
            dropped.append(section.name)

    return ContextPack(
        stage=stage,
        sections=kept,
        budget_meta={
            "budget_tokens": budget_tokens,
            "used_tokens": used,
            "dropped_sections": dropped,
        },
    )
