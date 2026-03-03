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


class QueueMetrics(TypedDict, total=False):
    """Raw queue statistics."""

    pending: int
    processing: int
    done: int
    error: int


class JobCounters(TypedDict, total=False):
    """Job-level counters."""

    docs_seen: int
    chunks_seen: int
    chunks_processed: int


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


def build_queue_based_metrics(queue_metrics: QueueMetrics) -> IngestionMetrics:
    """Build metrics from queue statistics."""
    pending = queue_metrics.get("pending", 0)
    processing = queue_metrics.get("processing", 0)
    done = queue_metrics.get("done", 0)
    error = queue_metrics.get("error", 0)

    return IngestionMetrics(
        chunks_pending=pending,
        chunks_processing=processing,
        chunks_embedded=done,
        chunks_failed=error,
        chunks_queued=pending + processing + done + error,
        documents_crawled=0,
        documents_cleaned=0,
        chunks_created=0,
    )


def augment_with_phase_data(
    metrics: IngestionMetrics, phase_details: list[dict[str, Any]]
) -> None:
    """Augment metrics with phase detail fallbacks."""
    if metrics["chunks_embedded"] == 0:
        metrics["chunks_embedded"] = get_phase_item_count(phase_details, "indexing")

    if metrics["chunks_queued"] == 0:
        metrics["chunks_queued"] = get_phase_item_count(
            phase_details, "chunking", "items_total"
        )

    metrics["documents_crawled"] = get_phase_item_count(phase_details, "loading")
    metrics["documents_cleaned"] = get_phase_item_count(phase_details, "chunking")
    metrics["chunks_created"] = get_phase_item_count(phase_details, "chunking")


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


def normalize_job_metrics(
    status: KBPersistedStatus,
    raw_queue_metrics: QueueMetrics,
    counters: JobCounters,
) -> IngestionMetrics:
    """Consolidate metrics from queue stats, phase details, and job counters."""
    metrics = build_queue_based_metrics(raw_queue_metrics)
    augment_with_phase_data(metrics, status.phase_details)
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
    )
