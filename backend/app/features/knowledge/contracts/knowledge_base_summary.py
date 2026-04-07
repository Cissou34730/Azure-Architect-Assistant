"""Cross-feature contract for knowledge-base summaries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KnowledgeBaseSummaryContract(BaseModel):
    """Knowledge-base metadata used in composed project workspaces."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    status: str
    profiles: list[str]
    priority: int
