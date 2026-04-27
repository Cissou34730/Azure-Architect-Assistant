"""Typed Pydantic output contracts for each LangGraph stage (P12).

Each contract represents the validated shape of an LLM response for its stage.
The helper ``_parse_and_validate_output`` provides a graceful-degradation
parse/validate step: on success it returns ``(model, None)``; on any failure
it logs a WARNING and returns ``(None, raw)`` so the caller can still forward
the raw text downstream without crashing.
"""

from __future__ import annotations

import json
import logging
from typing import Any, TypeVar

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


# ---------------------------------------------------------------------------
# Stage output contracts
# ---------------------------------------------------------------------------


class RequirementsExtractionOutput(BaseModel):
    """Structured output from the requirements extraction stage."""

    functional_requirements: list[str] = Field(
        default_factory=list,
        description="List of functional requirements identified in this extraction pass.",
    )
    non_functional_requirements: list[str] = Field(
        default_factory=list,
        description="Non-functional requirements (NFRs) such as availability, performance, security.",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Hard constraints that bound the solution space (e.g. region, compliance, budget cap).",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Questions that remain unanswered and may block design decisions.",
    )


class _ClarificationQuestion(BaseModel):
    """A single clarification question with decision context."""

    question: str = Field(description="The clarification question text.")
    decision_impact: str = Field(
        default="",
        description="How the answer affects an architecture or design decision.",
    )
    default_assumption: str = Field(
        default="",
        description="The assumption the assistant will use if the user does not answer.",
    )


class ClarificationPlanOutput(BaseModel):
    """Structured output from the clarification planning stage."""

    questions: list[_ClarificationQuestion] = Field(
        default_factory=list,
        description="Ordered list of clarification questions.",
    )
    proceed_with_defaults: bool = Field(
        default=False,
        description="True when the model recommends proceeding with default assumptions.",
    )


class ArchitectureDraftOutput(BaseModel):
    """Structured output from the architecture candidate drafting stage."""

    candidate_name: str = Field(description="Short name / label for the architecture candidate.")
    summary: str = Field(description="One-paragraph executive summary of the candidate.")
    components: list[str] = Field(
        default_factory=list,
        description="Key Azure services / components in the candidate.",
    )
    trade_offs: list[str] = Field(
        default_factory=list,
        description="Notable trade-offs of this candidate vs. alternatives.",
    )
    risks: list[str] = Field(
        default_factory=list,
        description="Identified risks and their potential impact.",
    )
    waf_highlights: dict[str, Any] = Field(
        default_factory=dict,
        description="WAF pillar highlights keyed by pillar name.",
    )
    next_steps: list[str] = Field(
        default_factory=list,
        description="Immediate next steps to validate or implement this candidate.",
    )


class ValidationOutput(BaseModel):
    """Structured output from the WAF validation stage."""

    waf_findings: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of WAF findings, each containing pillar, severity, description, etc.",
    )
    severity_breakdown: dict[str, Any] = Field(
        default_factory=dict,
        description="Count of findings per severity level (e.g. {'high': 2, 'medium': 1}).",
    )
    top_issues: list[str] = Field(
        default_factory=list,
        description="Short descriptions of the most critical issues found.",
    )
    recommendation: str = Field(
        default="",
        description="Overall recommendation based on the validation findings.",
    )


class AdrDraftOutput(BaseModel):
    """Structured output from the ADR drafting stage."""

    title: str = Field(description="ADR title (e.g. 'ADR-001: Use AKS for compute').")
    status: str = Field(
        default="proposed",
        description="ADR lifecycle status: proposed | accepted | superseded | deprecated.",
    )
    context: str = Field(description="Context section describing the situation and forces.")
    decision: str = Field(description="The decision that was made.")
    consequences: str = Field(description="Consequences of the decision (positive and negative).")
    alternatives_considered: list[str] = Field(
        default_factory=list,
        description="Alternative options that were evaluated but not chosen.",
    )


# ---------------------------------------------------------------------------
# Parse + validate helper
# ---------------------------------------------------------------------------


def _parse_and_validate_output(
    raw: str,
    contract: type[T],
) -> tuple[T | None, str | None]:
    """Parse *raw* as JSON and validate it against *contract*.

    Returns:
        ``(model_instance, None)`` on success.
        ``(None, raw)``           on any failure (malformed JSON or schema mismatch).

    The fallback raw string lets callers forward the original text downstream
    without crashing, ensuring graceful degradation.
    """
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning(
            "Stage output JSON parse failed for contract %s: %s",
            contract.__name__,
            exc,
        )
        return None, raw

    try:
        model = contract.model_validate(parsed)
        return model, None
    except ValidationError as exc:
        logger.warning(
            "Stage output schema validation failed for contract %s: %s",
            contract.__name__,
            exc,
        )
        return None, raw


__all__ = [
    "AdrDraftOutput",
    "ArchitectureDraftOutput",
    "ClarificationPlanOutput",
    "RequirementsExtractionOutput",
    "ValidationOutput",
    "_parse_and_validate_output",
]
