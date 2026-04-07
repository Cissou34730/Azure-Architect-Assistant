"""Cross-feature contract for checklist workspace summaries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ChecklistSummaryContract(BaseModel):
    """Compact checklist projection for workspace composition."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    status: str
    items_count: int = Field(alias="itemsCount")
    last_synced_at: str | None = Field(default=None, alias="lastSyncedAt")
