from __future__ import annotations

import inspect
import json
import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

_CITATION_RE = re.compile(r"https?://[^\s)\]}>,]+", re.IGNORECASE)
_WORD_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_DECISION_SIGNALS = (
    "recommend",
    "because",
    "trade-off",
    "tradeoff",
    "risk",
    "assumption",
    "decision",
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ThinReceiptRule(_StrictModel):
    max_length: int = Field(default=200, ge=1)
    required_keywords: list[str] = Field(min_length=1)


class QualityAssertions(_StrictModel):
    """Reference-oriented assertions that avoid exact-answer snapshots."""

    required_concepts: dict[str, list[str]] = Field(default_factory=dict)
    forbidden_claim_patterns: list[str] = Field(default_factory=list)
    require_citations: bool = False
    allowed_citation_hosts: list[str] = Field(default_factory=list)
    max_words: int | None = Field(default=None, ge=1)
    minimum_decision_signals: int = Field(default=0, ge=0)


class JourneyScenarioManifest(_StrictModel):
    scenario_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    input: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    expected_fields: list[str] = Field(min_length=1)
    forbidden_patterns: list[str] = Field(default_factory=list)
    required_answer_keywords: list[str] = Field(default_factory=list)
    thin_receipt_detection: ThinReceiptRule | None = None
    quality_gate_must_retry_on: list[str] = Field(default_factory=list)
    quality_gate_must_pass_on_keywords: list[str] = Field(default_factory=list)
    quality_assertions: QualityAssertions = Field(default_factory=QualityAssertions)
    tags: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class JourneyScenario:
    scenario_id: str
    description: str
    input: str
    stage: str
    expected_fields: tuple[str, ...]
    forbidden_patterns: tuple[str, ...]
    required_answer_keywords: tuple[str, ...] = ()
    thin_receipt_detection: ThinReceiptRule | None = None
    quality_gate_must_retry_on: tuple[str, ...] = ()
    quality_gate_must_pass_on_keywords: tuple[str, ...] = ()
    quality_assertions: QualityAssertions = field(default_factory=QualityAssertions)
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class JourneyScenarioResult:
    scenario: JourneyScenario
    passed: bool
    missing_fields: tuple[str, ...] = ()
    forbidden_pattern_matches: tuple[str, ...] = ()
    wrong_stage: str | None = None
    missing_required_keywords: tuple[str, ...] = ()
    invalid_patterns: tuple[str, ...] = ()
    assertion_failures: tuple[str, ...] = ()
    quality_gate_failures: tuple[str, ...] = ()

    @property
    def failure_reasons(self) -> list[str]:
        reasons: list[str] = []
        if self.missing_fields:
            reasons.append(f"Missing expected fields: {', '.join(self.missing_fields)}")
        if self.wrong_stage:
            reasons.append(
                f"Expected stage '{self.scenario.stage}', got '{self.wrong_stage}'."
            )
        if self.forbidden_pattern_matches:
            reasons.append(
                f"Forbidden patterns found: {', '.join(self.forbidden_pattern_matches)}"
            )
        if self.invalid_patterns:
            reasons.append(f"Invalid scenario regex patterns: {', '.join(self.invalid_patterns)}")
        if self.missing_required_keywords:
            reasons.append(
                "Missing required answer concepts: "
                + ", ".join(self.missing_required_keywords)
            )
        reasons.extend(self.assertion_failures)
        reasons.extend(self.quality_gate_failures)
        return reasons


@dataclass(frozen=True)
class JourneyEvalRun:
    results: tuple[JourneyScenarioResult, ...]

    @property
    def passed_count(self) -> int:
        return sum(result.passed for result in self.results)

    @property
    def failed_count(self) -> int:
        return sum(not result.passed for result in self.results)

    @property
    def all_passed(self) -> bool:
        return bool(self.results) and all(result.passed for result in self.results)


def discover_journey_scenarios(root: Path) -> list[JourneyScenario]:
    return [load_journey_scenario(path) for path in sorted(root.glob("journey-*.yaml"))]


def load_journey_scenario(yaml_path: Path) -> JourneyScenario:
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Expected a YAML object in {yaml_path}")
    try:
        manifest = JourneyScenarioManifest.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Invalid journey scenario {yaml_path}: {exc}") from exc

    _validate_regexes(
        [
            *manifest.forbidden_patterns,
            *manifest.quality_assertions.forbidden_claim_patterns,
        ],
        yaml_path,
    )
    return JourneyScenario(
        scenario_id=manifest.scenario_id,
        description=manifest.description,
        input=manifest.input,
        stage=manifest.stage,
        expected_fields=tuple(manifest.expected_fields),
        forbidden_patterns=tuple(manifest.forbidden_patterns),
        required_answer_keywords=tuple(manifest.required_answer_keywords),
        thin_receipt_detection=manifest.thin_receipt_detection,
        quality_gate_must_retry_on=tuple(manifest.quality_gate_must_retry_on),
        quality_gate_must_pass_on_keywords=tuple(
            manifest.quality_gate_must_pass_on_keywords
        ),
        quality_assertions=manifest.quality_assertions,
        tags=tuple(manifest.tags),
    )


def _validate_regexes(patterns: list[str], path: Path) -> None:
    for pattern in patterns:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"Invalid regex '{pattern}' in {path}: {exc}") from exc


def validate_journey_response(
    response: dict[str, Any],
    scenario: JourneyScenario,
    response_text: str = "",
) -> JourneyScenarioResult:
    missing_fields = tuple(
        field_path
        for field_path in scenario.expected_fields
        if not _check_field_path(response, field_path)
    )
    actual_stage = str(response.get("stage") or "").strip()
    wrong_stage = None if actual_stage == scenario.stage else (actual_stage or "<missing>")
    text_to_check = response_text.strip() or response_text_from_payload(response)
    lower_text = text_to_check.lower()

    forbidden_matches, invalid_patterns = _matching_patterns(
        text_to_check,
        scenario.forbidden_patterns,
    )
    missing_keywords = [
        keyword
        for keyword in (
            *scenario.required_answer_keywords,
            *scenario.quality_gate_must_pass_on_keywords,
        )
        if keyword.lower() not in lower_text
    ]
    missing_keywords = list(dict.fromkeys(missing_keywords))
    assertion_failures = _evaluate_quality_assertions(
        text=text_to_check,
        response=response,
        assertions=scenario.quality_assertions,
    )

    if scenario.thin_receipt_detection is not None:
        rule = scenario.thin_receipt_detection
        missing_receipt_terms = [
            keyword
            for keyword in rule.required_keywords
            if keyword.lower() not in lower_text
        ]
        if len(text_to_check) <= rule.max_length and missing_receipt_terms:
            assertion_failures.append(
                "Thin receipt detected; missing decision content: "
                + ", ".join(missing_receipt_terms)
            )

    quality_gate_failures = _evaluate_quality_gate_examples(scenario)
    passed = not any(
        (
            missing_fields,
            wrong_stage,
            forbidden_matches,
            invalid_patterns,
            missing_keywords,
            assertion_failures,
            quality_gate_failures,
        )
    )
    return JourneyScenarioResult(
        scenario=scenario,
        passed=passed,
        missing_fields=missing_fields,
        forbidden_pattern_matches=tuple(forbidden_matches),
        wrong_stage=wrong_stage,
        missing_required_keywords=tuple(missing_keywords),
        invalid_patterns=tuple(invalid_patterns),
        assertion_failures=tuple(assertion_failures),
        quality_gate_failures=tuple(quality_gate_failures),
    )


def _matching_patterns(text: str, patterns: tuple[str, ...]) -> tuple[list[str], list[str]]:
    matches: list[str] = []
    invalid: list[str] = []
    for pattern in patterns:
        try:
            if re.search(pattern, text):
                matches.append(pattern)
        except re.error:
            invalid.append(pattern)
    return matches, invalid


def _evaluate_quality_assertions(
    *,
    text: str,
    response: Mapping[str, Any],
    assertions: QualityAssertions,
) -> list[str]:
    failures: list[str] = []
    lower_text = text.lower()
    for label, acceptable_terms in assertions.required_concepts.items():
        if not acceptable_terms or not any(
            term.lower() in lower_text for term in acceptable_terms
        ):
            failures.append(f"Missing required concept '{label}'.")

    for pattern in assertions.forbidden_claim_patterns:
        if re.search(pattern, text):
            failures.append(f"Forbidden or unsupported claim matched: {pattern}")

    citations = _extract_citations(text, response)
    if assertions.require_citations and not citations:
        failures.append("No source citation was provided for a grounded scenario.")
    if assertions.allowed_citation_hosts:
        allowed = tuple(host.lower() for host in assertions.allowed_citation_hosts)
        for citation in citations:
            if not any(host in citation.lower() for host in allowed):
                failures.append(f"Citation host is not approved for this scenario: {citation}")

    word_count = len(_WORD_RE.findall(text))
    if assertions.max_words is not None and word_count > assertions.max_words:
        failures.append(
            f"Answer contains {word_count} words; maximum is {assertions.max_words}."
        )
    signal_count = sum(signal in lower_text for signal in _DECISION_SIGNALS)
    if signal_count < assertions.minimum_decision_signals:
        failures.append(
            f"Answer has {signal_count} decision signals; "
            f"minimum is {assertions.minimum_decision_signals}."
        )
    return failures


def _extract_citations(text: str, response: Mapping[str, Any]) -> list[str]:
    citations = list(_CITATION_RE.findall(text))
    raw_citations = response.get("citations") or response.get("sourceCitations")
    if isinstance(raw_citations, list):
        for citation in raw_citations:
            if isinstance(citation, str):
                citations.append(citation)
            elif isinstance(citation, Mapping):
                value = citation.get("url") or citation.get("id")
                if value:
                    citations.append(str(value))
    return list(dict.fromkeys(citations))


def _evaluate_quality_gate_examples(scenario: JourneyScenario) -> list[str]:
    if not scenario.quality_gate_must_retry_on:
        return []
    from app.agents_system.langgraph.nodes.quality_gate import completeness_check

    failures: list[str] = []
    for example in scenario.quality_gate_must_retry_on:
        result = completeness_check(
            {
                "next_stage": scenario.stage,
                "agent_output": example,
                "artifact_edit_detected": True,
                "intermediate_steps": [
                    {"tool": "aaa_generate_candidate_architecture"}
                ],
                "quality_retry_count": 0,
                "handled_by_stage_worker": False,
            }
        )
        if result != "retry":
            failures.append(f"Quality gate accepted known-bad output: {example}")
    return failures


def response_text_from_payload(response: Mapping[str, Any]) -> str:
    for key in ("summary", "answer", "agent_output", "final_answer"):
        value = response.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return json.dumps(response, ensure_ascii=False)


def _check_field_path(obj: Any, path: str) -> bool:
    current = obj
    for part in path.split("."):
        if "[" in part:
            key = part[: part.index("[")]
            if not isinstance(current, dict) or key not in current:
                return False
            current = current[key]
            if not isinstance(current, list) or not current:
                return False
            current = current[0]
        else:
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
    return current not in (None, "", [], {})


def run_journey_eval_harness(
    *,
    root: Path,
    responses: dict[str, dict[str, Any]] | None = None,
    response_texts: dict[str, str] | None = None,
) -> JourneyEvalRun:
    return JourneyEvalRun(
        results=tuple(
            validate_journey_response(
                response=(responses or {}).get(scenario.scenario_id, {}),
                scenario=scenario,
                response_text=(response_texts or {}).get(scenario.scenario_id, ""),
            )
            for scenario in discover_journey_scenarios(root)
        )
    )


JourneyExecutor = Callable[
    [JourneyScenario],
    dict[str, Any] | Awaitable[dict[str, Any]],
]


async def run_live_journey_eval_harness(
    executor: JourneyExecutor,
    *,
    root: Path,
) -> JourneyEvalRun:
    """Execute real scenario input through an adapter before evaluating it."""

    results: list[JourneyScenarioResult] = []
    for scenario in discover_journey_scenarios(root):
        response = executor(scenario)
        if inspect.isawaitable(response):
            response = await response
        if not isinstance(response, dict):
            raise TypeError(
                f"Live journey executor returned {type(response).__name__} "
                f"for {scenario.scenario_id}; expected dict."
            )
        results.append(
            validate_journey_response(
                response=response,
                scenario=scenario,
                response_text=response_text_from_payload(response),
            )
        )
    return JourneyEvalRun(results=tuple(results))
