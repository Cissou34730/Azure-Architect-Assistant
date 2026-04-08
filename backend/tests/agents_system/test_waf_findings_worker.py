from __future__ import annotations

import json
from typing import Any

import pytest

from app.agents_system.services.waf_findings_worker import WAFFindingsWorker


class _PromptLoaderStub:
    def load_prompt(self, prompt_name: str, force_reload: bool = False) -> dict[str, str]:
        assert prompt_name == "waf_validator.yaml"
        return {"system_prompt": "Generate remediation-focused WAF findings as JSON."}


@pytest.mark.asyncio
async def test_waf_findings_worker_generates_findings_and_checklist_deltas() -> None:
    seen_prompts: list[tuple[str, str]] = []

    async def _generator(system_prompt: str, user_prompt: str) -> dict[str, Any]:
        seen_prompts.append((system_prompt, user_prompt))
        return {
            "findings": [
                {
                    "title": "Public ingress is missing a web application firewall",
                    "severity": "critical",
                    "description": "The workload exposes a public application endpoint without a WAF control.",
                    "remediation": "Add Azure Front Door WAF or Application Gateway WAF before production cutover.",
                    "impactedComponents": ["App Service", "Public endpoint"],
                    "wafPillar": "Security",
                    "wafTopic": "Protect public entry points with a web application firewall",
                    "wafChecklistItemId": "sec-waf-1",
                    "sourceCitations": [
                        {
                            "id": "cite-doc-1",
                            "kind": "referenceDocument",
                            "referenceDocumentId": "doc-1",
                            "url": "https://learn.microsoft.com/azure/well-architected/security/",
                            "note": "Security pillar guidance",
                        }
                    ],
                }
            ]
        }

    worker = WAFFindingsWorker(
        generator=_generator,
        prompt_loader=_PromptLoaderStub(),
        id_factory=lambda item_id: f"finding-{item_id}",
    )

    result = await worker.generate_findings(
        evaluator_result={
            "items": [
                {
                    "itemId": "sec-waf-1",
                    "pillar": "Security",
                    "topic": "Protect public entry points with a web application firewall",
                    "status": "open",
                    "coverageScore": 0.0,
                    "matchedSourcePaths": [
                        "candidateArchitectures[0].notes",
                        "referenceDocuments[0].title",
                    ],
                    "evidence": [
                        {
                            "sourcePath": "candidateArchitectures[0].notes",
                            "excerpt": "The architecture currently publishes traffic directly to App Service.",
                        }
                    ],
                }
            ],
            "summary": {"evaluatedItems": 1},
        },
        architecture_state={
            "candidateArchitectures": [
                {
                    "notes": "The architecture currently publishes traffic directly to App Service.",
                }
            ],
            "referenceDocuments": [
                {
                    "id": "doc-1",
                    "category": "guidance",
                    "title": "Azure WAF guidance",
                    "url": "https://learn.microsoft.com/azure/well-architected/security/",
                    "accessedAt": "2026-04-08T12:00:00+00:00",
                }
            ],
        },
    )

    assert seen_prompts
    assert "Protect public entry points with a web application firewall" in seen_prompts[0][1]
    assert result["findings"] == [
        {
            "id": "finding-sec-waf-1",
            "title": "Public ingress is missing a web application firewall",
            "severity": "critical",
            "description": "The workload exposes a public application endpoint without a WAF control.",
            "remediation": "Add Azure Front Door WAF or Application Gateway WAF before production cutover.",
            "impactedComponents": ["App Service", "Public endpoint"],
            "wafPillar": "Security",
            "wafTopic": "Protect public entry points with a web application firewall",
            "wafChecklistItemId": "sec-waf-1",
            "sourceCitations": [
                {
                    "id": "cite-doc-1",
                    "kind": "referenceDocument",
                    "referenceDocumentId": "doc-1",
                    "url": "https://learn.microsoft.com/azure/well-architected/security/",
                    "note": "Security pillar guidance",
                }
            ],
        }
    ]
    assert result["wafEvaluations"] == [
        {
            "itemId": "sec-waf-1",
            "pillar": "Security",
            "topic": "Protect public entry points with a web application firewall",
            "status": "open",
            "evidence": "Deterministic WAF evaluator marked this checklist item as open (coverageScore=0.0).",
            "relatedFindingIds": ["finding-sec-waf-1"],
            "sourceCitations": [
                {
                    "id": "cite-doc-1",
                    "kind": "referenceDocument",
                    "referenceDocumentId": "doc-1",
                    "url": "https://learn.microsoft.com/azure/well-architected/security/",
                    "note": "Security pillar guidance",
                }
            ],
        }
    ]


@pytest.mark.asyncio
async def test_waf_findings_worker_returns_noop_when_no_actionable_items_exist() -> None:
    async def _generator(system_prompt: str, user_prompt: str) -> dict[str, Any]:
        raise AssertionError("generator should not be called when all checklist items are fixed")

    worker = WAFFindingsWorker(
        generator=_generator,
        prompt_loader=_PromptLoaderStub(),
    )

    result = await worker.generate_findings(
        evaluator_result={
            "items": [
                {
                    "itemId": "rel-1",
                    "pillar": "Reliability",
                    "topic": "Use availability zones",
                    "status": "fixed",
                    "coverageScore": 1.0,
                    "matchedSourcePaths": ["candidateArchitectures[0].notes"],
                    "evidence": [],
                }
            ],
            "summary": {"evaluatedItems": 1},
        },
        architecture_state={"candidateArchitectures": [{"notes": "Zones are already enabled."}]},
    )

    assert result == {"findings": [], "wafEvaluations": []}


@pytest.mark.asyncio
async def test_waf_findings_worker_backfills_reference_citations_when_generator_omits_them() -> None:
    async def _generator(system_prompt: str, user_prompt: str) -> str:
        return json.dumps(
            {
                "findings": [
                    {
                        "title": "Private endpoints are not documented for data services",
                        "severity": "high",
                        "description": "The architecture does not show a private connectivity plan for storage traffic.",
                        "remediation": "Add Private Link for the storage account and document DNS ownership.",
                        "impactedComponents": ["Storage account"],
                        "wafPillar": "Security",
                        "wafTopic": "Use private endpoints",
                        "wafChecklistItemId": "sec-net-1",
                        "sourceCitations": [],
                    }
                ]
            }
        )

    worker = WAFFindingsWorker(
        generator=_generator,
        prompt_loader=_PromptLoaderStub(),
        id_factory=lambda item_id: f"finding-{item_id}",
    )

    result = await worker.generate_findings(
        evaluator_result={
            "items": [
                {
                    "itemId": "sec-net-1",
                    "pillar": "Security",
                    "topic": "Use private endpoints",
                    "status": "in_progress",
                    "coverageScore": 0.5,
                    "matchedSourcePaths": ["referenceDocuments[0].title"],
                    "evidence": [
                        {
                            "sourcePath": "referenceDocuments[0].title",
                            "excerpt": "Private endpoints are mandatory for storage and databases.",
                        }
                    ],
                }
            ],
            "summary": {"evaluatedItems": 1},
        },
        architecture_state={
            "referenceDocuments": [
                {
                    "id": "doc-private-endpoints",
                    "category": "guidance",
                    "title": "Private endpoints are mandatory for storage and databases.",
                    "url": "https://learn.microsoft.com/azure/storage/common/storage-private-endpoints",
                    "accessedAt": "2026-04-08T12:00:00+00:00",
                }
            ]
        },
    )

    finding = result["findings"][0]
    assert finding["severity"] == "high"
    assert finding["remediation"].startswith("Add Private Link")
    assert finding["sourceCitations"] == [
        {
            "id": "ref-doc-private-endpoints",
            "kind": "referenceDocument",
            "referenceDocumentId": "doc-private-endpoints",
            "url": "https://learn.microsoft.com/azure/storage/common/storage-private-endpoints",
            "note": "Use private endpoints",
        }
    ]
    assert result["wafEvaluations"][0]["sourceCitations"] == finding["sourceCitations"]
