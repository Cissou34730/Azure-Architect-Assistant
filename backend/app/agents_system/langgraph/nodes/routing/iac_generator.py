"""IaC Generator routing and handoff logic."""

import logging
from typing import Any

from ...state import GraphState
from ..stage_routing import ProjectStage

logger = logging.getLogger(__name__)


def should_route_to_iac_generator(state: GraphState) -> bool:
    """
    Determine if request should go to IaC Generator sub-agent.

    Route to IaC Generator when:
    - User explicitly requests "terraform", "bicep", "iac"
    - Project stage is "iac"
    - Architecture is finalized (candidateArchitectures exists)

    Args:
        state: Current graph state

    Returns:
        True if should route to IaC generator
    """
    user_message = (state.get("user_message") or "").lower()

    # Explicit IaC keywords
    iac_keywords = [
        "terraform", "bicep", "iac", "infrastructure as code",
        "infrastructure code", "deploy", "provision",
        "generate bicep", "generate terraform", "create iac",
    ]

    if any(keyword in user_message for keyword in iac_keywords):
        # Only route if architecture is finalized
        project_state = state.get("current_project_state") or {}
        has_architecture = bool(project_state.get("candidateArchitectures"))

        if has_architecture:
            logger.info("🎯 Routing to IaC Generator: explicit request + architecture exists")
            return True
        else:
            logger.warning(
                "IaC request detected but no architecture finalized. "
                "Will not route to IaC Generator."
            )
            return False

    # Check project stage
    next_stage = state.get("next_stage")
    if next_stage == ProjectStage.IAC.value:
        logger.info("🎯 Routing to IaC Generator: project stage is 'iac'")
        return True

    return False


def prepare_iac_generator_handoff(state: GraphState) -> dict[str, Any]:
    """
    Prepare handoff context for IaC Generator sub-agent.

    Extracts architecture, resource list, and constraints to pass
    to the specialized IaC generation agent.

    Args:
        state: Current graph state

    Returns:
        State update with agent_handoff_context
    """
    project_state = state.get("current_project_state") or {}
    context_summary = state.get("context_summary") or ""

    # Extract architecture (use first candidate if multiple)
    candidate_architectures = project_state.get("candidateArchitectures") or []
    architecture = candidate_architectures[0] if candidate_architectures else {}

    # Extract resource list from architecture
    resource_list = _extract_resource_list(architecture, context_summary)

    # Detect IaC format from user message
    user_message = state.get("user_message", "").lower()
    iac_format = _detect_iac_format(user_message)

    # Extract constraints
    requirements = project_state.get("requirements") or {}

    # Handle list requirements by normalizing for parameter extraction
    req_params = requirements if isinstance(requirements, dict) else {}

    constraints = {
        "regions": req_params.get("allowedRegions", []),
        "naming_convention": req_params.get("namingConvention"),
        "tagging_policy": req_params.get("taggingPolicy", {}),
        "compliance": req_params.get("compliance", []),
    }
    # Remove None values
    constraints = {k: v for k, v in constraints.items() if v}

    handoff_context = {
        "project_context": context_summary,
        "architecture": architecture,
        "resource_list": resource_list,
        "constraints": constraints,
        "iac_format": iac_format,
        "user_request": state.get("user_message", ""),
        "routing_reason": "IaC generation for finalized architecture",
    }

    logger.info(
        f"Prepared IaC Generator handoff context: "
        f"format={iac_format}, {len(resource_list)} resources"
    )

    return {
        "agent_handoff_context": handoff_context,
        "current_agent": "iac_generator",
    }


def _extract_resource_list(architecture: dict[str, Any], context: str) -> list[str]:
    """Extract list of Azure resources from architecture."""
    resources = []

    # Try to extract from architecture components
    if "components" in architecture:
        components = architecture["components"]
        if isinstance(components, list):
            for component in components:
                if isinstance(component, dict) and "type" in component:
                    resources.append(f"{component.get('name', 'unnamed')} ({component['type']})")
                elif isinstance(component, str):
                    resources.append(component)

    # If no components, try to parse from description or diagram
    if not resources:
        # Common Azure resource type keywords
        azure_resources = [
            "App Service", "Function App", "Storage Account", "Cosmos DB",
            "SQL Database", "Key Vault", "Application Insights", "Virtual Network",
            "API Management", "Service Bus", "Event Hubs", "Container Instances",
            "Kubernetes Service", "Redis Cache", "Front Door", "CDN",
        ]

        description = architecture.get("description", "")
        diagram = architecture.get("diagram", "")
        combined_text = f"{description} {diagram} {context}".lower()

        for resource_type in azure_resources:
            if resource_type.lower() in combined_text:
                resources.append(resource_type)

    return resources if resources else ["Extract from architecture description"]


def _detect_iac_format(user_message: str) -> str:
    """Detect IaC format (Bicep or Terraform) from user message."""
    if "terraform" in user_message:
        return "terraform"
    elif "bicep" in user_message:
        return "bicep"
    else:
        # Default to Bicep (Azure-native)
        return "bicep"
