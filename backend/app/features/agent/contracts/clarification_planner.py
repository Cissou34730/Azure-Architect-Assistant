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


class CustomerClarificationQuestionContract(BaseModel):
    """A clarification question targeted at the customer to resolve requirement gaps."""

    model_config = _CLARIFICATION_CONFIG

    question: str
    why_it_matters: str
    clarification_target: Literal["conflict", "missing_input", "ambiguity", "inconsistency"] = "missing_input"
    source_refs: list[str] = Field(default_factory=list)
    default_assumption: str | None = None
    # Backward-compat fields kept for existing tests and the clarify node
    architectural_impact: ArchitecturalImpact = "medium"
    priority: int = Field(default=1, ge=1, le=5)
    related_requirement_ids: list[str] = Field(default_factory=list)
    affected_decision: str | None = None
    risk_if_wrong: str | None = None

    @field_validator("question", "why_it_matters")
    @classmethod
    def _validate_non_empty_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Clarification question fields must not be empty")
        return cleaned


class CustomerClarificationQuestionGroupContract(BaseModel):
    """A themed group of customer-facing clarification questions."""

    model_config = _CLARIFICATION_CONFIG

    theme: str
    questions: list[CustomerClarificationQuestionContract]

    @field_validator("theme")
    @classmethod
    def _validate_theme(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Clarification question group theme must not be empty")
        return cleaned

    @field_validator("questions")
    @classmethod
    def _validate_questions(
        cls, value: list[CustomerClarificationQuestionContract]
    ) -> list[CustomerClarificationQuestionContract]:
        if not value:
            raise ValueError("Clarification question groups must include at least one question")
        return value


class ArchitectQuestionCoverageSource(BaseModel):
    """A WAF checklist item, mindmap topic, or other artefact that drives an architect question."""

    model_config = _CLARIFICATION_CONFIG

    kind: Literal["waf", "mindmap", "requirement", "conflict", "mixed"]
    id: str
    pillar: str | None = None  # WAF pillar when kind == "waf"


class ArchitectQuestionContract(BaseModel):
    """An internal architect question tied to WAF/mindmap gaps with full lifecycle tracking."""

    model_config = _CLARIFICATION_CONFIG

    question: str
    design_decision: str
    coverage_sources: list[ArchitectQuestionCoverageSource] = Field(default_factory=list)
    risk_if_unanswered: str
    recommended_evidence: list[str] = Field(default_factory=list)
    status: Literal["open", "answered", "deferred", "not_applicable"] = "open"
    answer: str | None = None
    answered_at: str | None = None  # ISO timestamp
    answer_source: str | None = None


class ArchitectQuestionGroupContract(BaseModel):
    """A themed group of internal architect questions."""

    model_config = _CLARIFICATION_CONFIG

    theme: str
    questions: list[ArchitectQuestionContract]

    @field_validator("theme")
    @classmethod
    def _validate_theme(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Architect question group theme must not be empty")
        return cleaned

    @field_validator("questions")
    @classmethod
    def _validate_questions(cls, value: list[ArchitectQuestionContract]) -> list[ArchitectQuestionContract]:
        if not value:
            raise ValueError("Architect question groups must include at least one question")
        return value


class UncoveredWafGap(BaseModel):
    """A WAF checklist item not covered by any architect question."""

    model_config = _CLARIFICATION_CONFIG

    item_id: str


class ClarificationPlanningResultContract(BaseModel):
    model_config = _CLARIFICATION_CONFIG

    customer_clarification_groups: list[CustomerClarificationQuestionGroupContract] = Field(
        default_factory=list
    )
    architect_question_groups: list[ArchitectQuestionGroupContract] = Field(default_factory=list)
    # WAF gaps not covered by any architect question — populated by the worker
    uncovered_waf_gaps: list[UncoveredWafGap] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _handle_legacy_input(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        # Reject the old camelCase JSON key — the planner must now emit the split shape
        if "questionGroups" in data:
            raise ValueError(
                "questionGroups is no longer supported; "
                "use customerClarificationGroups and architectQuestionGroups"
            )
        # Accept the old snake_case Python kwarg for backward compatibility with
        # internal callers (e.g. _filter_and_prioritize, _build_plan in tests)
        if (
            "question_groups" in data
            and "customer_clarification_groups" not in data
            and "customerClarificationGroups" not in data
        ):
            data = dict(data)
            data["customer_clarification_groups"] = data.pop("question_groups")
        return data

    @model_validator(mode="after")
    def _validate_has_content(self) -> ClarificationPlanningResultContract:
        total = sum(len(g.questions) for g in self.customer_clarification_groups) + sum(
            len(g.questions) for g in self.architect_question_groups
        )
        if total <= 0:
            raise ValueError("ClarificationPlanningResultContract must include at least one question")
        return self

    @property
    def question_groups(self) -> list[CustomerClarificationQuestionGroupContract]:
        """Backward-compatibility shim — returns customer_clarification_groups."""
        return self.customer_clarification_groups


# Backward compatibility aliases for code that hasn't been updated to the split shape yet
ClarificationQuestionContract = CustomerClarificationQuestionContract
ClarificationQuestionGroupContract = CustomerClarificationQuestionGroupContract
