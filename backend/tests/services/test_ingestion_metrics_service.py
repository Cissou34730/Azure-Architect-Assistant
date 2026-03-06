"""Tests for ingestion metrics service."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.ingestion_metrics_service import (
    IngestionMetrics,
    JobCounters,
    apply_counter_overrides,
    build_persisted_status_metrics,
    build_phase_based_metrics,
    derive_job_status,
    get_job_counters,
    get_phase_item_count,
    get_status_message,
    normalize_job_metrics,
)

# ---------------------------------------------------------------------------
# get_phase_item_count
# ---------------------------------------------------------------------------

class TestGetPhaseItemCount:
    def test_returns_value_for_matching_phase(self):
        phases = [{"name": "loading", "items_processed": 42}]
        assert get_phase_item_count(phases, "loading") == 42

    def test_returns_zero_for_missing_phase(self):
        phases = [{"name": "loading", "items_processed": 5}]
        assert get_phase_item_count(phases, "indexing") == 0

    def test_returns_custom_key(self):
        phases = [{"name": "chunking", "items_total": 100}]
        assert get_phase_item_count(phases, "chunking", "items_total") == 100

    def test_returns_zero_for_none_value(self):
        phases = [{"name": "loading", "items_processed": None}]
        assert get_phase_item_count(phases, "loading") == 0

    def test_empty_list(self):
        assert get_phase_item_count([], "loading") == 0


# ---------------------------------------------------------------------------
# build_phase_based_metrics
# ---------------------------------------------------------------------------

class TestBuildPhaseBasedMetrics:
    def test_basic_counts(self):
        kb_status = MagicMock(
            phase_details=[
                {"name": "loading", "items_processed": 10},
                {"name": "chunking", "items_processed": 40, "items_total": 50},
                {"name": "embedding", "items_processed": 30},
                {"name": "indexing", "items_processed": 28},
            ]
        )

        result = build_phase_based_metrics(kb_status)
        assert result["chunks_pending"] == 22
        assert result["chunks_processing"] == 0
        assert result["chunks_embedded"] == 28
        assert result["chunks_failed"] == 0
        assert result["chunks_queued"] == 50
        assert result["documents_crawled"] == 10
        assert result["chunks_created"] == 40

    def test_empty_metrics(self):
        kb_status = MagicMock(phase_details=[])
        result = build_phase_based_metrics(kb_status)
        assert result["chunks_queued"] == 0
        assert result["documents_crawled"] == 0


# ---------------------------------------------------------------------------
# apply_counter_overrides
# ---------------------------------------------------------------------------

class TestApplyCounterOverrides:
    def test_overrides_docs_seen(self):
        metrics = IngestionMetrics(documents_crawled=0)
        counters = JobCounters(docs_seen=15)
        apply_counter_overrides(metrics, counters)
        assert metrics["documents_crawled"] == 15

    def test_overrides_chunks_seen(self):
        metrics = IngestionMetrics(chunks_created=0)
        counters = JobCounters(chunks_seen=200)
        apply_counter_overrides(metrics, counters)
        assert metrics["chunks_created"] == 200

    def test_overrides_chunks_processed(self):
        metrics = IngestionMetrics(chunks_embedded=0)
        counters = JobCounters(chunks_processed=100)
        apply_counter_overrides(metrics, counters)
        assert metrics["chunks_embedded"] == 100

    def test_recomputes_pending_with_errors_and_skips(self):
        metrics = IngestionMetrics(chunks_created=10, chunks_embedded=4, chunks_failed=0, chunks_queued=10)
        counters = JobCounters(chunks_error=2, chunks_skipped=3)
        apply_counter_overrides(metrics, counters)
        assert metrics["chunks_failed"] == 2
        assert metrics["chunks_pending"] == 1
        assert metrics["chunks_processing"] == 0

    def test_empty_counters_no_change(self):
        metrics = IngestionMetrics(documents_crawled=5, chunks_created=10, chunks_embedded=20, chunks_queued=20)
        apply_counter_overrides(metrics, JobCounters())
        assert metrics["documents_crawled"] == 5


# ---------------------------------------------------------------------------
# derive_job_status
# ---------------------------------------------------------------------------

class TestDeriveJobStatus:
    def test_no_job_state_returns_not_started(self):
        kb_status = MagicMock(status="pending")
        assert derive_job_status(None, kb_status) == "not_started"

    def test_running_state(self):
        job = SimpleNamespace(status="running")
        kb_status = MagicMock(status="indexing")
        assert derive_job_status(job, kb_status) == "running"

    def test_completed_state(self):
        job = SimpleNamespace(status="completed")
        kb_status = MagicMock(status="ready")
        assert derive_job_status(job, kb_status) == "completed"

    def test_failed_state(self):
        job = SimpleNamespace(status="failed")
        kb_status = MagicMock(status="error")
        assert derive_job_status(job, kb_status) == "failed"

    def test_paused_state(self):
        job = SimpleNamespace(status="paused")
        kb_status = MagicMock(status="indexing")
        assert derive_job_status(job, kb_status) == "paused"

    def test_fallback_to_kb_ready(self):
        job = SimpleNamespace(status="unknown")
        kb_status = MagicMock(status="ready")
        assert derive_job_status(job, kb_status) == "completed"

    def test_fallback_to_kb_pending(self):
        job = SimpleNamespace(status="unknown")
        kb_status = MagicMock(status="pending")
        assert derive_job_status(job, kb_status) == "pending"

    def test_fallback_not_started(self):
        job = SimpleNamespace(status="unknown")
        kb_status = MagicMock(status="error")
        assert derive_job_status(job, kb_status) == "not_started"


# ---------------------------------------------------------------------------
# get_status_message
# ---------------------------------------------------------------------------

class TestGetStatusMessage:
    @pytest.mark.parametrize(
        "status,expected",
        [
            ("running", "Ingestion in progress"),
            ("completed", "Ingestion complete"),
            ("failed", "Ingestion failed"),
            ("paused", "Ingestion paused"),
            ("canceled", "Ingestion canceled"),
            ("not_started", "Waiting to start"),
            ("pending", "Waiting to start"),
        ],
    )
    def test_all_statuses(self, status, expected):
        assert get_status_message(status) == expected


# ---------------------------------------------------------------------------
# get_job_counters
# ---------------------------------------------------------------------------

class TestGetJobCounters:
    def test_with_counters(self):
        job_view = SimpleNamespace(
            counters={
                "docs_seen": 5,
                "chunks_seen": 50,
                "chunks_processed": 45,
                "chunks_error": 2,
                "chunks_skipped": 3,
            }
        )
        result = get_job_counters(job_view)
        assert result["docs_seen"] == 5
        assert result["chunks_seen"] == 50
        assert result["chunks_processed"] == 45
        assert result["chunks_error"] == 2
        assert result["chunks_skipped"] == 3

    def test_none_job_view(self):
        result = get_job_counters(None)
        assert result == JobCounters()

    def test_none_counters(self):
        job_view = SimpleNamespace(counters=None)
        result = get_job_counters(job_view)
        assert result == JobCounters()

    def test_partial_counters(self):
        job_view = SimpleNamespace(counters={"docs_seen": 3})
        result = get_job_counters(job_view)
        assert result["docs_seen"] == 3
        assert result["chunks_seen"] == 0


# ---------------------------------------------------------------------------
# normalize_job_metrics (integration)
# ---------------------------------------------------------------------------

class TestNormalizeJobMetrics:
    def test_combines_all_sources(self):
        kb_status = MagicMock(
            phase_details=[
                {"name": "loading", "items_processed": 10},
                {"name": "chunking", "items_processed": 50, "items_total": 100},
                {"name": "indexing", "items_processed": 40},
            ]
        )
        counters = JobCounters(
            docs_seen=12,
            chunks_seen=55,
            chunks_processed=35,
            chunks_error=4,
            chunks_skipped=6,
        )

        result = normalize_job_metrics(kb_status, counters)
        assert result["documents_crawled"] == 12
        assert result["chunks_created"] == 55
        assert result["chunks_embedded"] == 35
        assert result["chunks_failed"] == 4
        assert result["chunks_pending"] == 10

    def test_empty_inputs(self):
        kb_status = MagicMock(phase_details=[])
        result = normalize_job_metrics(kb_status, JobCounters())
        assert result["chunks_queued"] == 0


class TestBuildPersistedStatusMetrics:
    def test_maps_persisted_metrics_to_status_shape(self):
        kb_status = MagicMock(
            phase_details=[
                {"name": "loading", "items_processed": 3},
                {"name": "chunking", "items_processed": 10, "items_total": 12},
                {"name": "indexing", "items_processed": 6},
            ]
        )

        result = build_persisted_status_metrics(
            kb_status,
            JobCounters(chunks_processed=8, chunks_error=1, chunks_skipped=2),
        )

        assert result == {"pending": 1, "processing": 0, "done": 8, "error": 1}
