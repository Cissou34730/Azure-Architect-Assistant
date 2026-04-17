"""Canonical workflow result contract for stage-worker and stream payloads."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator
from pydantic.alias_generators import to_camel

from app.features.projects.contracts import PendingChangeSetContract

_WORKFLOW_RESULT_CONFIG = ConfigDict(
    populate_by_name=True,
    alias_generator=to_camel,
    extra="forbid",
)


class WorkflowCitation(BaseModel):
    model_config = _WORKFLOW_RESULT_CONFIG

    title: str
    url: str
    source: str | None = None


class StageClassification(BaseModel):
    model_config = _WORKFLOW_RESULT_CONFIG

    stage: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: Literal["agent_output", "intent_rules", "state_gaps"]
    rationale: str

    @field_validator("stage", "rationale")
    @classmethod
    def _validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Stage classification fields must not be empty")
        return cleaned


class NextStepProposal(BaseModel):
    model_config = _WORKFLOW_RESULT_CONFIG

    stage: str
    tool: str | None = None
    rationale: str
    blocking_questions: list[str] = Field(default_factory=list)

    @field_validator("stage", "rationale")
    @classmethod
    def _validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Workflow next-step fields must not be empty")
        return cleaned


class ToolCallTrace(BaseModel):
    model_config = _WORKFLOW_RESULT_CONFIG

    tool_name: str
    args_preview: str
    result_preview: str
    citations: list[str] = Field(default_factory=list)
    duration_ms: int = Field(default=0, ge=0)


class ClarificationQuestionPayloadItem(BaseModel):
    model_config = _WORKFLOW_RESULT_CONFIG

    id: str
    text: str
    theme: str
    why_it_matters: str
    architectural_impact: str
    priority: int = Field(default=1, ge=1)
    related_requirement_ids: list[str] = Field(default_factory=list)


class ClarificationQuestionsPayload(BaseModel):
    model_config = _WORKFLOW_RESULT_CONFIG

    type: Literal["clarification_questions"] = "clarification_questions"
    questions: list[ClarificationQuestionPayloadItem] = Field(default_factory=list)


class ArchitectChoiceOption(BaseModel):
    model_config = _WORKFLOW_RESULT_CONFIG

    id: str
    title: str
    tradeoffs: list[str] = Field(default_factory=list)


class ArchitectChoicePayload(BaseModel):
    model_config = _WORKFLOW_RESULT_CONFIG

    type: Literal["architect_choice"] = "architect_choice"
    prompt: str
    options: list[ArchitectChoiceOption] = Field(default_factory=list)

    @field_validator("prompt")
    @classmethod
    def _validate_prompt(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Architect choice prompt must not be empty")
        return cleaned


StructuredPayload = ClarificationQuestionsPayload | ArchitectChoicePayload
_STRUCTURED_PAYLOAD_ADAPTER: TypeAdapter[StructuredPayload] = TypeAdapter(StructuredPayload)


class WorkflowStageResult(BaseModel):
    model_config = _WORKFLOW_RESULT_CONFIG

    stage: str
    stage_classification: StageClassification | None = None
    summary: str
    pending_change_set: PendingChangeSetContract | None = None
    citations: list[WorkflowCitation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_step: NextStepProposal
    reasoning_summary: str
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
    structured_payload: StructuredPayload | None = None

    @field_validator("stage", "summary", "reasoning_summary")
    @classmethod
    def _validate_text_fields(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Workflow result text fields must not be empty")
        return cleaned


def normalize_structured_payload(payload: Any) -> dict[str, Any] | None:
    """Validate and normalize stage-specific structured payloads."""
    if payload is None:
        return None
    normalized = _STRUCTURED_PAYLOAD_ADAPTER.validate_python(payload)
    return normalized.model_dump(mode="json", by_alias=True)

