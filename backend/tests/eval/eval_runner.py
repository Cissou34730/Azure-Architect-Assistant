from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .journey_scenarios import (
    JourneyEvalRun,
    JourneyExecutor,
    JourneyScenario,
    JourneyScenarioResult,
    QualityAssertions,
    ThinReceiptRule,
    discover_journey_scenarios as _discover_journey_scenarios,
    load_journey_scenario,
    run_journey_eval_harness as _run_journey_eval_harness,
    run_live_journey_eval_harness as _run_live_journey_eval_harness,
    validate_journey_response,
)
from .reporting import ScenarioEvalSummary, build_phase0_eval_summary

_GOLDEN_SCENARIOS_DIR = Path(__file__).resolve().parent / "golden_scenarios"


@dataclass(frozen=True)
class GoldenScenario:
    id: str
    name: str
    description: str
    report_path: Path
    tags: tuple[str, ...] = ()
    minimum_overall_score: float = 4.0


@dataclass(frozen=True)
class EvaluatedGoldenScenario:
    scenario: GoldenScenario
    summary: ScenarioEvalSummary
    quality_failures: tuple[str, ...] = ()
    below_minimum_score: bool = False

    @property
    def matches_expected_failures(self) -> bool:
        """Compatibility name: healthy baselines now require no expected failures."""
        return not self.quality_failures and not self.below_minimum_score


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

    @property
    def all_passed(self) -> bool:
        return bool(self.scenarios) and all(
            scenario.matches_expected_failures for scenario in self.scenarios
        )


class _GoldenScenarioManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    minimum_overall_score: float = Field(
        default=4.0,
        ge=1.0,
        le=5.0,
        alias="minimumOverallScore",
    )


def discover_golden_scenarios(scenarios_dir: Path | None = None) -> list[GoldenScenario]:
    root = scenarios_dir or _GOLDEN_SCENARIOS_DIR
    manifests = sorted(root.glob("*/scenario.json"))
    return [load_golden_scenario(manifest_path) for manifest_path in manifests]


def load_golden_scenario(manifest_path: Path) -> GoldenScenario:
    raw_manifest = _load_json_object(manifest_path)
    try:
        manifest = _GoldenScenarioManifest.model_validate(raw_manifest)
    except ValidationError as exc:
        raise ValueError(f"Invalid golden scenario {manifest_path}: {exc}") from exc
    report_path = manifest_path.with_name("report.normalized.json")
    if not report_path.exists():
        raise FileNotFoundError(f"Golden scenario report not found: {report_path}")

    return GoldenScenario(
        id=manifest.id,
        name=manifest.name,
        description=manifest.description,
        report_path=report_path,
        tags=tuple(manifest.tags),
        minimum_overall_score=manifest.minimum_overall_score,
    )


def evaluate_golden_scenario(scenario: GoldenScenario) -> EvaluatedGoldenScenario:
    report = _load_json_object(scenario.report_path)
    summary = build_phase0_eval_summary(report)
    if summary.scenario_id != scenario.id:
        raise ValueError(
            f"Golden scenario report id '{summary.scenario_id}' does not match '{scenario.id}'."
        )

    return EvaluatedGoldenScenario(
        scenario=scenario,
        summary=summary,
        quality_failures=tuple(summary.baseline_failures),
        below_minimum_score=summary.overall_score < scenario.minimum_overall_score,
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


def discover_journey_scenarios(scenarios_dir: Path | None = None) -> list[JourneyScenario]:
    return _discover_journey_scenarios(scenarios_dir or _GOLDEN_SCENARIOS_DIR)


def run_journey_eval_harness(
    scenarios_dir: Path | None = None,
    responses: dict[str, dict[str, Any]] | None = None,
    response_texts: dict[str, str] | None = None,
) -> JourneyEvalRun:
    return _run_journey_eval_harness(
        root=scenarios_dir or _GOLDEN_SCENARIOS_DIR,
        responses=responses,
        response_texts=response_texts,
    )


async def run_live_journey_eval_harness(
    executor: JourneyExecutor,
    scenarios_dir: Path | None = None,
) -> JourneyEvalRun:
    return await _run_live_journey_eval_harness(
        executor,
        root=scenarios_dir or _GOLDEN_SCENARIOS_DIR,
    )
