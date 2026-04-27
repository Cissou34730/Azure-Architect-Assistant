from __future__ import annotations

import json
from typing import Any

import pytest

from app.agents_system.langgraph.nodes.research import execute_research_worker_node
from app.agents_system.tools.research_tool import (
    EvidencePacket,
    GroundedResearchPacket,
    ResearchFacade,
    ResearchScope,
)
from app.agents_system.tools.tool_registry import get_allowed_runtime_tool_names
from app.features.agent.infrastructure.tools.aaa_cost_tool import AAAGenerateCostTool
from app.features.agent.infrastructure.tools.azure_retail_prices_tool import AzureRetailPricesTool


@pytest.mark.asyncio
async def test_research_facade_combines_sources_and_reranks_evidence() -> None:
    async def fake_project_search(query: str) -> list[dict[str, Any]]:
        assert query == "Azure Functions networking"
        return [
            {
                "documentId": "doc-1",
                "fileName": "solution-overview.md",
                "excerpt": "Azure Functions networking requires VNet integration for private endpoints.",
            }
        ]

    async def fake_kb_search(query: str) -> dict[str, Any]:
        assert query == "Azure Functions networking"
        return {
            "sources": [
                {
                    "title": "Azure Functions networking options",
                    "content": "Use private endpoints with Premium plans when isolation is required.",
                    "url": "https://learn.microsoft.com/azure/azure-functions/functions-networking-options",
                    "kb_name": "WAF",
                }
            ]
        }

    async def fake_docs_search(query: str) -> dict[str, Any]:
        assert query == "Azure Functions networking"
        return {
            "results": [
                {
                    "title": "Azure Functions networking options",
                    "content": "Functions supports VNet integration and private endpoints for inbound traffic.",
                    "contentUrl": "https://learn.microsoft.com/azure/azure-functions/functions-networking-options",
                }
            ]
        }

    async def fake_docs_fetch(url: str) -> dict[str, Any]:
        assert url == "https://learn.microsoft.com/azure/azure-functions/functions-networking-options"
        return {
            "url": url,
            "content": "Inbound private endpoints and outbound VNet integration are supported.",
            "length": 78,
        }

    facade = ResearchFacade(
        project_search=fake_project_search,
        kb_search=fake_kb_search,
        microsoft_docs_search=fake_docs_search,
        microsoft_docs_fetch=fake_docs_fetch,
    )

    result = await facade.research("Azure Functions networking", scope=ResearchScope.ALL)

    assert result.consulted_sources == ["project_document", "kb", "microsoft_docs"]
    assert [packet["source"] for packet in result.evidence] == [
        "project_document",
        "microsoft_docs",
        "kb",
    ]
    assert result.evidence[0]["sourceDocument"] == "solution-overview.md"
    assert result.evidence[1]["url"] == "https://learn.microsoft.com/azure/azure-functions/functions-networking-options"

def test_grounded_research_packet_contract_serializes_grounding_fields() -> None:
    packet = GroundedResearchPacket(
        packet_id="research-packet-1",
        focus="Azure Functions networking",
        query="propose candidate: Azure Functions networking",
        stage="propose_candidate",
        requirement_targets=["Private ingress"],
        mindmap_topics=["networking"],
        recommended_sources=["Microsoft Learn"],
        expected_evidence=["Capture at least one authoritative source."],
        consumer_guidance="Use grounded evidence.",
        evidence=[
            EvidencePacket(
                id="ev-1",
                source="kb",
                title="Functions networking",
                excerpt="Use private endpoints for inbound traffic.",
                relevance_score=0.91,
            )
        ],
        consulted_sources=["kb"],
        grounding_status="grounded",
    )

    serialized = packet.model_dump(mode="json", by_alias=True)

    assert serialized["consultedSources"] == ["kb"]
    assert serialized["groundingStatus"] == "grounded"
    assert serialized["evidence"][0]["id"] == "ev-1"




def test_evidence_packet_contract_serializes_with_aliases() -> None:
    packet = EvidencePacket(
        id="ev-1",
        source="kb",
        title="Functions networking",
        excerpt="Use private endpoints for inbound traffic.",
        url="https://learn.microsoft.com/example",
        relevance_score=0.91,
        source_document="waf",
    )

    serialized = packet.model_dump(mode="json", by_alias=True)

    assert serialized == {
        "id": "ev-1",
        "source": "kb",
        "title": "Functions networking",
        "excerpt": "Use private endpoints for inbound traffic.",
        "url": "https://learn.microsoft.com/example",
        "relevanceScore": 0.91,
        "sourceDocument": "waf",
    }


@pytest.mark.asyncio
async def test_execute_research_worker_node_materializes_grounded_packets() -> None:
    class StubFacade:
        async def research(self, query: str, scope: ResearchScope = ResearchScope.ALL):
            assert scope is ResearchScope.ALL
            return type(
                "StubResult",
                (),
                {
                    "evidence": [
                        {
                            "id": "ev-1",
                            "source": "kb",
                            "title": "Functions networking",
                            "excerpt": f"Evidence for {query}",
                            "url": "https://learn.microsoft.com/example",
                            "relevanceScore": 0.91,
                            "sourceDocument": None,
                        }
                    ],
                    "consulted_sources": ["kb"],
                },
            )()

    result = await execute_research_worker_node(
        {
            "project_id": "proj-1",
            "next_stage": "propose_candidate",
            "research_plan": ["Azure Functions networking options"],
            "current_project_state": {
                "requirements": [{"id": "req-1", "title": "Private ingress"}]
            },
        },
        research_facade=StubFacade(),
    )

    assert result["research_execution_artifact"]["groundedPackets"] == 1
    packet = result["research_evidence_packets"][0]
    assert packet["groundingStatus"] == "grounded"
    assert packet["evidence"][0]["id"] == "ev-1"
    assert packet["consultedSources"] == ["kb"]


@pytest.mark.asyncio
async def test_azure_retail_prices_tool_caches_structured_results() -> None:
    calls: list[str] = []

    class FakeClient:
        async def query_all_with_meta(
            self, *, filter_expr: str, top: int = 1000, max_pages: int = 25
        ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
            calls.append(filter_expr)
            return (
                [
                    {
                        "serviceName": "Azure Functions",
                        "armRegionName": "eastus",
                        "skuName": "Consumption",
                        "meterName": "Execution Time",
                        "retailPrice": 0.2,
                        "unitOfMeasure": "1M executions",
                    }
                ],
                {"pages": 2, "requests": [{"url": "https://prices.azure.com/api/retail/prices"}]},
            )

    tool = AzureRetailPricesTool(client=FakeClient(), cache_ttl_seconds=3600)

    first = json.loads(
        await tool._arun(
            {
                "serviceName": "Azure Functions",
                "region": "eastus",
                "skuName": "Consumption",
            }
        )
    )
    second = json.loads(
        await tool._arun(
            {
                "serviceName": "Azure Functions",
                "region": "eastus",
                "skuName": "Consumption",
            }
        )
    )

    assert len(calls) == 1
    assert first["itemCount"] == 1
    assert first["items"][0]["meterName"] == "Execution Time"
    assert second["fromCache"] is True


@pytest.mark.asyncio
async def test_cost_tool_uses_standalone_retail_prices_tool() -> None:
    requests: list[dict[str, Any]] = []

    class FakeRetailPricesTool:
        async def lookup_prices(self, payload: dict[str, Any]) -> dict[str, Any]:
            requests.append(payload)
            return {
                "items": [
                    {
                        "serviceName": payload["serviceName"],
                        "armRegionName": payload["region"],
                        "skuName": payload["skuName"],
                        "meterName": "Execution Time",
                        "retailPrice": 0.2,
                        "unitOfMeasure": "1M executions",
                    }
                ],
                "meta": {"pages": 1},
                "fromCache": False,
            }

    tool = AAAGenerateCostTool(retail_prices_tool=FakeRetailPricesTool())
    result = await tool._arun(
        payload={
            "pricingLines": [
                {
                    "name": "Azure Functions executions baseline",
                    "serviceName": "Azure Functions",
                    "armRegionName": "eastus",
                    "skuName": "Consumption",
                    "monthlyQuantity": 2,
                }
            ]
        }
    )

    assert requests == [
        {
            "serviceName": "Azure Functions",
            "region": "eastus",
            "skuName": "Consumption",
            "productNameContains": None,
            "meterNameContains": None,
            "currencyCode": "USD",
        }
    ]
    assert "AAA_STATE_UPDATE" in result
    assert "AAA_PRICING_LOG" in result


def test_runtime_tool_registry_exposes_pricing_tool_only_for_v1_slice() -> None:
    assert "research" not in get_allowed_runtime_tool_names("propose_candidate")
    assert "azure_retail_prices" in get_allowed_runtime_tool_names("pricing")
    assert "azure_retail_prices" not in get_allowed_runtime_tool_names("validate")


# ---------------------------------------------------------------------------
# P9: Cost estimation precision and transparency tests
# ---------------------------------------------------------------------------

from app.features.agent.infrastructure.tools.aaa_cost_tool import AAAGenerateCostInput  # noqa: E402


def test_cost_input_defaults_to_low_confidence() -> None:
    """Default confidence_level must be 'low' to prevent overconfident estimates."""
    inp = AAAGenerateCostInput()
    assert inp.confidence_level == "low"


def test_cost_input_accepts_region_and_currency() -> None:
    """region and currency fields must be accepted and stored."""
    inp = AAAGenerateCostInput(region="westeurope", currency="EUR")
    assert inp.region == "westeurope"
    assert inp.currency == "EUR"


def test_cost_input_no_architecture_available() -> None:
    """AAAGenerateCostInput must work with an empty pricing_lines list."""
    inp = AAAGenerateCostInput(pricing_lines=[])
    assert inp.pricing_lines == []
    assert inp.is_baseline_estimate is True


def test_cost_input_accepts_optimization_opportunities() -> None:
    """optimization_opportunities field must be stored correctly."""
    tips = ["Use Reserved Instances", "Enable auto-scaling"]
    inp = AAAGenerateCostInput(optimization_opportunities=tips)
    assert inp.optimization_opportunities == tips


def test_cost_input_baseline_estimate_flag() -> None:
    """is_baseline_estimate must default to True."""
    inp = AAAGenerateCostInput()
    assert inp.is_baseline_estimate is True


def test_cost_input_accepts_pricing_assumptions() -> None:
    """pricing_assumptions must default to empty list and accept values."""
    inp_default = AAAGenerateCostInput()
    assert inp_default.pricing_assumptions == []
    inp_with = AAAGenerateCostInput(pricing_assumptions=["Assumed 730 hours/month"])
    assert inp_with.pricing_assumptions == ["Assumed 730 hours/month"]


def test_cost_input_accepts_pricing_gaps() -> None:
    """pricing_gaps must default to empty list and accept values."""
    inp = AAAGenerateCostInput(pricing_gaps=["SKU not specified"])
    assert inp.pricing_gaps == ["SKU not specified"]


def test_cost_input_accepts_accuracy_improvement_tips() -> None:
    """accuracy_improvement_tips must default to empty list and accept values."""
    inp = AAAGenerateCostInput(
        accuracy_improvement_tips=["Provide exact SKU", "Specify instance count"]
    )
    assert len(inp.accuracy_improvement_tips) == 2


def test_cost_input_accepts_excluded_services() -> None:
    """excluded_services must default to empty list and accept values."""
    inp = AAAGenerateCostInput(excluded_services=["Azure Firewall", "DDoS Protection"])
    assert inp.excluded_services == ["Azure Firewall", "DDoS Protection"]


def test_cost_input_environment_and_confidence_explicit() -> None:
    """environment and confidence_level must be settable to non-default values."""
    inp = AAAGenerateCostInput(environment="staging", confidence_level="medium")
    assert inp.environment == "staging"
    assert inp.confidence_level == "medium"
