"""Async-timing constants mixin.

Centralises all ``asyncio.sleep`` delays and ``asyncio.wait_for`` timeouts
that were previously hardcoded as magic floats throughout service code.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class AsyncTimingsMixin(BaseModel):
    # ── Ingestion runtime ─────────────────────────────────────────────────────
    ingestion_shutdown_timeout: float = Field(
        default=5.0,
        description="Seconds to wait for a running ingestion task on pause/cancel",
    )
    ingestion_stop_timeout: float = Field(
        default=2.0,
        description="Seconds to wait when aborting a cancel-targeted task",
    )
    ingestion_drain_sleep: float = Field(
        default=2.0,
        description="Sleep duration (s) before cancelling remaining tasks on cleanup",
    )

    # ── AI service ────────────────────────────────────────────────────────────
    ai_reinit_grace_sleep: float = Field(
        default=0.5,
        description="Grace-period sleep (s) before swapping the AIService singleton",
    )

    # ── KB management ─────────────────────────────────────────────────────────
    kb_delete_sleep: float = Field(
        default=0.5,
        description="Sleep (s) after clearing index cache before deleting KB storage",
    )

    # ── Ingestion job gate ────────────────────────────────────────────────────
    job_gate_poll_interval: float = Field(
        default=1.0,
        description="Poll interval (s) for the ingestion job-gate check loop",
    )

    # ── Web crawler ───────────────────────────────────────────────────────────
    web_crawl_politeness_delay: float = Field(
        default=2.0,
        description="Politeness delay (s) between consecutive website page fetches",
    )
