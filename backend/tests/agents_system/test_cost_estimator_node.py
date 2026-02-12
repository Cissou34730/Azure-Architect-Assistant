from typing import Any

import pytest

from app.agents_system.langgraph.nodes import cost_estimator as cost_node


@pytest.mark.asyncio
async def test_cost_estimator_returns_clarification_when_inputs_are_insufficient():
    state = {
        "user_message": "estimate the cost for this architecture",
        "agent_handoff_context": {
            "project_context": "",
            "architecture": {},
            "resource_list": ["Extract from architecture description"],
            "region": "eastus",
            "environment": "production",
            "constraints": {},
        },
        "intermediate_steps": [],
    }

    result = await cost_node.cost_estimator_node(state)

    assert result["success"] is True
    assert result["current_agent"] == "cost_estimator"
    assert result["error"] is None
    assert "Please confirm" in result["agent_output"]
    assert "baseline assumptions" in result["agent_output"]


@pytest.mark.asyncio
async def test_cost_estimator_uses_deterministic_path_for_supported_services(monkeypatch):
    captured: dict[str, Any] = {}

    async def _fake_det_pricing(**kwargs: Any):
        captured["kwargs"] = kwargs
        return {
            "agent_output": "## Baseline Cost Estimate (deterministic pricing API path)\n- Estimated Monthly Total: `USD 42.00`",
            "intermediate_steps": [],
            "current_agent": "cost_estimator",
            "sub_agent_output": "deterministic",
            "cost_estimate": {"totalMonthlyCost": 42.0, "currencyCode": "USD"},
            "success": True,
            "error": None,
        }

    monkeypatch.setattr(cost_node, "_run_deterministic_cost_estimate", _fake_det_pricing)

    state = {
        "user_message": (
            "estimate monthly cost for SWA, Azure Functions Premium plan "
            "with 2 instances, and Table Storage with 100 GB"
        ),
        "agent_handoff_context": {
            "project_context": "Simple serverless workload",
            "architecture": {"description": "SWA + Functions + Table Storage"},
            "resource_list": ["Static Web Apps", "Function App", "Table Storage"],
            "region": "eastus",
            "environment": "production",
            "constraints": {},
        },
        "intermediate_steps": [],
    }

    result = await cost_node.cost_estimator_node(state)

    assert result["success"] is True
    assert result["error"] is None
    assert "pricing_lines" in captured["kwargs"]
    assert len(captured["kwargs"]["pricing_lines"]) >= 2
    assert "deterministic pricing API path" in result["agent_output"]


@pytest.mark.asyncio
async def test_cost_estimator_supported_services_without_sizing_runs_baseline_then_refines(monkeypatch):
    captured: dict[str, Any] = {}

    async def _fake_det_pricing(**kwargs: Any):
        captured["kwargs"] = kwargs
        return {
            "agent_output": "## Baseline Cost Estimate (deterministic pricing API path)\n- Estimated Monthly Total: `USD 33.00`",
            "intermediate_steps": [],
            "current_agent": "cost_estimator",
            "sub_agent_output": "deterministic",
            "cost_estimate": {"totalMonthlyCost": 33.0, "currencyCode": "USD"},
            "success": True,
            "error": None,
        }

    monkeypatch.setattr(cost_node, "_run_deterministic_cost_estimate", _fake_det_pricing)

    state = {
        "user_message": "estimate cost for SWA + Azure Functions + Table Storage",
        "agent_handoff_context": {
            "project_context": "",
            "architecture": {},
            "resource_list": ["Static Web Apps", "Function App", "Table Storage"],
            "region": "eastus",
            "environment": "production",
            "constraints": {},
        },
        "intermediate_steps": [],
    }

    result = await cost_node.cost_estimator_node(state)

    assert result["success"] is True
    assert "pricing_lines" in captured["kwargs"]
    assert "Estimated Monthly Total" in result["agent_output"]
    assert "To refine this estimate" in result["agent_output"]


@pytest.mark.asyncio
async def test_cost_estimator_baseline_acceptance_triggers_deterministic_path(monkeypatch):
    captured: dict[str, Any] = {}

    async def _fake_det_pricing(**kwargs: Any):
        captured["kwargs"] = kwargs
        return {
            "agent_output": "## Baseline Cost Estimate (deterministic pricing API path)\n- Estimated Monthly Total: `USD 99.00`",
            "intermediate_steps": [],
            "current_agent": "cost_estimator",
            "sub_agent_output": "deterministic",
            "cost_estimate": {"totalMonthlyCost": 99.0, "currencyCode": "USD"},
            "success": True,
            "error": None,
        }

    monkeypatch.setattr(cost_node, "_run_deterministic_cost_estimate", _fake_det_pricing)

    state = {
        "user_message": "use baseline assumptions for SWA and Azure Functions and Table Storage",
        "agent_handoff_context": {
            "project_context": "",
            "architecture": {},
            "resource_list": ["Static Web Apps", "Function App", "Table Storage"],
            "region": "eastus",
            "environment": "production",
            "constraints": {},
        },
        "intermediate_steps": [],
    }

    result = await cost_node.cost_estimator_node(state)

    assert result["success"] is True
    assert "pricing_lines" in captured["kwargs"]
    assert len(captured["kwargs"]["pricing_lines"]) >= 2
    assert "deterministic pricing API path" in result["agent_output"]


@pytest.mark.asyncio
async def test_cost_estimator_returns_unavailable_message_when_deterministic_fails(monkeypatch):

    async def _no_det_pricing(**kwargs: Any):
        return None

    monkeypatch.setattr(cost_node, "_run_deterministic_cost_estimate", _no_det_pricing)

    state = {
        "user_message": "use baseline assumptions for SWA and Azure Functions and Table Storage",
        "agent_handoff_context": {
            "project_context": "",
            "architecture": {"description": "SWA + Functions + Storage"},
            "resource_list": ["Static Web Apps", "Function App", "Table Storage"],
            "region": "eastus",
            "environment": "production",
            "constraints": {},
        },
        "intermediate_steps": [],
    }

    result = await cost_node.cost_estimator_node(state)

    assert result["success"] is True
    assert result["error"] is None
    assert "could not build a reliable pricing-line mapping" in result["agent_output"].lower()
    assert "auto-derive services" in result["agent_output"].lower()


@pytest.mark.asyncio
async def test_cost_estimator_uses_architecture_context_for_service_inference(monkeypatch):
    captured: dict[str, Any] = {}

    async def _fake_det_pricing(**kwargs: Any):
        captured["kwargs"] = kwargs
        return {
            "agent_output": "## Baseline Cost Estimate (deterministic pricing API path)\n- Estimated Monthly Total: `USD 12.00`",
            "intermediate_steps": [],
            "current_agent": "cost_estimator",
            "sub_agent_output": "deterministic",
            "cost_estimate": {"totalMonthlyCost": 12.0, "currencyCode": "USD"},
            "success": True,
            "error": None,
        }

    monkeypatch.setattr(cost_node, "_run_deterministic_cost_estimate", _fake_det_pricing)

    state = {
        "user_message": "can you provide a price estimate taking assumptions you need",
        "agent_handoff_context": {
            "project_context": "Architecture includes App Service, API Management, Redis Cache",
            "architecture": {"description": "Web app on App Service with API Management and Redis"},
            "resource_list": ["web-api (App Service)", "api-gateway (API Management)", "cache (Redis Cache)"],
            "region": "eastus",
            "environment": "development",
            "constraints": {},
        },
        "intermediate_steps": [],
    }

    result = await cost_node.cost_estimator_node(state)

    assert result["success"] is True
    assert "pricing_lines" in captured["kwargs"]
    assert len(captured["kwargs"]["pricing_lines"]) >= 1
    assert "deterministic pricing API path" in result["agent_output"]
