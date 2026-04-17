"""Contracts for structured clarification planning results."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

_CLARIFICATION_CONFIG = ConfigDict(
    populate_by_name=True,
    alias_generator=to_camel,
    extra="forbid",
)

ArchitecturalImpact = Literal["high", "medium", "low"]


class ClarificationQuestionContract(BaseModel):
    model_config = _CLARIFICATION_CONFIG

    question: str
    why_it_matters: str = Field(alias="whyItMatters")
    architectural_impact: ArchitecturalImpact = Field(alias="architecturalImpact")
    priority: int = Field(default=1, ge=1, le=5)
    related_requirement_ids: list[str] = Field(default_factory=list, alias="relatedRequirementIds")

    @field_validator("question", "why_it_matters")
    @classmethod
    def _validate_non_empty_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Clarification question fields must not be empty")
        return cleaned


class ClarificationQuestionGroupContract(BaseModel):
    model_config = _CLARIFICATION_CONFIG

    theme: str
    questions: list[ClarificationQuestionContract]

    @field_validator("theme")
    @classmethod
    def _validate_theme(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Clarification question group theme must not be empty")
        return cleaned

    @field_validator("questions")
    @classmethod
    def _validate_questions(cls, value: list[ClarificationQuestionContract]) -> list[ClarificationQuestionContract]:
        if not value:
            raise ValueError("Clarification question groups must include at least one question")
        return value


class ClarificationPlanningResultContract(BaseModel):
    model_config = _CLARIFICATION_CONFIG

    question_groups: list[ClarificationQuestionGroupContract] = Field(alias="questionGroups")

    @model_validator(mode="after")
    def _validate_total_questions(self) -> ClarificationPlanningResultContract:
        total_questions = sum(len(group.questions) for group in self.question_groups)
        if total_questions <= 0:
            raise ValueError("Clarification planning result must include at least one question")
        return self
