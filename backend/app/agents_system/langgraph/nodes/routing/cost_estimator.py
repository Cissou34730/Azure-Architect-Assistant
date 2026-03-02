"""Cost Estimator routing and handoff logic."""

import logging
from typing import Any

from ...state import GraphState
from ..stage_routing import ProjectStage
from .iac_generator import _extract_resource_list

logger = logging.getLogger(__name__)


def should_route_to_cost_estimator(state: GraphState) -> bool:
    """
    Determine if request should go to Cost Estimator sub-agent.

    Route to Cost Estimator ONLY when:
    - User explicitly mentions "cost", "price", "pricing", "how much", "TCO", "budget"
    - User asks for cost estimate or breakdown
    - Architecture is finalized (candidateArchitectures exists)

    DO NOT route for:
    - General architecture questions (no cost aspect)
    - Budget as a constraint (not requesting estimate)

    This is a LOW priority routing check (after IaC, Architecture, and SaaS).

    Args:
        state: Current graph state

    Returns:
        True if should route to Cost Estimator
    """
    user_message = (state.get("user_message") or "").lower()

    # Explicit cost keywords (strict matching)
    cost_keywords = [
        "cost", "price", "pricing", "how much",
        "tco", "total cost of ownership",
        "budget estimate", "cost estimate", "estimate cost",
        "monthly cost", "annual cost", "pricing breakdown",
        "cost analysis", "cost breakdown", "cost calculation",
        "cost comparison", "cost optimization",
    ]

    explicit_cost = any(keyword in user_message for keyword in cost_keywords)
    next_stage = state.get("next_stage")

    if explicit_cost:
        # Prefer existing architecture when available.
        project_state = state.get("current_project_state") or {}
        has_architecture = bool(project_state.get("candidateArchitectures"))

        if has_architecture:
            logger.info("💰 Routing to Cost Estimator: explicit cost request + architecture exists")
            return True

        # Service-based pricing requests can be estimated without a finalized
        # candidate architecture by asking assumptions/quantities first.
        if _has_service_pricing_signals(user_message):
            logger.info("💰 Routing to Cost Estimator: explicit cost request + service signals")
            return True

        # Route anyway for clarification-first pricing instead of falling back
        # to generic agent loops.
        logger.info(
            "💰 Routing to Cost Estimator: explicit cost request without finalized architecture"
        )
        return True

    # Check project stage
    if next_stage == ProjectStage.PRICING.value:
        logger.info("💰 Routing to Cost Estimator: project stage is 'pricing'")
        return True

    return False


def _has_service_pricing_signals(user_message: str) -> bool:
    """Detect service hints in user text for pricing-first workflows."""
    service_tokens = [
        "swa",
        "static web app",
        "static web apps",
        "azure function",
        "function app",
        "table storage",
        "storage account",
        "blob storage",
        "sql database",
        "cosmos db",
        "app service",
        "aks",
        "api management",
        "service bus",
        "event hub",
        "front door",
        "application gateway",
        "redis",
        "key vault",
    ]
    return any(token in user_message for token in service_tokens)


def prepare_cost_estimator_handoff(state: GraphState) -> dict[str, Any]:
    """
    Prepare handoff context for Cost Estimator sub-agent.

    Extracts architecture, resource list, and constraints to pass
    to the specialized cost estimation agent.

    Args:
        state: Current graph state

    Returns:
        State update with agent_handoff_context for Cost Estimator
    """
    project_state = state.get("current_project_state") or {}
    context_summary = state.get("context_summary") or ""

    # Extract architecture (use first candidate if multiple)
    candidate_architectures = project_state.get("candidateArchitectures") or []
    architecture = candidate_architectures[0] if candidate_architectures else {}

    # Extract resource list from architecture
    resource_list = _extract_resource_list(architecture, context_summary)

    # Detect region from user message or requirements
    user_message = state.get("user_message", "").lower()
    requirements = project_state.get("requirements") or {}
    region = _detect_region(user_message, requirements)

    # Detect environment (production, dev, test)
    environment = _detect_environment(user_message, context_summary)

    # Extract constraints
    req_params = requirements if isinstance(requirements, dict) else {}
    constraints = {
        "budget": req_params.get("budget"),
        "reserved_instances": "reserved instance" in user_message or "ri" in user_message,
        "azure_hybrid_benefit": "ahb" in user_message or "hybrid benefit" in user_message,
        "spot_instances": "spot" in user_message,
        "compliance": req_params.get("compliance", []),
    }
    # Remove None/False values
    constraints = {k: v for k, v in constraints.items() if v}

    handoff_context = {
        "project_context": context_summary,
        "architecture": architecture,
        "resource_list": resource_list,
        "region": region,
        "environment": environment,
        "constraints": constraints,
        "user_request": state.get("user_message", ""),
        "routing_reason": "Cost estimation requested for finalized architecture",
    }

    logger.info(
        f"Prepared Cost Estimator handoff context: "
        f"region={region}, environment={environment}, {len(resource_list)} resources"
    )

    return {
        "agent_handoff_context": handoff_context,
        "current_agent": "cost_estimator",
    }


def _detect_region(user_message: str, requirements: dict[str, Any]) -> str:
    """
    Detect Azure region from user message or requirements.

    Args:
        user_message: User's message
        requirements: Project requirements

    Returns:
        Azure region (defaults to eastus)
    """
    # Common Azure regions
    regions = [
        "eastus", "eastus2", "westus", "westus2", "westus3",
        "centralus", "northcentralus", "southcentralus",
        "westcentralus", "canadacentral", "canadaeast",
        "brazilsouth", "northeurope", "westeurope",
        "uksouth", "ukwest", "francecentral", "germanywestcentral",
        "switzerlandnorth", "norwayeast", "swedencentral",
        "eastasia", "southeastasia", "japaneast", "japanwest",
        "australiaeast", "australiasoutheast", "centralindia",
        "southindia", "westindia",
    ]

    # Check user message
    for region in regions:
        if region in user_message:
            return region

    # Check requirements
    req_params = requirements if isinstance(requirements, dict) else {}
    allowed_regions = req_params.get("allowedRegions", [])
    if allowed_regions:
        return allowed_regions[0]

    # Default to East US
    return "eastus"


def _detect_environment(user_message: str, context_summary: str) -> str:
    """
    Detect environment type (production, dev, test).

    Args:
        user_message: User's message
        context_summary: Context summary

    Returns:
        Environment type (defaults to production)
    """
    combined_text = f"{user_message} {context_summary}".lower()

    if any(keyword in combined_text for keyword in ["dev", "development", "sandbox"]):
        return "development"
    elif any(keyword in combined_text for keyword in ["test", "testing", "qa", "staging"]):
        return "test"
    elif any(keyword in combined_text for keyword in ["prod", "production"]):
        return "production"

    # Default to production for cost estimates
    return "production"
