"""Search / query settings mixin.

Replaces the old ``QuerySettings`` from ``config/settings.py`` and
consolidates search-related constants that were previously scattered as magic
literals across ``multi_query.py``, ``query_service.py``, and routers.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class SearchSettingsMixin(BaseModel):
    # ── Vector retrieval thresholds ───────────────────────────────────────────
    search_similarity_threshold: float = Field(
        default=0.38,
        description=(
            "Minimum similarity score for retrieved results (0.0–1.0). "
            "Lower values increase recall."
        ),
    )
    search_min_results: int = Field(
        default=3,
        description="Minimum number of results to return if any are available",
    )
    search_initial_retrieve_multiplier: int = Field(
        default=2,
        description="Multiply top_k by this factor for initial retrieval before filtering",
    )
    search_min_initial_retrieve: int = Field(
        default=10,
        description="Minimum number of results to retrieve initially, regardless of top_k",
    )

    # ── Per-profile top-k defaults ────────────────────────────────────────────
    kb_top_k_chat: int = Field(
        default=3,
        description="Default top-k per KB for CHAT query profile",
    )
    kb_top_k_proposal: int = Field(
        default=5,
        description="Default top-k per KB for PROPOSAL query profile",
    )

    # ── Per-profile max returned sources ─────────────────────────────────────
    kb_max_sources_chat: int = Field(
        default=6,
        description="Maximum merged sources returned for CHAT profile",
    )
    kb_max_sources_proposal: int = Field(
        default=15,
        description="Maximum merged sources returned for PROPOSAL profile",
    )

    # ── Pagination / list limits ──────────────────────────────────────────────
    checklist_next_actions_limit: int = Field(
        default=10,
        description="Maximum next-actions returned by the checklist progress endpoint",
    )
    messages_pagination_limit: int = Field(
        default=50,
        description="Default page size for conversation messages",
    )
