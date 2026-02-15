"""
IaC Generator Node - Specialized agent for Infrastructure as Code generation.

This module provides a specialized sub-agent for generating production-ready
Bicep and Terraform code with schema validation.
"""

import logging
from typing import Any

from app.agents_system.runner import get_agent_runner
from app.agents_system.config.prompt_loader import PromptLoader

from ..state import GraphState
from .agent_native import run_stage_aware_agent

logger = logging.getLogger(__name__)


async def iac_generator_node(state: GraphState) -> dict[str, Any]:
    """
    Specialized node for Infrastructure as Code generation.

    This node is invoked when:
    - User requests IaC generation (Bicep or Terraform)
    - Project stage is "iac"
    - Architecture is finalized

    The IaC Generator specializes in:
    - Bicep code generation with best practices
    - Terraform code generation with best practices
    - Azure resource schema validation
    - Parameterization and modularization
    - Resource dependency management
    - IaC linting and validation

    Args:
        state: Current graph state with architecture context

    Returns:
        Updated state with IaC code
    """
    logger.info("⚙️ IaC Generator Agent activated")

    try:
        # Load IaC generator prompt
        prompt_loader = PromptLoader()
        iac_generator_prompt = prompt_loader.load_prompt("iac_generator_prompt.yaml")

        # Prepare handoff context for IaC generator
        handoff_context = state.get("agent_handoff_context", {})
        project_context = handoff_context.get("project_context", "")
        architecture = handoff_context.get("architecture", {})
        resource_list = handoff_context.get("resource_list", [])
        constraints = handoff_context.get("constraints", {})
        iac_format = handoff_context.get("iac_format", "bicep")  # Default to Bicep

        # Get user's original request
        user_message = state.get("user_message", "")

        # Construct comprehensive input for IaC generator
        iac_generator_input = f"""
{user_message}

**Context from Main Agent:**

**Project Context:**
{project_context}

**Architecture:**
{_format_architecture(architecture)}

**Azure Resources to Provision:**
{_format_resource_list(resource_list)}

**Constraints:**
{_format_constraints(constraints)}

**Target Format:** {iac_format.upper()}

---

**Task:** Generate production-ready {iac_format.upper()} code for this architecture. Include:

1. **Schema Validation** - Validate all resources against latest Azure API schemas
2. **Parameterized Templates** - Proper parameters with descriptions and defaults
3. **Modular Structure** - Separate modules for networking, security, compute, data, monitoring
4. **Best Practices** - Follow latest {iac_format.upper()} best practices
5. **Deployment Instructions** - Clear step-by-step deployment guide
6. **Resource Tagging** - Consistent tags for cost tracking and compliance

Ensure all code is production-ready and validated.
"""

        logger.info(f"IaC Generator invoking LangGraph-native agent for {iac_format}...")

        runner = await get_agent_runner()
        iac_state: GraphState = dict(state)
        iac_state["user_message"] = iac_generator_input
        iac_state["stage_directives"] = str(iac_generator_prompt.get("system_prompt", ""))

        result = await run_stage_aware_agent(
            iac_state,
            mcp_client=getattr(runner, "mcp_client", None),
            openai_settings=getattr(runner, "openai_settings", None),
        )

        iac_code = str(result.get("agent_output", ""))
        intermediate_steps = result.get("intermediate_steps", [])

        logger.info(
            f"✅ IaC Generator completed ({iac_format}) with "
            f"{len(intermediate_steps)} tool calls"
        )

        return {
            "agent_output": iac_code,
            "intermediate_steps": state.get("intermediate_steps", []) + intermediate_steps,
            "current_agent": "iac_generator",
            "sub_agent_output": iac_code,
            "success": bool(result.get("success", True)),
            "error": result.get("error"),
        }

    except Exception as exc:
        logger.error(f"❌ IaC Generator failed: {exc}", exc_info=True)

        # Graceful fallback: Return error but don't break the workflow
        error_msg = (
            f"IaC Generator encountered an error: {exc!s}\n\n"
            "Falling back to main agent for IaC generation. "
            "The main agent will provide a best-effort IaC code."
        )

        return {
            "agent_output": error_msg,
            "current_agent": "main",  # Fallback to main agent
            "sub_agent_output": None,
            "success": False,
            "error": str(exc),
        }


def _format_architecture(architecture: dict[str, Any] | list[dict[str, Any]]) -> str:
    """Format architecture for display."""
    if not architecture:
        return "No architecture information available."

    # If architecture is a list (multiple candidates), use the first one
    if isinstance(architecture, list):
        architecture = architecture[0] if architecture else {}

    formatted = []
    if "title" in architecture:
        formatted.append(f"**Title:** {architecture['title']}")
    if "description" in architecture:
        formatted.append(f"**Description:** {architecture['description']}")
    if "components" in architecture:
        components = architecture["components"]
        if components:
            formatted.append(f"**Components:** {', '.join(str(c) for c in components)}")
    if "diagram" in architecture:
        formatted.append(f"**Diagram:** {architecture['diagram']}")

    return "\n".join(formatted) if formatted else str(architecture)


def _format_resource_list(resources: list[str] | list[dict[str, Any]]) -> str:
    """Format Azure resource list for display."""
    if not resources:
        return "No explicit resource list provided. Extract from architecture."

    if isinstance(resources, list) and resources:
        if isinstance(resources[0], str):
            return "\n".join(f"- {resource}" for resource in resources)
        elif isinstance(resources[0], dict):
            formatted = []
            for resource in resources:
                name = resource.get("name", "Unknown")
                resource_type = resource.get("type", "Unknown")
                formatted.append(f"- {name} ({resource_type})")
            return "\n".join(formatted)

    return str(resources)


def _format_constraints(constraints: dict[str, Any]) -> str:
    """Format constraints dictionary for display."""
    if not constraints:
        return "No explicit constraints provided."

    formatted = []
    if "regions" in constraints:
        formatted.append(f"- Allowed Regions: {', '.join(constraints['regions'])}")
    if "naming_convention" in constraints:
        formatted.append(f"- Naming Convention: {constraints['naming_convention']}")
    if "tagging_policy" in constraints:
        tags = constraints["tagging_policy"]
        formatted.append(f"- Required Tags: {', '.join(f'{k}={v}' for k, v in tags.items())}")
    if "compliance" in constraints:
        formatted.append(f"- Compliance: {', '.join(constraints['compliance'])}")

    return "\n".join(formatted) if formatted else "No explicit constraints provided."
