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


def test_build_phase0_eval_summary_flags_cost_payload_regressions() -> None:
    report = {
        "scenario": {"id": "scenario-cost", "name": "Scenario Cost"},
        "final": {
            "missingRequiredKeys": [],
            "stateSummary": {
                "keys": ["requirements"],
                "counts": {"requirements": 1},
            },
            "costPayload": {
                "present": False,
                "missingRequiredKeys": ["costEstimates"],
                "stateSummary": {"keys": [], "counts": {}},
                "pricingLogCount": 0,
                "latestEstimate": None,
            },
        },
        "dbPersistence": {"status": "PASS"},
        "steps": [
            {
                "id": "us5-iac-cost",
                "request": "Generate IaC and provide a cost estimate with explicit assumptions.",
                "answer": "Baseline estimate unavailable.",
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

    assert "Cost payload missing required keys: costEstimates" in summary.baseline_failures
    assert "Cost payload missing pricing log evidence." in summary.baseline_failures


def test_build_phase0_eval_summary_flags_iac_payload_regressions() -> None:
    report = {
        "scenario": {"id": "scenario-iac", "name": "Scenario IaC"},
        "final": {
            "missingRequiredKeys": [],
            "stateSummary": {
                "keys": ["requirements"],
                "counts": {"requirements": 1},
            },
            "iacPayload": {
                "present": True,
                "missingRequiredKeys": [],
                "stateSummary": {"keys": ["iacArtifacts"], "counts": {"iacArtifacts": 1}},
                "latestArtifact": {
                    "id": "iac-1",
                    "fileCount": 0,
                    "formats": [],
                    "validationResultCount": 0,
                    "validationStatusCounts": {},
                },
            },
        },
        "dbPersistence": {"status": "PASS"},
        "steps": [
            {
                "id": "us5-iac",
                "request": "Generate Bicep IaC with validation results for the approved design.",
                "answer": "IaC artifact recorded without validation evidence.",
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

    assert "IaC payload latest artifact missing files." in summary.baseline_failures
    assert "IaC payload missing validation evidence." in summary.baseline_failures


def test_build_phase0_eval_summary_flags_clarify_payload_regressions() -> None:
    report = {
        "scenario": {"id": "scenario-clarify", "name": "Scenario Clarify"},
        "final": {
            "missingRequiredKeys": [],
            "stateSummary": {"keys": ["requirements"], "counts": {"requirements": 1}},
            "clarifyPayload": {
                "present": False,
                "missingRequiredKeys": ["questionGroups"],
                "themeCount": 0,
                "themes": [],
                "questionCount": 0,
                "whyItMattersCount": 0,
                "architecturalImpactCounts": {},
                "ungroupedQuestionCount": 1,
            },
        },
        "dbPersistence": {"status": "PASS"},
        "steps": [
            {
                "id": "us1-clarify",
                "request": "Ask the key clarification questions before designing the architecture.",
                "answer": "Need more information.",
                "success": True,
                "error": None,
                "mcpCallCount": 0,
                "pricingCallCount": 0,
                "kbCallCount": 0,
                "advisoryQuality": {
                    "proactivity": 1,
                    "correction": 0,
                    "evidence": 0,
                    "clarity": 0,
                    "total": 1,
                },
            }
        ],
    }

    summary = build_phase0_eval_summary(report)

    assert "Clarify payload missing required keys: questionGroups" in summary.baseline_failures
    assert "Clarify payload did not produce any questions." in summary.baseline_failures
    assert "Clarify payload left one or more questions outside a named theme." in summary.baseline_failures


def test_build_phase0_eval_summary_flags_candidate_payload_regressions() -> None:
    report = {
        "scenario": {"id": "scenario-candidate", "name": "Scenario Candidate"},
        "final": {
            "missingRequiredKeys": [],
            "stateSummary": {
                "keys": ["candidateArchitectures"],
                "counts": {"candidateArchitectures": 1},
            },
            "candidatePayload": {
                "present": True,
                "missingRequiredKeys": [],
                "stateSummary": {
                    "keys": ["candidateArchitectures"],
                    "counts": {"candidateArchitectures": 1},
                },
                "latestCandidate": {
                    "id": "cand-1",
                    "title": "Target architecture",
                    "assumptionIdCount": 0,
                    "citationCount": 0,
                    "diagramIdCount": 0,
                },
            },
        },
        "dbPersistence": {"status": "PASS"},
        "steps": [
            {
                "id": "us2-candidate",
                "request": "Propose the target architecture candidate with diagrams and citations.",
                "answer": "Candidate recorded without the required evidence sections.",
                "success": True,
                "error": None,
                "mcpCallCount": 1,
                "pricingCallCount": 0,
                "kbCallCount": 0,
                "advisoryQuality": {
                    "proactivity": 1,
                    "correction": 0,
                    "evidence": 0,
                    "clarity": 1,
                    "total": 2,
                },
            }
        ],
    }

    summary = build_phase0_eval_summary(report)

    assert "Candidate payload latest candidate missing citations." in summary.baseline_failures
    assert "Candidate payload latest candidate missing diagram links." in summary.baseline_failures


def test_build_phase0_eval_summary_flags_adr_payload_regressions() -> None:
    report = {
        "scenario": {"id": "scenario-adr", "name": "Scenario ADR"},
        "final": {
            "missingRequiredKeys": [],
            "stateSummary": {"keys": ["pendingChangeSets"], "counts": {"pendingChangeSets": 1}},
            "adrPayload": {
                "present": True,
                "missingRequiredKeys": [],
                "pendingChangeSetCount": 1,
                "stateSummary": {
                    "keys": ["pendingChangeSets"],
                    "counts": {"pendingChangeSets": 1},
                },
                "latestChangeSet": {
                    "id": "cs-1",
                    "status": "applied",
                    "hasLifecycleCommand": False,
                    "lifecycleAction": None,
                    "artifactDraftCount": 0,
                    "adrDraftCount": 0,
                    "citationCount": 0,
                    "relatedRequirementIdCount": 0,
                    "missingDraftFields": ["decision", "sourceCitations"],
                },
            },
        },
        "dbPersistence": {"status": "PASS"},
        "steps": [
            {
                "id": "us3-adr",
                "request": "Create an ADR draft for the messaging decision.",
                "answer": "ADR draft recorded.",
                "success": True,
                "error": None,
                "mcpCallCount": 0,
                "pricingCallCount": 0,
                "kbCallCount": 1,
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

    assert "ADR payload latest change set is not pending." in summary.baseline_failures
    assert "ADR payload missing lifecycle command." in summary.baseline_failures
    assert "ADR payload missing ADR draft artifacts." in summary.baseline_failures
    assert (
        "ADR payload latest draft missing fields: decision, sourceCitations"
        in summary.baseline_failures
    )
