from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path


def _import_runner_module():
    repo_root = Path(__file__).resolve().parents[2]
    scripts_e2e = repo_root / "scripts" / "e2e"
    sys.path.insert(0, str(scripts_e2e))
    try:
        return importlib.import_module("aaa_e2e_runner")
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


def test_export_payload_summary_tracks_traceability_and_scorecard_coverage() -> None:
    runner = _import_runner_module()

    answer = (
        "Exported AAA state to proj-1-aaa-export.json at 2026-01-01T00:00:00+00:00.\n\n"
        "AAA_EXPORT\n"
        "```json\n"
        f"{json.dumps(_build_export_payload(), indent=2)}\n"
        "```"
    )

    summary = runner._summarize_export_payload(answer)

    assert summary == {
        "present": True,
        "topLevelKeys": ["exportedAt", "mindmapCoverageScorecard", "state"],
        "missingRequiredKeys": [],
        "stateMissingRequiredKeys": [],
        "stateSummary": {
            "counts": {"requirements": 1, "traceabilityLinks": 1},
            "keys": ["mindMapCoverage", "requirements", "traceabilityLinks"],
            "mindMapCoverage": {
                "statusCounts": {"addressed": 13},
                "topicCount": 13,
            },
        },
        "mindmapCoverageScorecard": {
            "missingTopicKeys": [],
            "summary": {"addressed": 13, "notAddressed": 0, "partial": 0},
            "topicCount": 13,
        },
    }


def test_export_payload_summary_flags_missing_required_export_sections() -> None:
    runner = _import_runner_module()

    answer = (
        "AAA_EXPORT\n"
        "```json\n"
        "{\"exportedAt\":\"2026-01-01T00:00:00+00:00\",\"state\":{\"requirements\":[]}}\n"
        "```"
    )

    summary = runner._summarize_export_payload(answer)

    assert summary["present"] is True
    assert summary["missingRequiredKeys"] == ["mindmapCoverageScorecard"]
    assert summary["stateMissingRequiredKeys"] == ["traceabilityLinks", "mindMapCoverage"]
    assert summary["mindmapCoverageScorecard"]["topicCount"] == 0
    assert len(summary["mindmapCoverageScorecard"]["missingTopicKeys"]) == 13


def _build_export_payload() -> dict[str, object]:
    topic_keys = _required_topic_keys()
    coverage_topics = {
        key: {"status": "addressed", "confidence": 1.0}
        for key in topic_keys
    }
    return {
        "exportedAt": "2026-01-01T00:00:00+00:00",
        "state": {
            "requirements": [{"id": "req-1"}],
            "traceabilityLinks": [{"id": "trace-1"}],
            "mindMapCoverage": {
                "version": "1",
                "computedAt": "2026-01-01T00:00:00+00:00",
                "topics": coverage_topics,
            },
        },
        "mindmapCoverageScorecard": {
            "version": "1",
            "generatedAt": "2026-01-01T00:00:00+00:00",
            "summary": {"addressed": 13, "partial": 0, "notAddressed": 0},
            "topics": {
                key: {
                    "label": key,
                    "status": "addressed",
                    "confidence": 1.0,
                    "evidence": [],
                }
                for key in topic_keys
            },
        },
    }


def _required_topic_keys() -> list[str]:
    runner = _import_runner_module()
    mindmap_loader = (
        Path(runner.__file__).resolve().parents[2]
        / "backend"
        / "app"
        / "agents_system"
        / "services"
        / "mindmap_loader.py"
    )
    with mindmap_loader.open(encoding="utf-8") as handle:
        content = handle.read()
    match = re.search(
        r"REQUIRED_TOP_LEVEL_TOPIC_KEYS:\s*tuple\[str,\s*\.\.\.\]\s*=\s*\((?P<body>.*?)\)\n\n",
        content,
        re.DOTALL,
    )
    assert match is not None
    return re.findall(r'"([^"]+)"', match.group("body"))
