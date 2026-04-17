"""Contracts for structured clarification resolution results."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

_CLARIFICATION_RESOLUTION_CONFIG = ConfigDict(
    populate_by_name=True,
    alias_generator=to_camel,
    extra="forbid",
)

AnsweredStatus = Literal["answered"]


class ClarificationRequirementUpdateContract(BaseModel):
    model_config = _CLARIFICATION_RESOLUTION_CONFIG

    requirement_id: str = Field(alias="requirementId")
    text: str
    category: str | None = None
    answer_summary: str = Field(alias="answerSummary")
    related_question_ids: list[str] = Field(default_factory=list, alias="relatedQuestionIds")

    @field_validator("requirement_id", "text", "answer_summary")
    @classmethod
    def _validate_non_empty_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Clarification requirement updates must not contain empty text")
        return cleaned


class ClarificationQuestionUpdateContract(BaseModel):
    model_config = _CLARIFICATION_RESOLUTION_CONFIG

    question_id: str = Field(alias="questionId")
    status: AnsweredStatus = "answered"
    answer_summary: str = Field(alias="answerSummary")
    related_requirement_ids: list[str] = Field(
        default_factory=list,
        alias="relatedRequirementIds",
    )

    @field_validator("question_id", "answer_summary")
    @classmethod
    def _validate_non_empty_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Clarification question updates must not contain empty text")
        return cleaned


class ClarificationAssumptionContract(BaseModel):
    model_config = _CLARIFICATION_RESOLUTION_CONFIG

    text: str
    related_requirement_ids: list[str] = Field(default_factory=list, alias="relatedRequirementIds")

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Clarification assumptions must not be empty")
        return cleaned


class ClarificationResolutionResultContract(BaseModel):
    model_config = _CLARIFICATION_RESOLUTION_CONFIG

    summary: str
    requirement_updates: list[ClarificationRequirementUpdateContract] = Field(
        default_factory=list,
        alias="requirementUpdates",
    )
    question_updates: list[ClarificationQuestionUpdateContract] = Field(
        default_factory=list,
        alias="questionUpdates",
    )
    assumptions: list[ClarificationAssumptionContract] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("summary")
    @classmethod
    def _validate_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Clarification resolution summary must not be empty")
        return cleaned

    @model_validator(mode="after")
    def _validate_actionable_output(self) -> ClarificationResolutionResultContract:
        if not self.requirement_updates and not self.question_updates and not self.assumptions:
            raise ValueError("Clarification resolution result must include at least one update")
        return self
