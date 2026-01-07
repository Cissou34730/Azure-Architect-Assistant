"""Prometheus-style metrics for ingestion monitoring."""

from __future__ import annotations

import logging
import threading
import time
from typing import Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MetricValue:
    """Container for a metric value with timestamp."""

    value: float
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    """Prometheus-style metrics collector for ingestion operations."""

    def __init__(self):
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, MetricValue] = {}
        self._histograms: Dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def increment_counter(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter metric."""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def set_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Set a gauge metric."""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = MetricValue(value=value)

    def observe_histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a histogram observation."""
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current counter value."""
        key = self._make_key(name, labels)
        with self._lock:
            return self._counters.get(key, 0.0)

    def get_gauge(
        self, name: str, labels: Optional[Dict[str, str]] = None
    ) -> Optional[float]:
        """Get current gauge value."""
        key = self._make_key(name, labels)
        with self._lock:
            metric = self._gauges.get(key)
            return metric.value if metric else None

    def get_histogram_stats(
        self, name: str, labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, float]:
        """Get histogram statistics (count, sum, avg, p50, p95, p99)."""
        key = self._make_key(name, labels)
        with self._lock:
            values = self._histograms.get(key, [])
            if not values:
                return {
                    "count": 0,
                    "sum": 0.0,
                    "avg": 0.0,
                    "p50": 0.0,
                    "p95": 0.0,
                    "p99": 0.0,
                }

            sorted_values = sorted(values)
            count = len(sorted_values)
            total = sum(sorted_values)
            avg = total / count if count > 0 else 0.0

            return {
                "count": count,
                "sum": total,
                "avg": avg,
                "p50": self._percentile(sorted_values, 0.50),
                "p95": self._percentile(sorted_values, 0.95),
                "p99": self._percentile(sorted_values, 0.99),
            }

    def get_all_metrics(self) -> Dict[str, any]:
        """Get all metrics for export."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": {k: v.value for k, v in self._gauges.items()},
                "histograms": {
                    k: self.get_histogram_stats(k) for k in self._histograms
                },
            }

    def reset_histogram(
        self, name: str, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Reset histogram values."""
        key = self._make_key(name, labels)
        with self._lock:
            if key in self._histograms:
                self._histograms[key] = []

    @staticmethod
    def _make_key(name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create metric key with labels."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    @staticmethod
    def _percentile(sorted_values: list[float], p: float) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0
        k = (len(sorted_values) - 1) * p
        f = int(k)
        c = int(k) + 1
        if c >= len(sorted_values):
            return sorted_values[-1]
        d0 = sorted_values[f] * (c - k)
        d1 = sorted_values[c] * (k - f)
        return d0 + d1


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


# Convenience functions for common metrics
def record_job_started(kb_id: str, job_id: str) -> None:
    """Record job start."""
    collector = get_metrics_collector()
    collector.increment_counter("ingestion_jobs_started_total", labels={"kb_id": kb_id})
    collector.set_gauge(
        "ingestion_job_active", 1.0, labels={"kb_id": kb_id, "job_id": job_id}
    )


def record_job_completed(kb_id: str, job_id: str, duration_seconds: float) -> None:
    """Record job completion."""
    collector = get_metrics_collector()
    collector.increment_counter(
        "ingestion_jobs_completed_total", labels={"kb_id": kb_id}
    )
    collector.set_gauge(
        "ingestion_job_active", 0.0, labels={"kb_id": kb_id, "job_id": job_id}
    )
    collector.observe_histogram(
        "ingestion_job_duration_seconds", duration_seconds, labels={"kb_id": kb_id}
    )


def record_job_failed(kb_id: str, job_id: str, error_type: str) -> None:
    """Record job failure."""
    collector = get_metrics_collector()
    collector.increment_counter(
        "ingestion_jobs_failed_total", labels={"kb_id": kb_id, "error_type": error_type}
    )
    collector.set_gauge(
        "ingestion_job_active", 0.0, labels={"kb_id": kb_id, "job_id": job_id}
    )


def record_chunks_processed(kb_id: str, count: int) -> None:
    """Record chunks processed."""
    collector = get_metrics_collector()
    collector.increment_counter(
        "ingestion_chunks_processed_total", count, labels={"kb_id": kb_id}
    )


def record_queue_depth(kb_id: str, job_id: str, depth: int) -> None:
    """Record current queue depth."""
    collector = get_metrics_collector()
    collector.set_gauge(
        "ingestion_queue_depth", float(depth), labels={"kb_id": kb_id, "job_id": job_id}
    )


def record_processing_latency(
    kb_id: str, operation: str, duration_seconds: float
) -> None:
    """Record processing latency."""
    collector = get_metrics_collector()
    collector.observe_histogram(
        "ingestion_operation_duration_seconds",
        duration_seconds,
        labels={"kb_id": kb_id, "operation": operation},
    )
