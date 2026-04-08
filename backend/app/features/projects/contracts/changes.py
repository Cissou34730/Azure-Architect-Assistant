"""Contracts for read-only pending change set views."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


_CHANGESET_CONFIG = ConfigDict(
    populate_by_name=True,
    alias_generator=to_camel,
    extra="ignore",
)


class ChangeSetStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ArtifactDraftType(str, Enum):
    REQUIREMENT = "requirement"
    ASSUMPTION = "assumption"
    CLARIFICATION_QUESTION = "clarification_question"
    CANDIDATE_ARCHITECTURE = "candidate_architecture"
    ADR = "adr"
    FINDING = "finding"
    DIAGRAM = "diagram"
    IAC = "iac"
    COST_ESTIMATE = "cost_estimate"
    WAF_UPDATE = "waf_update"
    OTHER = "other"


class _ChangeSetModel(BaseModel):
    model_config = _CHANGESET_CONFIG


class ArtifactDraftContract(_ChangeSetModel):
    id: str
    artifact_type: ArtifactDraftType = Field(alias="artifactType")
    artifact_id: str | None = Field(default=None, alias="artifactId")
    content: dict[str, Any] = Field(default_factory=dict)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str | None = Field(default=None, alias="createdAt")


class PendingChangeSetSummaryContract(_ChangeSetModel):
    id: str
    project_id: str = Field(alias="projectId")
    stage: str
    status: ChangeSetStatus
    created_at: str = Field(alias="createdAt")
    source_message_id: str | None = Field(default=None, alias="sourceMessageId")
    bundle_summary: str = Field(alias="bundleSummary")
    artifact_count: int = Field(alias="artifactCount")


class PendingChangeSetContract(_ChangeSetModel):
    id: str
    project_id: str = Field(alias="projectId")
    stage: str
    status: ChangeSetStatus
    created_at: str = Field(alias="createdAt")
    source_message_id: str | None = Field(default=None, alias="sourceMessageId")
    bundle_summary: str = Field(alias="bundleSummary")
    proposed_patch: dict[str, Any] = Field(default_factory=dict, alias="proposedPatch")
    artifact_drafts: list[ArtifactDraftContract] = Field(
        default_factory=list,
        alias="artifactDrafts",
    )
    citations: list[dict[str, Any]] = Field(default_factory=list)
    reviewed_at: str | None = Field(default=None, alias="reviewedAt")
    review_reason: str | None = Field(default=None, alias="reviewReason")


class ChangeSetReviewRequest(_ChangeSetModel):
    reason: str | None = None


class ChangeSetReviewResultContract(_ChangeSetModel):
    change_set: PendingChangeSetContract = Field(alias="changeSet")
    project_state: dict[str, Any] | None = Field(default=None, alias="projectState")
    conflicts: list[dict[str, Any]] = Field(default_factory=list)

