"""Project-level quality gate reporting service."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol

from sqlalchemy import select

from app.agents_system.services.mindmap_loader import build_top_level_coverage_scorecard
from app.features.projects.contracts.quality_gate import (
    QualityGateMissingArtifactsContract,
    QualityGateMindMapSummaryContract,
    QualityGateOpenClarificationsContract,
    QualityGateReportContract,
    QualityGateTraceSummaryContract,
    QualityGateWafSummaryContract,
)
from app.models.project import ProjectTraceEvent

_OPEN_CLARIFICATION_STATUSES = {"open", "pending", "unanswered"}
_MISSING_ARTIFACT_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
    (
        "candidate-architectures",
        "Candidate Architectures",
        "No candidate architecture has been generated yet.",
    ),
    ("diagrams", "Diagrams", "No diagrams have been generated yet."),
    ("adrs", "ADRs", "No architecture decisions have been recorded yet."),
    ("costs", "Cost Estimates", "No cost estimate has been recorded yet."),
    ("iac", "Infrastructure as Code", "No IaC artifact has been generated yet."),
    ("waf", "WAF Checklist", "No WAF checklist evidence has been recorded yet."),
)


class StateProvider(Protocol):
    async def get_project_state(self, project_id: str, db: object) -> dict[str, Any]: ...


class TraceSummaryProvider(Protocol):
    async def get_trace_summary(self, project_id: str, db: object) -> dict[str, Any]: ...


class ProjectTraceSummaryProvider:
    async def get_trace_summary(self, project_id: str, db: object) -> dict[str, Any]:
        result = await db.execute(
            select(ProjectTraceEvent.event_type, ProjectTraceEvent.created_at)
            .where(ProjectTraceEvent.project_id == project_id)
            .order_by(ProjectTraceEvent.created_at.desc())
        )
        rows = result.all()
        counts = Counter(str(event_type) for event_type, _ in rows)
        return {
            "totalEvents": len(rows),
            "lastEventAt": str(rows[0][1]) if rows else None,
            "eventTypes": [
                {"eventType": event_type, "count": count}
                for event_type, count in sorted(
                    counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
        }


class QualityGateService:
    def __init__(
        self,
        *,
        state_provider: StateProvider,
        trace_summary_provider: TraceSummaryProvider | None = None,
    ) -> None:
        self._state_provider = state_provider
        self._trace_summary_provider = trace_summary_provider or ProjectTraceSummaryProvider()

    async def get_report(self, *, project_id: str, db: object) -> QualityGateReportContract:
        state = await self._state_provider.get_project_state(project_id, db)
        trace_summary = await self._trace_summary_provider.get_trace_summary(project_id, db)
        return self._build_report(state, trace_summary)

    def _build_report(
        self,
        state: Mapping[str, Any],
        trace_summary: Mapping[str, Any],
    ) -> QualityGateReportContract:
        return QualityGateReportContract(
            generated_at=_now_iso(),
            waf=self._build_waf_summary(state),
            mind_map=self._build_mind_map_summary(state),
            open_clarifications=self._build_open_clarifications_summary(state),
            missing_artifacts=self._build_missing_artifacts_summary(state),
            trace=self._build_trace_summary(trace_summary),
        )

    def _build_waf_summary(self, state: Mapping[str, Any]) -> QualityGateWafSummaryContract:
        pillar_buckets: dict[str, dict[str, int | str]] = {}

        for item in _coerce_mapping_list(_coerce_mapping(state.get("wafChecklist")).get("items")):
            pillar = str(item.get("pillar") or "General")
            status = _derive_waf_status(item)
            bucket = pillar_buckets.setdefault(
                pillar,
                {
                    "pillar": pillar,
                    "totalItems": 0,
                    "coveredItems": 0,
                    "partialItems": 0,
                    "notCoveredItems": 0,
                    "coveragePercentage": 0,
                },
            )
            bucket["totalItems"] = int(bucket["totalItems"]) + 1
            if status == "covered":
                bucket["coveredItems"] = int(bucket["coveredItems"]) + 1
            elif status == "partial":
                bucket["partialItems"] = int(bucket["partialItems"]) + 1
            else:
                bucket["notCoveredItems"] = int(bucket["notCoveredItems"]) + 1

        pillars = [pillar_buckets[key] for key in sorted(pillar_buckets)]
        for pillar in pillars:
            pillar["coveragePercentage"] = _weighted_percentage(
                covered=int(pillar["coveredItems"]),
                partial=int(pillar["partialItems"]),
                total=int(pillar["totalItems"]),
            )

        covered_items = sum(int(pillar["coveredItems"]) for pillar in pillars)
        partial_items = sum(int(pillar["partialItems"]) for pillar in pillars)
        not_covered_items = sum(int(pillar["notCoveredItems"]) for pillar in pillars)
        total_items = sum(int(pillar["totalItems"]) for pillar in pillars)

        return QualityGateWafSummaryContract(
            total_items=total_items,
            covered_items=covered_items,
            partial_items=partial_items,
            not_covered_items=not_covered_items,
            coverage_percentage=_weighted_percentage(
                covered=covered_items,
                partial=partial_items,
                total=total_items,
            ),
            pillars=pillars,
        )

    def _build_mind_map_summary(
        self,
        state: Mapping[str, Any],
    ) -> QualityGateMindMapSummaryContract:
        state_dict = dict(state)
        scorecard = build_top_level_coverage_scorecard(
            state_dict,
            state_dict.get("mindMapCoverage")
            if isinstance(state_dict.get("mindMapCoverage"), dict)
            else None,
        )
        raw_summary = _coerce_mapping(scorecard.get("summary"))
        addressed_topics = _coerce_int(raw_summary.get("addressed"))
        partial_topics = _coerce_int(raw_summary.get("partial"))
        not_addressed_topics = _coerce_int(raw_summary.get("notAddressed"))
        topics = [
            {
                "key": topic_key,
                "label": str(topic_payload.get("label") or topic_key),
                "status": str(topic_payload.get("status") or "not-addressed"),
                "confidence": float(topic_payload.get("confidence") or 0.0),
            }
            for topic_key, topic_payload in _coerce_mapping(scorecard.get("topics")).items()
            if isinstance(topic_payload, dict)
        ]
        total_topics = len(topics)
        return QualityGateMindMapSummaryContract(
            total_topics=total_topics,
            addressed_topics=addressed_topics,
            partial_topics=partial_topics,
            not_addressed_topics=not_addressed_topics,
            coverage_percentage=_weighted_percentage(
                covered=addressed_topics,
                partial=partial_topics,
                total=total_topics,
            ),
            topics=topics,
        )

    def _build_open_clarifications_summary(
        self,
        state: Mapping[str, Any],
    ) -> QualityGateOpenClarificationsContract:
        items = [
            {
                "id": str(question.get("id") or ""),
                "question": str(question.get("question") or question.get("text") or ""),
                "status": str(question.get("status") or "open"),
                "priority": question.get("priority"),
            }
            for question in _coerce_mapping_list(state.get("clarificationQuestions"))
            if _is_open_clarification(question)
        ]
        return QualityGateOpenClarificationsContract(count=len(items), items=items)

    def _build_missing_artifacts_summary(
        self,
        state: Mapping[str, Any],
    ) -> QualityGateMissingArtifactsContract:
        items = [
            {"key": key, "label": label, "reason": reason}
            for key, label, reason in _MISSING_ARTIFACT_DEFINITIONS
            if not _artifact_present(key, state)
        ]
        return QualityGateMissingArtifactsContract(count=len(items), items=items)

    def _build_trace_summary(
        self,
        trace_summary: Mapping[str, Any],
    ) -> QualityGateTraceSummaryContract:
        raw_event_types = _coerce_mapping_list(trace_summary.get("eventTypes"))
        return QualityGateTraceSummaryContract(
            total_events=_coerce_int(trace_summary.get("totalEvents")),
            last_event_at=_coerce_optional_str(trace_summary.get("lastEventAt")),
            event_types=[
                {
                    "eventType": str(event_type.get("eventType") or "unknown"),
                    "count": _coerce_int(event_type.get("count")),
                }
                for event_type in raw_event_types
            ],
        )


def _artifact_present(key: str, state: Mapping[str, Any]) -> bool:
    if key == "candidate-architectures":
        return _has_entries(state.get("candidateArchitectures"))
    if key == "diagrams":
        return _has_entries(state.get("diagrams"))
    if key == "adrs":
        return _has_entries(state.get("adrs"))
    if key == "costs":
        return _has_entries(state.get("costEstimates"))
    if key == "iac":
        return _has_entries(state.get("iacArtifacts"))
    if key == "waf":
        waf_checklist = _coerce_mapping(state.get("wafChecklist"))
        return _has_entries(waf_checklist.get("items"))
    return False


def _has_entries(value: object) -> bool:
    if isinstance(value, dict):
        return len(value) > 0
    if isinstance(value, list | tuple):
        return len(value) > 0
    return False


def _is_open_clarification(question: Mapping[str, Any]) -> bool:
    status = str(question.get("status") or "open").strip().lower()
    if status in _OPEN_CLARIFICATION_STATUSES:
        return True
    return status not in {"answered", "resolved", "closed"}


def _derive_waf_status(item: Mapping[str, Any]) -> str:
    evaluations = _coerce_mapping_list(item.get("evaluations"))
    statuses = {
        str(evaluation.get("status") or "").strip().lower()
        for evaluation in evaluations
        if isinstance(evaluation, Mapping)
    }
    if "fixed" in statuses:
        return "covered"
    if "in_progress" in statuses:
        return "partial"
    return "not-covered"


def _weighted_percentage(*, covered: int, partial: int, total: int) -> int:
    if total <= 0:
        return 0
    return int(round(((covered + (partial * 0.5)) / total) * 100))


def _coerce_mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _coerce_mapping_list(value: object) -> list[dict[str, Any]]:
    if isinstance(value, Mapping):
        return [dict(item) for item in value.values() if isinstance(item, Mapping)]
    if isinstance(value, list | tuple):
        return [dict(item) for item in value if isinstance(item, Mapping)]
    return []


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _coerce_optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
