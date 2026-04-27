from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

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


# ---------------------------------------------------------------------------
# P15: Journey Scenario tests
# ---------------------------------------------------------------------------


def test_discover_journey_scenarios_loads_yaml_files() -> None:
    scenarios = eval_runner.discover_journey_scenarios()

    assert len(scenarios) == 5
    ids = [s.scenario_id for s in scenarios]
    assert "journey-clarify-vague-request" in ids
    assert "journey-propose-candidate" in ids
    assert "journey-cost-estimation" in ids
    assert "journey-quality-gate-retry" in ids
    assert "journey-compliance-workload" in ids
    assert all(s.stage for s in scenarios)
    assert all(s.expected_fields for s in scenarios)


def test_validate_journey_response_passes_on_valid_response() -> None:
    scenario = eval_runner.JourneyScenario(
        scenario_id="test-pass",
        description="Test pass scenario",
        input="Test input",
        stage="clarify",
        expected_fields=("stage", "nextStep"),
        forbidden_patterns=("(?i)recorded successfully",),
    )
    response = {
        "stage": "clarify",
        "nextStep": {"stage": "clarify", "rationale": "Answer questions", "blockingQuestions": []},
    }
    result = eval_runner.validate_journey_response(response=response, scenario=scenario)

    assert result.passed is True
    assert result.missing_fields == ()
    assert result.forbidden_pattern_matches == ()
    assert result.failure_reasons == []


def test_validate_journey_response_fails_on_missing_fields() -> None:
    scenario = eval_runner.JourneyScenario(
        scenario_id="test-missing",
        description="Test missing fields",
        input="Test input",
        stage="propose_candidate",
        expected_fields=("stage", "summary", "reasoningSummary"),
        forbidden_patterns=(),
    )
    response = {"stage": "propose_candidate"}

    result = eval_runner.validate_journey_response(response=response, scenario=scenario)

    assert result.passed is False
    assert "summary" in result.missing_fields
    assert "reasoningSummary" in result.missing_fields
    assert len(result.failure_reasons) >= 1


def test_validate_journey_response_fails_on_forbidden_pattern() -> None:
    scenario = eval_runner.JourneyScenario(
        scenario_id="test-forbidden",
        description="Test forbidden pattern",
        input="Test input",
        stage="propose_candidate",
        expected_fields=("stage",),
        forbidden_patterns=("(?i)recorded successfully",),
    )
    response = {"stage": "propose_candidate"}
    response_text = "I've created a change set. Recorded successfully."

    result = eval_runner.validate_journey_response(
        response=response, scenario=scenario, response_text=response_text
    )

    assert result.passed is False
    assert "(?i)recorded successfully" in result.forbidden_pattern_matches


def test_run_journey_eval_harness_produces_correct_counts() -> None:
    """Harness with all valid responses should report all passed.
    Harness with empty responses reports all failed (missing expected fields).
    """
    scenarios = eval_runner.discover_journey_scenarios()
    first = scenarios[0]

    # Build a valid nested response for the first scenario
    # (journey-clarify-vague-request has dot-path fields like structuredPayload.type)
    valid_response: dict[str, Any] = {
        "stage": "clarify",
        "nextStep": {"stage": "clarify", "rationale": "Answer questions", "blockingQuestions": []},
        "structuredPayload": {
            "type": "clarification_questions",
            "questions": [{"id": "q-1", "text": "What is your workload?"}],
        },
    }
    valid_responses = {first.scenario_id: valid_response}

    run_empty = eval_runner.run_journey_eval_harness(responses={})
    assert run_empty.failed_count == len(scenarios)
    assert run_empty.passed_count == 0
    assert not run_empty.all_passed

    run_one = eval_runner.run_journey_eval_harness(responses=valid_responses)
    first_result = next(r for r in run_one.results if r.scenario.scenario_id == first.scenario_id)
    assert first_result.passed is True

