"""Contracts for project-level quality gate reporting."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _QualityGateModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class QualityGateWafSummaryContract(_QualityGateModel):
    total_items: int = Field(default=0, alias="totalItems")
    covered_items: int = Field(default=0, alias="coveredItems")
    partial_items: int = Field(default=0, alias="partialItems")
    not_covered_items: int = Field(default=0, alias="notCoveredItems")
    coverage_percentage: int = Field(default=0, alias="coveragePercentage")
    pillars: list[dict[str, Any]] = Field(default_factory=list)


class QualityGateMindMapSummaryContract(_QualityGateModel):
    total_topics: int = Field(default=0, alias="totalTopics")
    addressed_topics: int = Field(default=0, alias="addressedTopics")
    partial_topics: int = Field(default=0, alias="partialTopics")
    not_addressed_topics: int = Field(default=0, alias="notAddressedTopics")
    coverage_percentage: int = Field(default=0, alias="coveragePercentage")
    topics: list[dict[str, Any]] = Field(default_factory=list)


class QualityGateOpenClarificationsContract(_QualityGateModel):
    count: int = 0
    items: list[dict[str, Any]] = Field(default_factory=list)


class QualityGateMissingArtifactsContract(_QualityGateModel):
    count: int = 0
    items: list[dict[str, str]] = Field(default_factory=list)


class QualityGateTraceEventTypeContract(_QualityGateModel):
    event_type: str = Field(alias="eventType")
    count: int = 0


class QualityGateTraceSummaryContract(_QualityGateModel):
    total_events: int = Field(default=0, alias="totalEvents")
    last_event_at: str | None = Field(default=None, alias="lastEventAt")
    event_types: list[QualityGateTraceEventTypeContract] = Field(
        default_factory=list,
        alias="eventTypes",
    )


class QualityGateReportContract(_QualityGateModel):
    generated_at: str = Field(alias="generatedAt")
    waf: QualityGateWafSummaryContract
    mind_map: QualityGateMindMapSummaryContract = Field(alias="mindMap")
    open_clarifications: QualityGateOpenClarificationsContract = Field(
        alias="openClarifications"
    )
    missing_artifacts: QualityGateMissingArtifactsContract = Field(alias="missingArtifacts")
    trace: QualityGateTraceSummaryContract
