"""Checklist metric helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.checklist import ChecklistItemEvaluation, EvaluationStatus, SeverityLevel


def severity_value(value: SeverityLevel | str) -> str:
    return value.value if isinstance(value, SeverityLevel) else str(value)


class ChecklistMetricsService:
    """Metric and action-list helpers from already-loaded items."""

    @staticmethod
    def latest_status(evaluations: list[ChecklistItemEvaluation]) -> EvaluationStatus:
        if not evaluations:
            return EvaluationStatus.OPEN
        latest = max(evaluations, key=lambda e: e.created_at or datetime.min.replace(tzinfo=timezone.utc))
        raw = latest.status
        if isinstance(raw, EvaluationStatus):
            return raw
        try:
            return EvaluationStatus(str(raw))
        except ValueError:
            return EvaluationStatus.OPEN

    @staticmethod
    def latest_timestamp(evaluations: list[ChecklistItemEvaluation]) -> str | None:
        if not evaluations:
            return None
        latest = max(evaluations, key=lambda e: e.created_at or datetime.min.replace(tzinfo=timezone.utc))
        return latest.created_at.isoformat() if latest.created_at else None
