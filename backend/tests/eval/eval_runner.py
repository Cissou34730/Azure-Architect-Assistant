from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Any

import yaml

from .reporting import ScenarioEvalSummary, build_phase0_eval_summary

_GOLDEN_SCENARIOS_DIR = Path(__file__).resolve().parent / "golden_scenarios"


@dataclass(frozen=True)
class GoldenScenario:
    id: str
    name: str
    description: str
    report_path: Path
    tags: tuple[str, ...] = ()
    expected_baseline_failures: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvaluatedGoldenScenario:
    scenario: GoldenScenario
    summary: ScenarioEvalSummary
    missing_expected_failures: tuple[str, ...] = ()
    unexpected_failures: tuple[str, ...] = ()

    @property
    def matches_expected_failures(self) -> bool:
        return not self.missing_expected_failures and not self.unexpected_failures


@dataclass(frozen=True)
class EvalHarnessRun:
    scenarios: tuple[EvaluatedGoldenScenario, ...]

    @property
    def scenario_count(self) -> int:
        return len(self.scenarios)

    @property
    def mismatched_scenario_count(self) -> int:
        return sum(0 if scenario.matches_expected_failures else 1 for scenario in self.scenarios)

    @property
    def average_overall_score(self) -> float:
        if not self.scenarios:
            return 0.0
        return round(fmean(scenario.summary.overall_score for scenario in self.scenarios), 2)


def discover_golden_scenarios(scenarios_dir: Path | None = None) -> list[GoldenScenario]:
    root = scenarios_dir or _GOLDEN_SCENARIOS_DIR
    manifests = sorted(root.glob("*/scenario.json"))
    return [load_golden_scenario(manifest_path) for manifest_path in manifests]


def load_golden_scenario(manifest_path: Path) -> GoldenScenario:
    raw_manifest = _load_json_object(manifest_path)
    report_path = manifest_path.with_name("report.normalized.json")
    if not report_path.exists():
        raise FileNotFoundError(f"Golden scenario report not found: {report_path}")

    scenario_id = str(raw_manifest.get("id") or "").strip()
    scenario_name = str(raw_manifest.get("name") or "").strip()
    if not scenario_id:
        raise ValueError(f"Golden scenario id is required: {manifest_path}")
    if not scenario_name:
        raise ValueError(f"Golden scenario name is required: {manifest_path}")

    description = str(raw_manifest.get("description") or "").strip()
    return GoldenScenario(
        id=scenario_id,
        name=scenario_name,
        description=description,
        report_path=report_path,
        tags=_coerce_string_tuple(raw_manifest.get("tags")),
        expected_baseline_failures=_coerce_string_tuple(
            raw_manifest.get("expectedBaselineFailures")
        ),
    )


def evaluate_golden_scenario(scenario: GoldenScenario) -> EvaluatedGoldenScenario:
    report = _load_json_object(scenario.report_path)
    summary = build_phase0_eval_summary(report)
    if summary.scenario_id != scenario.id:
        raise ValueError(
            f"Golden scenario report id '{summary.scenario_id}' does not match '{scenario.id}'."
        )

    missing_expected_failures = tuple(
        expected_failure
        for expected_failure in scenario.expected_baseline_failures
        if expected_failure not in summary.baseline_failures
    )
    unexpected_failures = tuple(
        failure
        for failure in summary.baseline_failures
        if failure not in scenario.expected_baseline_failures
    )
    return EvaluatedGoldenScenario(
        scenario=scenario,
        summary=summary,
        missing_expected_failures=missing_expected_failures,
        unexpected_failures=unexpected_failures,
    )


def run_foundation_eval_harness(scenarios_dir: Path | None = None) -> EvalHarnessRun:
    scenarios = tuple(
        evaluate_golden_scenario(scenario)
        for scenario in discover_golden_scenarios(scenarios_dir)
    )
    return EvalHarnessRun(scenarios=scenarios)


def _load_json_object(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return raw


def _coerce_string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if isinstance(item, str))


# ---------------------------------------------------------------------------
# Journey Scenario support (P15)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class JourneyScenario:
    scenario_id: str
    description: str
    input: str
    stage: str
    expected_fields: tuple[str, ...]
    forbidden_patterns: tuple[str, ...]


@dataclass(frozen=True)
class JourneyScenarioResult:
    scenario: JourneyScenario
    passed: bool
    missing_fields: tuple[str, ...]
    forbidden_pattern_matches: tuple[str, ...]

    @property
    def failure_reasons(self) -> list[str]:
        reasons: list[str] = []
        if self.missing_fields:
            reasons.append(f"Missing expected fields: {', '.join(self.missing_fields)}")
        if self.forbidden_pattern_matches:
            reasons.append(
                f"Forbidden patterns found: {', '.join(self.forbidden_pattern_matches)}"
            )
        return reasons


@dataclass(frozen=True)
class JourneyEvalRun:
    results: tuple[JourneyScenarioResult, ...]

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)


def discover_journey_scenarios(scenarios_dir: Path | None = None) -> list[JourneyScenario]:
    """Discover YAML journey scenarios from the golden_scenarios directory."""
    root = scenarios_dir or _GOLDEN_SCENARIOS_DIR
    yaml_files = sorted(root.glob("journey-*.yaml"))
    return [load_journey_scenario(yaml_file) for yaml_file in yaml_files]


def load_journey_scenario(yaml_path: Path) -> JourneyScenario:
    """Load a journey scenario from a YAML file."""
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Expected a YAML object in {yaml_path}")

    scenario_id = str(raw.get("scenario_id") or "").strip()
    if not scenario_id:
        raise ValueError(f"journey scenario_id is required: {yaml_path}")

    return JourneyScenario(
        scenario_id=scenario_id,
        description=str(raw.get("description") or "").strip(),
        input=str(raw.get("input") or "").strip(),
        stage=str(raw.get("stage") or "").strip(),
        expected_fields=_coerce_string_tuple(raw.get("expected_fields")),
        forbidden_patterns=_coerce_string_tuple(raw.get("forbidden_patterns")),
    )


def validate_journey_response(
    response: dict[str, Any],
    scenario: JourneyScenario,
    response_text: str = "",
) -> JourneyScenarioResult:
    """Validate a workflow response dict against a journey scenario.

    Checks expected_fields (dot-path lookup) and forbidden_patterns (regex on text).
    """
    import re as _re

    missing_fields: list[str] = []
    for field_path in scenario.expected_fields:
        if not _check_field_path(response, field_path):
            missing_fields.append(field_path)

    text_to_check = response_text or json.dumps(response)
    forbidden_matches: list[str] = []
    for pattern in scenario.forbidden_patterns:
        try:
            if _re.search(pattern, text_to_check):
                forbidden_matches.append(pattern)
        except _re.error:
            pass

    passed = not missing_fields and not forbidden_matches
    return JourneyScenarioResult(
        scenario=scenario,
        passed=passed,
        missing_fields=tuple(missing_fields),
        forbidden_pattern_matches=tuple(forbidden_matches),
    )


def _check_field_path(obj: Any, path: str) -> bool:
    """Check if a dot-path field exists and is non-empty in an object."""
    parts = path.split(".")
    current = obj
    for part in parts:
        if "[" in part:
            key = part[: part.index("[")]
            if not isinstance(current, dict) or key not in current:
                return False
            arr = current[key]
            if not isinstance(arr, list) or len(arr) == 0:
                return False
            current = arr[0]
        else:
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
    return current is not None and current != "" and current != [] and current != {}


def run_journey_eval_harness(
    scenarios_dir: Path | None = None,
    responses: dict[str, dict[str, Any]] | None = None,
    response_texts: dict[str, str] | None = None,
) -> JourneyEvalRun:
    """Run the journey eval harness against a set of responses.

    responses: mapping from scenario_id to response dict (optional, uses empty dict if missing)
    response_texts: mapping from scenario_id to response text (optional)
    """
    scenarios = discover_journey_scenarios(scenarios_dir)
    results = tuple(
        validate_journey_response(
            response=(responses or {}).get(scenario.scenario_id, {}),
            scenario=scenario,
            response_text=(response_texts or {}).get(scenario.scenario_id, ""),
        )
        for scenario in scenarios
    )
    return JourneyEvalRun(results=results)
