
import pytest
from pydantic import ValidationError

from app.agents_system.services.aaa_state_models import AAAProjectState
from app.agents_system.services.state_update_parser import extract_state_updates
from app.agents_system.tools.aaa_validation_tool import AAARunValidationTool


def test_validation_tool_emits_state_update_block_parseable() -> None:
    tool = AAARunValidationTool()

    response = tool._run(
        findings=[
            {
                "title": "Missing private networking",
                "severity": "high",
                "description": "Service endpoints are public with no private access path.",
                "remediation": "Add Private Link and restrict public network access.",
                "wafPillar": "security",
                "wafTopic": "Network security",
                "relatedRequirementIds": ["NFR-SEC-001"],
                "sourceCitations": [
                    {
                        "id": "c1",
                        "kind": "referenceDocument",
                        "referenceDocumentId": "doc-1",
                        "note": "Security baseline",
                    }
                ],
            }
        ],
        wafEvaluations=[
            {
                "itemId": "waf-sec-001",
                "pillar": "security",
                "topic": "Network security",
                "status": "open",
                "evidence": "No Private Link configured.",
                "relatedFindingIds": [],
                "sourceCitations": [
                    {
                        "id": "c2",
                        "kind": "mcp",
                        "url": "https://learn.microsoft.com/",
                        "note": "Private Link guidance",
                    }
                ],
            }
        ],
    )

    updates = extract_state_updates(response, user_message="", current_state={})
    assert updates is not None
    assert "findings" in updates
    assert "wafChecklist" in updates


def test_project_state_validates_findings_and_waf_evaluations() -> None:
    payload = {
        "findings": [
            {
                "id": "f-1",
                "title": "Missing private networking",
                "severity": "high",
                "description": "Public endpoints only.",
                "remediation": "Use Private Link.",
                "sourceCitations": [
                    {
                        "id": "c1",
                        "kind": "referenceDocument",
                        "referenceDocumentId": "doc-1",
                    }
                ],
            }
        ],
        "wafChecklist": {
            "version": "1",
            "pillars": ["security"],
            "items": [
                {
                    "id": "waf-sec-001",
                    "pillar": "security",
                    "topic": "Network security",
                    "evaluations": [
                        {
                            "id": "e-1",
                            "status": "open",
                            "evidence": "No Private Link configured.",
                            "relatedFindingIds": ["f-1"],
                            "sourceCitations": [],
                        }
                    ],
                }
            ],
        },
    }

    validated = AAAProjectState.model_validate(payload)
    assert validated.findings[0].severity == "high"
    dumped = validated.model_dump(mode="json", by_alias=True)
    assert dumped["wafChecklist"]["items"][0]["evaluations"][0]["status"] == "open"


def test_finding_requires_citation() -> None:
    payload = {
        "findings": [
            {
                "id": "f-1",
                "title": "Bad",
                "severity": "low",
                "description": "d",
                "remediation": "r",
                "sourceCitations": [],
            }
        ]
    }

    with pytest.raises(ValidationError):
        AAAProjectState.model_validate(payload)


def test_validation_tool_preserves_worker_supplied_finding_shape_and_links() -> None:
    tool = AAARunValidationTool()

    response = tool._run(
        findings=[
            {
                "id": "finding-sec-waf-1",
                "title": "Missing WAF on public ingress",
                "severity": "critical",
                "description": "The public endpoint is exposed without an upstream WAF control.",
                "remediation": "Add Front Door WAF or Application Gateway WAF.",
                "impactedComponents": ["App Service", "Public endpoint"],
                "wafPillar": "Security",
                "wafTopic": "Protect public entry points with a web application firewall",
                "wafChecklistItemId": "sec-waf-1",
                "sourceCitations": [
                    {
                        "id": "c1",
                        "kind": "referenceDocument",
                        "referenceDocumentId": "doc-1",
                        "url": "https://learn.microsoft.com/azure/well-architected/security/",
                    }
                ],
            }
        ],
        wafEvaluations=[
            {
                "itemId": "sec-waf-1",
                "pillar": "Security",
                "topic": "Protect public entry points with a web application firewall",
                "status": "open",
                "evidence": "Deterministic WAF evaluator marked this checklist item as open.",
                "relatedFindingIds": ["finding-sec-waf-1"],
                "sourceCitations": [
                    {
                        "id": "c1",
                        "kind": "referenceDocument",
                        "referenceDocumentId": "doc-1",
                        "url": "https://learn.microsoft.com/azure/well-architected/security/",
                    }
                ],
            }
        ],
    )

    updates = extract_state_updates(response, user_message="", current_state={})

    assert updates is not None
    assert updates["findings"][0]["id"] == "finding-sec-waf-1"
    assert updates["findings"][0]["impactedComponents"] == ["App Service", "Public endpoint"]
    assert updates["findings"][0]["wafChecklistItemId"] == "sec-waf-1"
    assert updates["wafChecklist"]["items"][0]["evaluations"][0]["relatedFindingIds"] == [
        "finding-sec-waf-1"
    ]

