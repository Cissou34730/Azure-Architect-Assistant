from __future__ import annotations

from app.agents_system.services.waf_evaluator import WAFEvaluatorService


def test_waf_evaluator_scores_fixed_in_progress_and_open_items() -> None:
    service = WAFEvaluatorService()

    result = service.evaluate(
        {
            "current_project_state": {
                "requirements": [
                    {
                        "text": "Encrypt sensitive data with customer-managed keys and protect data at rest.",
                    },
                    {
                        "text": "Deploy the workload across multiple availability zones with failover support.",
                    },
                ],
                "assumptions": [
                    "Autoscaling is enabled for the main compute tier.",
                ],
                "wafChecklist": {
                    "items": [
                        {
                            "id": "sec-1",
                            "pillar": "Security",
                            "topic": "Encrypt sensitive data at rest",
                            "description": "Use key management and encryption controls",
                        },
                        {
                            "id": "rel-1",
                            "pillar": "Reliability",
                            "topic": "Use availability zones for resilience",
                            "description": "Deploy across multiple zones with failover",
                        },
                        {
                            "id": "cost-1",
                            "pillar": "Cost Optimization",
                            "topic": "Right size compute resources",
                            "description": "Use autoscaling and monitor utilization",
                        },
                        {
                            "id": "ops-1",
                            "pillar": "Operational Excellence",
                            "topic": "Maintain golden image baselines",
                            "description": "Track image drift detection cadence",
                        },
                    ]
                },
            }
        }
    )

    items_by_id = {item["itemId"]: item for item in result["items"]}

    assert items_by_id["sec-1"]["status"] == "fixed"
    assert items_by_id["rel-1"]["status"] == "fixed"
    assert items_by_id["cost-1"]["status"] == "in_progress"
    assert items_by_id["ops-1"]["status"] == "open"
    assert "requirements[0].text" in items_by_id["sec-1"]["matchedSourcePaths"]
    assert "assumptions[0]" in items_by_id["cost-1"]["matchedSourcePaths"]

    assert result["summary"] == {
        "evaluatedItems": 4,
        "itemsByStatus": {
            "fixed": 2,
            "in_progress": 1,
            "open": 1,
        },
        "pillars": {
            "Cost Optimization": {"fixed": 0, "in_progress": 1, "open": 0},
            "Operational Excellence": {"fixed": 0, "in_progress": 0, "open": 1},
            "Reliability": {"fixed": 1, "in_progress": 0, "open": 0},
            "Security": {"fixed": 1, "in_progress": 0, "open": 0},
        },
        "sourceCount": 3,
    }


def test_waf_evaluator_is_deterministic_for_same_input() -> None:
    service = WAFEvaluatorService()
    state = {
        "wafChecklist": {
            "items": [
                {
                    "id": "sec-1",
                    "pillar": "Security",
                    "topic": "Protect secrets with managed identity",
                    "description": "Avoid shared credentials and rotate secrets",
                }
            ]
        },
        "candidateArchitectures": [
            {
                "services": [
                    "Managed identity",
                    "Key Vault",
                ],
                "notes": "Avoid shared credentials by using managed identity and Key Vault.",
            }
        ],
    }

    first = service.evaluate(state)
    second = service.evaluate(state)

    assert first == second


def test_waf_evaluator_supports_mapping_style_checklist_items() -> None:
    service = WAFEvaluatorService()

    result = service.evaluate(
        {
            "wafChecklist": {
                "items": {
                    "b": {
                        "id": "b",
                        "pillar": "Security",
                        "title": "Use private endpoints",
                        "description": "Private network connectivity only",
                    },
                    "a": {
                        "id": "a",
                        "pillar": "Reliability",
                        "title": "Use health probes",
                        "description": "Detect unhealthy instances quickly",
                    },
                }
            },
            "applicationStructure": {
                "networking": "Private endpoints are used for all data services.",
            },
        }
    )

    assert [item["itemId"] for item in result["items"]] == ["a", "b"]
    assert result["items"][1]["status"] == "in_progress"


def test_waf_evaluator_marks_short_controls_fixed_on_full_match() -> None:
    service = WAFEvaluatorService()

    result = service.evaluate(
        {
            "wafChecklist": {
                "items": [
                    {
                        "id": "sec-rbac",
                        "pillar": "Security",
                        "topic": "Use Azure RBAC",
                    }
                ]
            },
            "candidateArchitectures": [
                {"notes": "Azure RBAC is used for all platform access control."}
            ],
        }
    )

    assert result["items"][0]["status"] == "fixed"
    assert result["items"][0]["coverageScore"] == 1.0


def test_waf_evaluator_uses_adr_and_reference_document_evidence() -> None:
    service = WAFEvaluatorService()

    result = service.evaluate(
        {
            "wafChecklist": {
                "items": [
                    {
                        "id": "net-1",
                        "pillar": "Security",
                        "topic": "Use private endpoints",
                    }
                ]
            },
            "adrs": [
                {"decision": "Use private endpoints for all data plane connectivity."}
            ],
            "referenceDocuments": [
                {"title": "Private endpoints are mandatory for storage and databases."}
            ],
        }
    )

    assert result["summary"]["sourceCount"] == 2
    assert result["items"][0]["status"] == "fixed"
    assert "adrs[0].decision" in result["items"][0]["matchedSourcePaths"]
    assert "referenceDocuments[0].title" in result["items"][0]["matchedSourcePaths"]


def test_waf_evaluator_returns_empty_summary_when_no_checklist_exists() -> None:
    service = WAFEvaluatorService()

    result = service.evaluate({"requirements": [{"text": "Support SSO"}]})

    assert result == {
        "items": [],
        "summary": {
            "evaluatedItems": 0,
            "itemsByStatus": {"fixed": 0, "in_progress": 0, "open": 0},
            "pillars": {},
            "sourceCount": 1,
        },
    }
