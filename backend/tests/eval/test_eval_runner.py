from __future__ import annotations

from . import eval_runner
from .reporting import ScenarioEvalSummary


def test_discover_golden_scenarios_loads_initial_manifest_set() -> None:
    scenarios = eval_runner.discover_golden_scenarios()

    assert [scenario.id for scenario in scenarios] == [
        "scenario-behavior",
        "scenario-clarify-guardrails",
        "scenario-delivery-guardrails",
    ]
    assert all(scenario.report_path.exists() for scenario in scenarios)
    assert all(scenario.expected_baseline_failures for scenario in scenarios)


def test_evaluate_golden_scenario_reuses_reporting_layer(monkeypatch) -> None:
    scenario = eval_runner.discover_golden_scenarios()[0]
    sentinel = ScenarioEvalSummary(
        scenario_id=scenario.id,
        scenario_name=scenario.name,
        turns=[],
        dimension_averages={},
        overall_score=1.0,
    )

    called_with: list[dict[str, object]] = []

    def fake_build_phase0_eval_summary(report: dict[str, object]) -> ScenarioEvalSummary:
        called_with.append(report)
        return sentinel

    monkeypatch.setattr(eval_runner, "build_phase0_eval_summary", fake_build_phase0_eval_summary)

    result = eval_runner.evaluate_golden_scenario(scenario)

    assert result.summary is sentinel
    assert len(called_with) == 1
    assert result.missing_expected_failures == scenario.expected_baseline_failures
    assert result.unexpected_failures == ()


def test_run_foundation_eval_harness_matches_expected_baselines() -> None:
    run = eval_runner.run_foundation_eval_harness()

    assert run.scenario_count == 3
    assert run.mismatched_scenario_count == 0
    assert [evaluation.scenario.id for evaluation in run.scenarios] == [
        "scenario-behavior",
        "scenario-clarify-guardrails",
        "scenario-delivery-guardrails",
    ]
    assert run.average_overall_score >= 2.0

    delivery = next(
        evaluation
        for evaluation in run.scenarios
        if evaluation.scenario.id == "scenario-delivery-guardrails"
    )
    assert delivery.summary.overall_score >= 3.0
    assert "Candidate payload latest candidate missing citations." in delivery.summary.baseline_failures
    assert "IaC payload missing validation evidence." in delivery.summary.baseline_failures
