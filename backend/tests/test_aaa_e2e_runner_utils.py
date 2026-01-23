from __future__ import annotations

import sys
from pathlib import Path


def _import_runner_module():
    repo_root = Path(__file__).resolve().parents[2]
    scripts_e2e = repo_root / "scripts" / "e2e"
    sys.path.insert(0, str(scripts_e2e))
    try:
        import aaa_e2e_runner  # type: ignore

        return aaa_e2e_runner
    finally:
        sys.path.pop(0)


def test_scenarios_load_and_validate() -> None:
    runner = _import_runner_module()

    for scenario_id in ["scenario-a", "scenario-b", "scenario-c"]:
        scenario = runner.load_scenario(scenario_id)
        assert scenario.id == scenario_id
        assert scenario.project_name
        assert scenario.documents
        assert scenario.chat_turns


def test_report_normalization_drops_high_variance_fields() -> None:
    runner = _import_runner_module()

    report = {
        "runId": "20260101_000000",
        "generatedAt": "2026-01-01T00:00:00Z",
        "projectId": "p1",
        "steps": [
            {
                "id": "t1",
                "answer": "long text",
                "answerHash": "deadbeef",
                "durationMs": 123,
                "mcpLogs": [{"x": 1}],
                "pricingLogs": [{"y": 2}],
                "success": True,
            }
        ],
        "final": {"missingRequiredKeys": []},
    }

    normalized = runner.normalize_report_for_golden(report)
    assert "runId" not in normalized
    assert "generatedAt" not in normalized
    assert "projectId" not in normalized

    step = normalized["steps"][0]
    assert "answer" not in step
    assert "answerHash" not in step
    assert "durationMs" not in step
    assert "mcpLogs" not in step
    assert "pricingLogs" not in step
    assert step["success"] is True
