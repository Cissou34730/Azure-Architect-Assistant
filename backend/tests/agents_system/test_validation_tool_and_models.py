
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
                "status": "notCovered",
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
                            "status": "notCovered",
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
    assert validated.wafChecklist.items[0].evaluations[0].status == "notCovered"


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

