from __future__ import annotations

import re
from enum import Enum
from statistics import fmean
from typing import Any

from pydantic import BaseModel, Field

_STOPWORDS = {
    "a",
    "an",
    "and",
    "architecture",
    "create",
    "for",
    "guidance",
    "into",
    "run",
    "the",
    "this",
    "with",
}


class EvalDimension(str, Enum):
    SPECIFICITY = "specificity"
    TOOL_USAGE = "tool_usage"
    PERSISTENCE = "persistence"
    STRUCTURE = "structure"
    CHALLENGE_QUALITY = "challenge_quality"
    CITATION_GROUNDING = "citation_grounding"
    COMPLETENESS = "completeness"


class EvalScore(BaseModel):
    dimension: EvalDimension
    score: int = Field(ge=1, le=5)
    rationale: str


class TurnEvalSummary(BaseModel):
    turn_id: str
    request: str
    success: bool
    error: str | None = None
    tool_call_count: int = Field(ge=0)
    state_delta_keys: list[str] = Field(default_factory=list)
    scores: list[EvalScore]
    notes: list[str] = Field(default_factory=list)

    def score_for(self, dimension: EvalDimension) -> int:
        for score in self.scores:
            if score.dimension == dimension:
                return score.score
        raise KeyError(f"Missing score for dimension: {dimension}")

    @property
    def total_score(self) -> float:
        return round(fmean(score.score for score in self.scores), 2)


class ScenarioEvalSummary(BaseModel):
    scenario_id: str
    scenario_name: str
    missing_required_keys: list[str] = Field(default_factory=list)
    persisted_state_keys: list[str] = Field(default_factory=list)
    turns: list[TurnEvalSummary]
    dimension_averages: dict[EvalDimension, float]
    overall_score: float = Field(ge=1, le=5)
    baseline_failures: list[str] = Field(default_factory=list)


def build_phase0_eval_summary(report: dict[str, Any]) -> ScenarioEvalSummary:
    scenario = _coerce_mapping(report.get("scenario"))
    final = _coerce_mapping(report.get("final"))
    state_summary = _coerce_mapping(final.get("stateSummary"))
    persisted_state_keys = sorted(_coerce_string_list(state_summary.get("keys")))
    missing_required_keys = _coerce_string_list(final.get("missingRequiredKeys"))

    turns = [
        _build_turn_summary(step, persisted_state_keys, missing_required_keys, report)
        for step in _coerce_mapping_list(report.get("steps"))
    ]
    dimension_averages = _compute_dimension_averages(turns)
    overall_score = (
        round(fmean(dimension_averages.values()), 2) if dimension_averages else 1.0
    )
    baseline_failures = _collect_failures(
        missing_required_keys=missing_required_keys,
        report=report,
        dimension_averages=dimension_averages,
    )

    return ScenarioEvalSummary(
        scenario_id=str(scenario.get("id") or "unknown"),
        scenario_name=str(scenario.get("name") or "unknown"),
        missing_required_keys=missing_required_keys,
        persisted_state_keys=persisted_state_keys,
        turns=turns,
        dimension_averages=dimension_averages,
        overall_score=overall_score,
        baseline_failures=baseline_failures,
    )


def _build_turn_summary(
    step: dict[str, Any],
    persisted_state_keys: list[str],
    missing_required_keys: list[str],
    report: dict[str, Any],
) -> TurnEvalSummary:
    request = str(step.get("request") or "")
    answer = str(step.get("answer") or "")
    advisory = _coerce_mapping(step.get("advisoryQuality"))
    tool_call_count = sum(
        _coerce_non_negative_int(step.get(field))
        for field in ("mcpCallCount", "pricingCallCount", "kbCallCount")
    )

    scores = [
        EvalScore(
            dimension=EvalDimension.SPECIFICITY,
            score=_score_specificity(request, answer),
            rationale="Derived from meaningful overlap between the request and answer.",
        ),
        EvalScore(
            dimension=EvalDimension.TOOL_USAGE,
            score=_score_tool_usage(tool_call_count),
            rationale="Derived from captured MCP, pricing, and KB call counts.",
        ),
        EvalScore(
            dimension=EvalDimension.PERSISTENCE,
            score=_score_persistence(
                db_status=_db_status(report),
                missing_required_keys=missing_required_keys,
                persisted_state_keys=persisted_state_keys,
            ),
            rationale="Derived from DB assertions and the final persisted state shape.",
        ),
        EvalScore(
            dimension=EvalDimension.STRUCTURE,
            score=_scale_three_point_score(advisory.get("clarity")),
            rationale="Mapped from the existing advisory clarity score.",
        ),
        EvalScore(
            dimension=EvalDimension.CHALLENGE_QUALITY,
            score=_scale_three_point_score(advisory.get("correction")),
            rationale="Mapped from the existing advisory correction score.",
        ),
        EvalScore(
            dimension=EvalDimension.CITATION_GROUNDING,
            score=_score_grounding(advisory.get("evidence"), tool_call_count),
            rationale="Mapped from advisory evidence and observed research/tool activity.",
        ),
        EvalScore(
            dimension=EvalDimension.COMPLETENESS,
            score=_score_completeness(
                success=bool(step.get("success")),
                error=str(step.get("error") or ""),
                answer=answer,
                missing_required_keys=missing_required_keys,
            ),
            rationale="Derived from turn success, answer presence, and final missing keys.",
        ),
    ]

    notes: list[str] = []
    proactivity_score = _coerce_non_negative_int(advisory.get("proactivity"))
    if proactivity_score <= 0:
        notes.append("Response was passive and did not propose a next step.")

    return TurnEvalSummary(
        turn_id=str(step.get("id") or "unknown"),
        request=request,
        success=bool(step.get("success")),
        error=str(step.get("error")) if step.get("error") else None,
        tool_call_count=tool_call_count,
        state_delta_keys=persisted_state_keys,
        scores=scores,
        notes=notes,
    )


def _compute_dimension_averages(
    turns: list[TurnEvalSummary],
) -> dict[EvalDimension, float]:
    if not turns:
        return {}

    averages: dict[EvalDimension, float] = {}
    for dimension in EvalDimension:
        averages[dimension] = round(
            fmean(turn.score_for(dimension) for turn in turns),
            2,
        )
    return averages


def _collect_failures(
    *,
    missing_required_keys: list[str],
    report: dict[str, Any],
    dimension_averages: dict[EvalDimension, float],
) -> list[str]:
    failures: list[str] = []

    if missing_required_keys:
        failures.append(f"Missing required keys: {', '.join(missing_required_keys)}")
    if _db_status(report) != "PASS":
        failures.append("Database persistence assertions failed.")
    failures.extend(_collect_clarify_payload_failures(report))
    failures.extend(_collect_export_payload_failures(report))
    failures.extend(_collect_candidate_payload_failures(report))
    failures.extend(_collect_adr_payload_failures(report))
    failures.extend(_collect_cost_payload_failures(report))
    failures.extend(_collect_iac_payload_failures(report))

    for dimension, average in dimension_averages.items():
        if average <= 2.0:
            failures.append(
                f"Low {dimension.value.replace('_', ' ')} score ({average:.1f}/5)."
            )
    return failures


def _collect_clarify_payload_failures(report: dict[str, Any]) -> list[str]:
    final = _coerce_mapping(report.get("final"))
    clarify_payload = _coerce_mapping(final.get("clarifyPayload"))
    if not clarify_payload:
        return []

    failures: list[str] = []
    missing_keys = _coerce_string_list(clarify_payload.get("missingRequiredKeys"))
    if missing_keys:
        failures.append(f"Clarify payload missing required keys: {', '.join(missing_keys)}")

    question_count = clarify_payload.get("questionCount")
    if not isinstance(question_count, int) or question_count < 1:
        failures.append("Clarify payload did not produce any questions.")

    why_it_matters_count = clarify_payload.get("whyItMattersCount")
    if (
        isinstance(question_count, int)
        and question_count > 0
        and (not isinstance(why_it_matters_count, int) or why_it_matters_count < question_count)
    ):
        failures.append("Clarify payload missing rationale for one or more questions.")

    theme_count = clarify_payload.get("themeCount")
    if not isinstance(theme_count, int) or theme_count < 1:
        failures.append("Clarify payload did not group questions under any theme.")

    ungrouped_question_count = clarify_payload.get("ungroupedQuestionCount")
    if isinstance(ungrouped_question_count, int) and ungrouped_question_count > 0:
        failures.append("Clarify payload left one or more questions outside a named theme.")

    return failures


def _collect_export_payload_failures(report: dict[str, Any]) -> list[str]:
    final = _coerce_mapping(report.get("final"))
    export_payload = _coerce_mapping(final.get("exportPayload"))
    if not export_payload:
        return []

    failures: list[str] = []
    missing_keys = _coerce_string_list(export_payload.get("missingRequiredKeys"))
    if missing_keys:
        failures.append(f"Export payload missing required keys: {', '.join(missing_keys)}")

    state_missing_keys = _coerce_string_list(export_payload.get("stateMissingRequiredKeys"))
    if state_missing_keys:
        failures.append(
            "Export payload state missing required keys: "
            + ", ".join(state_missing_keys)
        )

    scorecard = _coerce_mapping(export_payload.get("mindmapCoverageScorecard"))
    missing_topics = _coerce_string_list(scorecard.get("missingTopicKeys"))
    topic_count = scorecard.get("topicCount")
    if missing_topics or (isinstance(topic_count, int) and topic_count < 13):
        failures.append("Export payload mind map scorecard does not cover all 13 topics.")

    return failures


def _collect_candidate_payload_failures(report: dict[str, Any]) -> list[str]:
    final = _coerce_mapping(report.get("final"))
    candidate_payload = _coerce_mapping(final.get("candidatePayload"))
    if not candidate_payload:
        return []

    failures: list[str] = []
    missing_keys = _coerce_string_list(candidate_payload.get("missingRequiredKeys"))
    if missing_keys:
        failures.append(f"Candidate payload missing required keys: {', '.join(missing_keys)}")

    latest_candidate = _coerce_mapping(candidate_payload.get("latestCandidate"))
    if candidate_payload.get("present"):
        citation_count = latest_candidate.get("citationCount")
        if not isinstance(citation_count, int) or citation_count < 1:
            failures.append("Candidate payload latest candidate missing citations.")

        diagram_id_count = latest_candidate.get("diagramIdCount")
        if not isinstance(diagram_id_count, int) or diagram_id_count < 1:
            failures.append("Candidate payload latest candidate missing diagram links.")

    return failures


def _collect_adr_payload_failures(report: dict[str, Any]) -> list[str]:
    final = _coerce_mapping(report.get("final"))
    adr_payload = _coerce_mapping(final.get("adrPayload"))
    if not adr_payload:
        return []

    failures: list[str] = []
    missing_keys = _coerce_string_list(adr_payload.get("missingRequiredKeys"))
    if missing_keys:
        failures.append(f"ADR payload missing required keys: {', '.join(missing_keys)}")

    latest_change_set = _coerce_mapping(adr_payload.get("latestChangeSet"))
    if adr_payload.get("present"):
        if str(latest_change_set.get("status") or "").lower() != "pending":
            failures.append("ADR payload latest change set is not pending.")

        if not bool(latest_change_set.get("hasLifecycleCommand")):
            failures.append("ADR payload missing lifecycle command.")

        adr_draft_count = latest_change_set.get("adrDraftCount")
        if not isinstance(adr_draft_count, int) or adr_draft_count < 1:
            failures.append("ADR payload missing ADR draft artifacts.")

        missing_draft_fields = _coerce_string_list(latest_change_set.get("missingDraftFields"))
        if missing_draft_fields:
            failures.append(
                "ADR payload latest draft missing fields: " + ", ".join(missing_draft_fields)
            )

    return failures


def _collect_cost_payload_failures(report: dict[str, Any]) -> list[str]:
    final = _coerce_mapping(report.get("final"))
    cost_payload = _coerce_mapping(final.get("costPayload"))
    if not cost_payload:
        return []

    failures: list[str] = []
    missing_keys = _coerce_string_list(cost_payload.get("missingRequiredKeys"))
    if missing_keys:
        failures.append(f"Cost payload missing required keys: {', '.join(missing_keys)}")

    pricing_log_count = cost_payload.get("pricingLogCount")
    if not isinstance(pricing_log_count, int) or pricing_log_count < 1:
        failures.append("Cost payload missing pricing log evidence.")

    latest_estimate = _coerce_mapping(cost_payload.get("latestEstimate"))
    if cost_payload.get("present") and latest_estimate.get("totalMonthlyCost") is None:
        failures.append("Cost payload latest estimate missing totalMonthlyCost.")

    return failures


def _collect_iac_payload_failures(report: dict[str, Any]) -> list[str]:
    final = _coerce_mapping(report.get("final"))
    iac_payload = _coerce_mapping(final.get("iacPayload"))
    if not iac_payload:
        return []

    failures: list[str] = []
    missing_keys = _coerce_string_list(iac_payload.get("missingRequiredKeys"))
    if missing_keys:
        failures.append(f"IaC payload missing required keys: {', '.join(missing_keys)}")

    latest_artifact = _coerce_mapping(iac_payload.get("latestArtifact"))
    file_count = latest_artifact.get("fileCount")
    if iac_payload.get("present") and (not isinstance(file_count, int) or file_count < 1):
        failures.append("IaC payload latest artifact missing files.")

    validation_result_count = latest_artifact.get("validationResultCount")
    if iac_payload.get("present") and (
        not isinstance(validation_result_count, int) or validation_result_count < 1
    ):
        failures.append("IaC payload missing validation evidence.")

    return failures


def _score_specificity(request: str, answer: str) -> int:
    request_terms = _meaningful_terms(request)
    if not request_terms:
        return 1

    overlap = len(request_terms & _meaningful_terms(answer))
    if overlap >= 5:
        return 5
    if overlap >= 3:
        return 4
    if overlap >= 2:
        return 3
    if answer.strip():
        return 2
    return 1


def _score_tool_usage(tool_call_count: int) -> int:
    if tool_call_count >= 4:
        return 5
    if tool_call_count == 3:
        return 4
    if tool_call_count == 2:
        return 3
    if tool_call_count == 1:
        return 2
    return 1


def _score_persistence(
    *,
    db_status: str,
    missing_required_keys: list[str],
    persisted_state_keys: list[str],
) -> int:
    if db_status != "PASS":
        return 1
    if db_status == "PASS" and not missing_required_keys:
        return 5
    if db_status == "PASS":
        return 3
    if persisted_state_keys:
        return 2
    return 1


def _score_grounding(evidence_score: Any, tool_call_count: int) -> int:
    scaled = _scale_three_point_score(evidence_score)
    if scaled < 5 and tool_call_count >= 3:
        return min(5, scaled + 1)
    return scaled


def _score_completeness(
    *,
    success: bool,
    error: str,
    answer: str,
    missing_required_keys: list[str],
) -> int:
    if not success:
        return 1
    if error:
        return 2
    if not answer.strip():
        return 1
    if not missing_required_keys and len(answer.strip()) >= 120:
        return 5
    if not missing_required_keys:
        return 4
    return 3


def _scale_three_point_score(value: Any) -> int:
    match _coerce_non_negative_int(value):
        case 2:
            return 5
        case 1:
            return 3
        case _:
            return 1


def _coerce_non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(0, value)
    return 0


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items() if isinstance(key, str)}


def _coerce_mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _coerce_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _meaningful_terms(text: str) -> set[str]:
    terms = {
        term
        for term in re.findall(r"[a-z0-9]+", text.lower())
        if len(term) > 3 and term not in _STOPWORDS
    }
    return terms


def _db_status(report: dict[str, Any]) -> str:
    db_persistence = _coerce_mapping(report.get("dbPersistence"))
    return str(db_persistence.get("status") or "").upper()


# ---------------------------------------------------------------------------
# Journey Eval Reporting (P15)
# ---------------------------------------------------------------------------


class JourneyScenarioDimension(str, Enum):
    FIELD_PRESENCE = "field_presence"
    PATTERN_SAFETY = "pattern_safety"


class JourneyScenarioReport(BaseModel):
    scenario_id: str
    stage: str
    passed: bool
    missing_fields: list[str] = Field(default_factory=list)
    forbidden_pattern_matches: list[str] = Field(default_factory=list)
    failure_reasons: list[str] = Field(default_factory=list)


class JourneyEvalReport(BaseModel):
    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    pass_rate: float = Field(ge=0.0, le=1.0)
    scenarios: list[JourneyScenarioReport]


def build_journey_eval_report(results: list[Any]) -> JourneyEvalReport:
    """Build a JourneyEvalReport from a list of JourneyScenarioResult objects."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    pass_rate = round(passed / total, 4) if total > 0 else 0.0

    scenario_reports = [
        JourneyScenarioReport(
            scenario_id=r.scenario.scenario_id,
            stage=r.scenario.stage,
            passed=r.passed,
            missing_fields=list(r.missing_fields),
            forbidden_pattern_matches=list(r.forbidden_pattern_matches),
            failure_reasons=r.failure_reasons,
        )
        for r in results
    ]

    return JourneyEvalReport(
        total=total,
        passed=passed,
        failed=failed,
        pass_rate=pass_rate,
        scenarios=scenario_reports,
    )
