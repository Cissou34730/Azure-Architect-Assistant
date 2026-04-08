from .reporting import EvalDimension, build_phase0_eval_summary


def test_build_phase0_eval_summary_scores_existing_runner_report_shape() -> None:
    report = {
        "scenario": {"id": "scenario-a", "name": "Scenario A"},
        "final": {
            "missingRequiredKeys": [],
            "stateSummary": {
                "keys": ["requirements", "adrs", "wafChecklist"],
                "counts": {"requirements": 4, "adrs": 1},
            },
        },
        "dbPersistence": {"status": "PASS"},
        "steps": [
            {
                "id": "us2-adr",
                "request": "Create an ADR with architecture trade-offs and WAF guidance.",
                "answer": (
                    "## Recommended architecture\n\n"
                    "- Use Azure App Service and Azure SQL.\n"
                    "- Capture the ADR decision with trade-offs and WAF guidance.\n"
                    "- Cite Microsoft Learn guidance for operational choices."
                ),
                "success": True,
                "error": None,
                "mcpCallCount": 1,
                "pricingCallCount": 0,
                "kbCallCount": 2,
                "advisoryQuality": {
                    "proactivity": 2,
                    "correction": 1,
                    "evidence": 2,
                    "clarity": 2,
                    "total": 7,
                },
            }
        ],
    }

    summary = build_phase0_eval_summary(report)

    assert summary.scenario_id == "scenario-a"
    assert summary.scenario_name == "Scenario A"
    assert summary.missing_required_keys == []
    assert len(summary.turns) == 1
    assert summary.overall_score >= 3.0
    assert summary.dimension_averages[EvalDimension.TOOL_USAGE] >= 4.0
    assert summary.dimension_averages[EvalDimension.STRUCTURE] == 5.0
    assert summary.dimension_averages[EvalDimension.CITATION_GROUNDING] == 5.0
    assert summary.baseline_failures == []


def test_build_phase0_eval_summary_flags_missing_keys_and_failed_persistence() -> None:
    report = {
        "scenario": {"id": "scenario-c", "name": "Scenario C"},
        "final": {
            "missingRequiredKeys": ["wafChecklist", "traceabilityLinks"],
            "stateSummary": {
                "keys": ["requirements"],
                "counts": {"requirements": 1},
            },
        },
        "dbPersistence": {"status": "FAIL"},
        "steps": [
            {
                "id": "us4-validate",
                "request": "Run a WAF validation and persist the result.",
                "answer": "Validation completed.",
                "success": False,
                "error": "tool failure",
                "mcpCallCount": 0,
                "pricingCallCount": 0,
                "kbCallCount": 0,
                "advisoryQuality": {
                    "proactivity": 0,
                    "correction": 0,
                    "evidence": 0,
                    "clarity": 0,
                    "total": 0,
                },
            }
        ],
    }

    summary = build_phase0_eval_summary(report)

    turn = summary.turns[0]

    assert turn.score_for(EvalDimension.PERSISTENCE) == 1
    assert turn.score_for(EvalDimension.TOOL_USAGE) == 1
    assert turn.score_for(EvalDimension.COMPLETENESS) == 1
    assert "Missing required keys: wafChecklist, traceabilityLinks" in summary.baseline_failures
    assert "Database persistence assertions failed." in summary.baseline_failures


def test_build_phase0_eval_summary_uses_request_overlap_for_specificity() -> None:
    report = {
        "scenario": {"id": "scenario-b", "name": "Scenario B"},
        "final": {
            "missingRequiredKeys": [],
            "stateSummary": {"keys": ["candidateArchitectures"], "counts": {}},
        },
        "dbPersistence": {"status": "PASS"},
        "steps": [
            {
                "id": "us2-candidate",
                "request": "Design a multi-region architecture with private endpoints and failover.",
                "answer": (
                    "The multi-region architecture uses private endpoints for data plane access "
                    "and failover between paired regions."
                ),
                "success": True,
                "error": None,
                "mcpCallCount": 0,
                "pricingCallCount": 0,
                "kbCallCount": 1,
                "advisoryQuality": {
                    "proactivity": 1,
                    "correction": 1,
                    "evidence": 0,
                    "clarity": 1,
                    "total": 3,
                },
            }
        ],
    }

    summary = build_phase0_eval_summary(report)

    assert summary.turns[0].score_for(EvalDimension.SPECIFICITY) >= 4


def test_build_phase0_eval_summary_flags_export_payload_regressions() -> None:
    report = {
        "scenario": {"id": "scenario-export", "name": "Scenario Export"},
        "final": {
            "missingRequiredKeys": [],
            "stateSummary": {
                "keys": ["requirements", "traceabilityLinks"],
                "counts": {"requirements": 2, "traceabilityLinks": 1},
            },
            "exportPayload": {
                "present": True,
                "missingRequiredKeys": ["mindmapCoverageScorecard"],
                "stateMissingRequiredKeys": ["mindMapCoverage"],
                "mindmapCoverageScorecard": {
                    "topicCount": 12,
                    "missingTopicKeys": ["13_learning_and_practice"],
                    "summary": {"addressed": 12, "partial": 0, "notAddressed": 1},
                },
            },
        },
        "dbPersistence": {"status": "PASS"},
        "steps": [
            {
                "id": "us6-export",
                "request": "Export traceability and mind map coverage.",
                "answer": "AAA_EXPORT payload emitted.",
                "success": True,
                "error": None,
                "mcpCallCount": 0,
                "pricingCallCount": 0,
                "kbCallCount": 0,
                "advisoryQuality": {
                    "proactivity": 1,
                    "correction": 0,
                    "evidence": 1,
                    "clarity": 1,
                    "total": 3,
                },
            }
        ],
    }

    summary = build_phase0_eval_summary(report)

    assert (
        "Export payload missing required keys: mindmapCoverageScorecard"
        in summary.baseline_failures
    )
    assert (
        "Export payload state missing required keys: mindMapCoverage"
        in summary.baseline_failures
    )
    assert (
        "Export payload mind map scorecard does not cover all 13 topics."
        in summary.baseline_failures
    )
