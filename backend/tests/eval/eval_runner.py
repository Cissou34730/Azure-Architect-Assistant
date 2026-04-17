from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Any

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
