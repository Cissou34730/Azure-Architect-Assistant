"""Ingestion metrics calculation and normalization.

Extracted from the ingestion router to keep metric logic testable in isolation.
"""

from __future__ import annotations

from typing import Any, Literal

from typing_extensions import TypedDict

from app.ingestion.application.status_query_service import KBPersistedStatus

# ── Domain types ──────────────────────────────────────────────────────────

class IngestionMetrics(TypedDict, total=False):
    """Typed metrics structure for ingestion jobs."""

    chunks_pending: int
    chunks_processing: int
    chunks_embedded: int
    chunks_failed: int
    chunks_queued: int
    documents_crawled: int
    documents_cleaned: int
    chunks_created: int


class JobCounters(TypedDict, total=False):
    """Job-level counters."""

    docs_seen: int
    chunks_seen: int
    chunks_processed: int
    chunks_error: int
    chunks_skipped: int


JobStatus = Literal[
    "not_started", "pending", "running", "paused", "completed", "failed", "canceled"
]


# ── Helpers ───────────────────────────────────────────────────────────────

def get_phase_item_count(
    phase_details: list[dict[str, Any]], phase_name: str, key: str = "items_processed"
) -> int:
    """Extract item count from phase details."""
    for phase in phase_details:
        if phase.get("name") == phase_name:
            return phase.get(key, 0) or 0
    return 0


def build_phase_based_metrics(status: KBPersistedStatus) -> IngestionMetrics:
    """Build metrics from persisted phase state only."""
    documents_crawled = get_phase_item_count(status.phase_details, "loading")
    chunks_created = get_phase_item_count(status.phase_details, "chunking")
    chunks_embedded = get_phase_item_count(status.phase_details, "indexing")
    chunks_queued = max(
        get_phase_item_count(status.phase_details, "chunking", "items_total"),
        chunks_created,
        chunks_embedded,
    )

    return IngestionMetrics(
        chunks_pending=max(chunks_queued - chunks_embedded, 0),
        chunks_processing=0,
        chunks_embedded=chunks_embedded,
        chunks_failed=0,
        chunks_queued=chunks_queued,
        documents_crawled=documents_crawled,
        documents_cleaned=get_phase_item_count(status.phase_details, "chunking"),
        chunks_created=chunks_created,
    )


def apply_counter_overrides(
    metrics: IngestionMetrics, counters: JobCounters
) -> None:
    """Override metrics with job counters if available."""
    if "docs_seen" in counters:
        metrics["documents_crawled"] = counters["docs_seen"]
    if "chunks_seen" in counters:
        metrics["chunks_created"] = counters["chunks_seen"]
    if "chunks_processed" in counters:
        metrics["chunks_embedded"] = counters["chunks_processed"]
    if "chunks_error" in counters:
        metrics["chunks_failed"] = counters["chunks_error"]

    completed_chunks = (
        metrics.get("chunks_embedded", 0)
        + metrics.get("chunks_failed", 0)
        + counters.get("chunks_skipped", 0)
    )
    if "chunks_seen" in counters:
        metrics["chunks_queued"] = max(metrics.get("chunks_created", 0), completed_chunks)
    else:
        metrics["chunks_queued"] = max(
            metrics.get("chunks_queued", 0),
            metrics.get("chunks_created", 0),
            completed_chunks,
        )
    metrics["chunks_pending"] = max(metrics["chunks_queued"] - completed_chunks, 0)
    metrics["chunks_processing"] = 0


def build_persisted_status_metrics(
    status: KBPersistedStatus, counters: JobCounters
) -> dict[str, int]:
    """Build queue-shaped status metrics from persisted job and phase state."""
    metrics = normalize_job_metrics(status, counters)
    return {
        "pending": metrics["chunks_pending"],
        "processing": metrics["chunks_processing"],
        "done": metrics["chunks_embedded"],
        "error": metrics["chunks_failed"],
    }


def normalize_job_metrics(
    status: KBPersistedStatus,
    counters: JobCounters,
) -> IngestionMetrics:
    """Consolidate metrics from persisted phase details and job counters."""
    metrics = build_phase_based_metrics(status)
    apply_counter_overrides(metrics, counters)
    return metrics


def derive_job_status(
    latest_job_state: Any, kb_status: KBPersistedStatus
) -> JobStatus:
    """Determine job status from database state and KB status."""
    if not latest_job_state:
        return "not_started"

    job_status = str(latest_job_state.status)
    if job_status in ("running", "paused", "failed", "canceled", "completed"):
        return job_status  # type: ignore[return-value]

    # Fallback to KB status
    if kb_status.status == "ready":
        return "completed"
    if kb_status.status == "pending":
        return "pending"

    return "not_started"


def get_status_message(status: JobStatus) -> str:
    """Map job status to user-friendly message."""
    return {
        "running": "Ingestion in progress",
        "completed": "Ingestion complete",
        "failed": "Ingestion failed",
        "paused": "Ingestion paused",
        "canceled": "Ingestion canceled",
        "not_started": "Waiting to start",
        "pending": "Waiting to start",
    }[status]


def get_job_counters(job_view: Any) -> JobCounters:
    """Extract typed counters from job view."""
    if not job_view or not job_view.counters:
        return JobCounters()
    raw_counters = dict(job_view.counters) if job_view.counters else {}
    return JobCounters(
        docs_seen=raw_counters.get("docs_seen", 0),
        chunks_seen=raw_counters.get("chunks_seen", 0),
        chunks_processed=raw_counters.get("chunks_processed", 0),
        chunks_error=raw_counters.get("chunks_error", 0),
        chunks_skipped=raw_counters.get("chunks_skipped", 0),
    )
