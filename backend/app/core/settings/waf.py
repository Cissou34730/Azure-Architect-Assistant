"""WAF feature flags and batch-size settings mixin."""
from __future__ import annotations

from pydantic import BaseModel, Field


class WafSettingsMixin(BaseModel):
    aaa_feature_waf_normalized: bool = Field(
        default=False,
        description="Enable normalized WAF checklist storage (dual-write mode)",
    )
    waf_namespace_uuid: str = Field(
        default="3a7e8c2f-1b4d-4f5e-9c3d-2a8b7e6f1c4d",
        description="Namespace UUID for deterministic checklist item IDs (UUID v5)",
    )
    waf_backfill_batch_size: int = Field(
        default=50,
        description="Number of projects to process per backfill batch",
    )
    waf_sync_chunk_size: int = Field(
        default=500,
        description="Number of items per database transaction during WAF sync",
    )
