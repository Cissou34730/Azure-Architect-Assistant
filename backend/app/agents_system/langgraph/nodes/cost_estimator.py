"""
Cost Estimator Node - Specialized agent for Azure cost estimation.

This module provides a specialized sub-agent for calculating Azure cost estimates
using the Azure Retail Prices API and providing optimization recommendations.
"""

import logging
import re
from typing import Any

from app.agents_system.agents.mcp_react_agent import MCPReActAgent
from app.agents_system.config.prompt_loader import PromptLoader
from app.agents_system.tools.aaa_candidate_tool import create_aaa_tools

from ..state import GraphState

logger = logging.getLogger(__name__)


async def cost_estimator_node(state: GraphState) -> dict[str, Any]:
    """
    Specialized node for Azure cost estimation.

    This node is invoked when:
    - User requests "cost", "price", "pricing", "how much"
    - User asks for "TCO", "total cost of ownership", "budget"
    - Finalized architecture exists in project state

    The Cost Estimator specializes in:
    - Azure Retail Prices API integration
    - Cost calculation (hourly → monthly → annual → 3-year TCO)
    - Service and SKU identification
    - Regional pricing differences
    - Reserved Instance and cost optimization recommendations
    - Pricing breakdown by service

    Args:
        state: Current graph state with project context and architecture

    Returns:
        Updated state with cost estimate
    """
    logger.info("💰 Cost Estimator Agent activated")

    try:
        # Load cost estimator prompt
        prompt_loader = PromptLoader()
        cost_prompt = prompt_loader.load_prompt("cost_estimator_prompt.yaml")

        # Prepare handoff context for cost estimator
        handoff_context = state.get("agent_handoff_context", {})
        project_context = handoff_context.get("project_context", "")
        architecture = handoff_context.get("architecture", "")
        resource_list = handoff_context.get("resource_list", [])
        region = handoff_context.get("region", "eastus")
        environment = handoff_context.get("environment", "production")
        constraints = handoff_context.get("constraints", {})

        # Get user's original request
        user_message = state.get("user_message", "")

        # Construct comprehensive input for cost estimator
        cost_estimator_input = f"""
{user_message}

**Context from Main Agent:**

**Project Context:**
{project_context}

**Architecture to Cost:**
{architecture if architecture else "No architecture provided. Unable to estimate costs without architecture details."}

**Azure Services Identified:**
{_format_resource_list(resource_list)}

**Target Region:**
{region}

**Environment:**
{environment}

**Constraints:**
{_format_constraints(constraints)}

---

**Task:** Calculate a comprehensive Azure cost estimate for this architecture. Include:

1. **Total Cost Summary** (monthly, annual, 3-year TCO)
2. **Cost Breakdown by Service** (table with service, SKU, quantity, monthly/annual costs)
3. **Regional Pricing** (if multi-region architecture)
4. **Cost Optimization Opportunities** with specific savings estimates:
   - Reserved Instances (1-year, 3-year savings percentages)
   - Right-Sizing recommendations
   - Azure Hybrid Benefit
   - Dev/Test pricing
   - Auto-scaling strategies
5. **Alternative SKU Suggestions** with trade-offs
6. **Pricing Lines for aaa_record_iac_and_cost** tool

Use the Azure Retail Prices API to get accurate, up-to-date pricing. Do not guess prices.

**Important:** If architecture details are insufficient, request clarification from the user about:
- Specific Azure services to use
- SKU/tier for each service
- Number of instances/quantity
- Expected usage patterns
"""

        # Create cost estimator agent with specialized prompt
        cost_agent = MCPReActAgent(
            system_prompt=cost_prompt["system_prompt"],
            react_template=cost_prompt.get("react_template", ""),
            tools=create_aaa_tools(state),  # Reuse AAA tools
            model_name="gpt-4o",  # Use GPT-4 for complex cost reasoning
            temperature=0.1,  # Low temperature for consistency
        )

        logger.info("Cost Estimator agent initialized, invoking...")

        # Invoke cost estimator agent
        result = await cost_agent.ainvoke({
            "input": cost_estimator_input,
            "context": project_context,
        })

        cost_estimate = result.get("output", "")
        intermediate_steps = result.get("intermediate_steps", [])

        logger.info(f"✅ Cost Estimator completed with {len(intermediate_steps)} tool calls")

        # Extract cost summary from estimate
        cost_summary = _extract_cost_summary(cost_estimate)

        return {
            "agent_output": cost_estimate,
            "intermediate_steps": state.get("intermediate_steps", []) + intermediate_steps,
            "current_agent": "cost_estimator",
            "sub_agent_output": cost_estimate,
            "cost_estimate": cost_summary,
            "success": True,
            "error": None,
        }

    except Exception as exc:
        logger.error(f"❌ Cost Estimator failed: {exc}", exc_info=True)

        # Graceful fallback: Return error but don't break the workflow
        error_msg = (
            f"Cost Estimator encountered an error: {exc!s}\n\n"
            "Falling back to main agent for cost guidance. "
            "The main agent will provide best-effort cost estimates based on available data."
        )

        return {
            "agent_output": error_msg,
            "current_agent": "main",  # Fallback to main agent
            "sub_agent_output": None,
            "cost_estimate": None,
            "success": False,
            "error": str(exc),
        }


def _format_resource_list(resources: list[str]) -> str:
    """Format list of Azure resources for display."""
    if not resources:
        return "No resources identified. Please provide architecture details."

    formatted = []
    for idx, resource in enumerate(resources, 1):
        formatted.append(f"{idx}. {resource}")

    return "\n".join(formatted)


def _format_constraints(constraints: dict[str, Any]) -> str:
    """Format constraints dictionary for display."""
    if not constraints:
        return "No explicit constraints provided."

    formatted = []
    if "budget" in constraints:
        formatted.append(f"- Budget: {constraints['budget']}")
    if "timeline" in constraints:
        formatted.append(f"- Timeline: {constraints['timeline']}")
    if "compliance" in constraints:
        formatted.append(f"- Compliance: {', '.join(constraints['compliance'])}")
    if "regions" in constraints:
        formatted.append(f"- Allowed Regions: {', '.join(constraints['regions'])}")

    return "\n".join(formatted) if formatted else "No explicit constraints provided."


def _extract_cost_summary(cost_estimate: str) -> dict[str, Any]:
    """
    Extract cost summary from cost estimate text.

    Looks for monthly, annual, and TCO values in the estimate.

    Args:
        cost_estimate: Cost estimate text from agent

    Returns:
        Dictionary with monthly_cost, annual_cost, tco_3_year
    """
    summary: dict[str, Any] = {
        "monthly_cost": None,
        "annual_cost": None,
        "tco_3_year": None,
        "currency": "USD",
        "region": "eastus",
    }

    # Extract monthly cost
    monthly_patterns = [
        r"\*\*Monthly\*\*[:\s]*\$?([\d,]+\.?\d*)",
        r"Monthly Cost[:\s]*\$?([\d,]+\.?\d*)",
        r"Total Monthly[:\s]*\$?([\d,]+\.?\d*)",
    ]

    summary["monthly_cost"] = _extract_cost_value(cost_estimate, monthly_patterns)

    # Extract annual cost
    annual_patterns = [
        r"\*\*Annual\*\*[:\s]*\$?([\d,]+\.?\d*)",
        r"Annual Cost[:\s]*\$?([\d,]+\.?\d*)",
        r"Total Annual[:\s]*\$?([\d,]+\.?\d*)",
    ]

    summary["annual_cost"] = _extract_cost_value(cost_estimate, annual_patterns)

    # Extract 3-year TCO
    tco_patterns = [
        r"\*\*3-Year TCO\*\*[:\s]*\$?([\d,]+\.?\d*)",
        r"3-Year TCO[:\s]*\$?([\d,]+\.?\d*)",
        r"Total 3-Year[:\s]*\$?([\d,]+\.?\d*)",
    ]

    summary["tco_3_year"] = _extract_cost_value(cost_estimate, tco_patterns)

    # If annual not found but monthly exists, calculate
    if summary["annual_cost"] is None and summary["monthly_cost"]:
        summary["annual_cost"] = summary["monthly_cost"] * 12

    # If TCO not found but annual exists, calculate
    if summary["tco_3_year"] is None and summary["annual_cost"]:
        summary["tco_3_year"] = summary["annual_cost"] * 3

    return summary


def _extract_cost_value(cost_estimate: str, patterns: list[str]) -> float | None:
    """Extract a numeric cost value matching the provided patterns."""
    for pattern in patterns:
        match = re.search(pattern, cost_estimate, re.IGNORECASE)
        if not match:
            continue
        value = _parse_cost_value(match.group(1))
        if value is not None:
            return value
    return None


def _parse_cost_value(value: str) -> float | None:
    """Parse a numeric cost value from a string, returning None on failure."""
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None
