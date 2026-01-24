"""
SaaS Advisor Node - Specialized agent for multi-tenant SaaS architectures.

This module provides a specialized sub-agent for handling SaaS-specific
architecture requests with tenant isolation, B2B/B2C patterns, and scaling strategies.
"""

import logging
from typing import Any

from app.agents_system.agents.mcp_react_agent import MCPReActAgent
from app.agents_system.config.prompt_loader import PromptLoader
from app.agents_system.tools.create_tools import create_aaa_tools

from ..state import GraphState

logger = logging.getLogger(__name__)


async def saas_advisor_node(state: GraphState) -> dict[str, Any]:
    """
    Specialized node for SaaS architecture design.

    This node is invoked ONLY when:
    - User explicitly mentions SaaS, multi-tenant, B2B/B2C keywords
    - User asks "should this be SaaS?" or similar suitability questions

    The SaaS Advisor specializes in:
    - Tenant architecture models (Silo, Pool, Bridge)
    - Tenant isolation strategies (data, compute, network)
    - B2B vs B2C SaaS patterns
    - Noisy neighbor mitigation
    - Deployment stamps for regional scaling
    - SaaS operational considerations (onboarding, billing, monitoring)
    - Cost analysis per tenant model

    Args:
        state: Current graph state with project context

    Returns:
        Updated state with SaaS architecture proposal
    """
    logger.info("🏢 SaaS Advisor Agent activated")

    try:
        # Load SaaS advisor prompt
        prompt_loader = PromptLoader()
        saas_prompt = prompt_loader.load_prompt("saas_advisor_prompt.yaml")

        # Prepare handoff context for SaaS advisor
        handoff_context = state.get("agent_handoff_context", {})
        project_context = handoff_context.get("project_context", "")
        requirements = handoff_context.get("requirements", "")
        current_architecture = handoff_context.get("current_architecture", "")
        tenant_requirements = handoff_context.get("tenant_requirements", {})
        constraints = handoff_context.get("constraints", {})

        # Get user's original request
        user_message = state.get("user_message", "")

        # Construct comprehensive input for SaaS advisor
        saas_advisor_input = f"""
{user_message}

**Context from Main Agent:**

**Project Context:**
{project_context}

**Requirements:**
{requirements}

**Current Architecture (if exists):**
{current_architecture if current_architecture else "No architecture designed yet."}

**Tenant Requirements:**
{_format_tenant_requirements(tenant_requirements)}

**Constraints:**
{_format_constraints(constraints)}

---

**Task:** Design a comprehensive SaaS architecture for this project. Include:

1. **Tenant Architecture Model** (Silo, Pool, or Bridge) with justification
2. **Tenant Isolation Strategy** (data, compute, network layers)
3. **B2B or B2C Specific Patterns** (authentication, onboarding, billing)
4. **Noisy Neighbor Mitigation Plan** (rate limiting, quotas, monitoring)
5. **Scaling Strategy** (deployment stamps if needed)
6. **Operational Considerations** (tenant onboarding, monitoring, billing)
7. **Cost Analysis** (per-tenant cost, suggested pricing, margins)
8. **Architecture Decision Record (ADR)** documenting SaaS model choice

Ensure the proposal addresses all SaaS-specific concerns and provides clear implementation guidance.
"""

        # Create SaaS advisor agent with specialized prompt
        saas_agent = MCPReActAgent(
            system_prompt=saas_prompt["system_prompt"],
            react_template=saas_prompt.get("react_template", ""),
            tools=create_aaa_tools(state),  # Reuse AAA tools
            model_name="gpt-4o",  # Use GPT-4 for complex SaaS reasoning
            temperature=0.1,  # Low temperature for consistency
        )

        logger.info("SaaS Advisor agent initialized, invoking...")

        # Invoke SaaS advisor agent
        result = await saas_agent.ainvoke({
            "input": saas_advisor_input,
            "context": project_context,
        })

        saas_proposal = result.get("output", "")
        intermediate_steps = result.get("intermediate_steps", [])

        logger.info(f"✅ SaaS Advisor completed with {len(intermediate_steps)} tool calls")

        return {
            "agent_output": saas_proposal,
            "intermediate_steps": state.get("intermediate_steps", []) + intermediate_steps,
            "current_agent": "saas_advisor",
            "sub_agent_output": saas_proposal,
            "saas_context": {
                "tenant_model": _extract_tenant_model(saas_proposal),
                "customer_type": tenant_requirements.get("customer_type", "unknown"),
                "activation_reason": "explicit_saas_request",
            },
            "success": True,
            "error": None,
        }

    except Exception as exc:
        logger.error(f"❌ SaaS Advisor failed: {exc}", exc_info=True)

        # Graceful fallback: Return error but don't break the workflow
        error_msg = (
            f"SaaS Advisor encountered an error: {exc!s}\n\n"
            "Falling back to main agent for SaaS architecture guidance. "
            "The main agent will provide best-effort SaaS recommendations."
        )

        return {
            "agent_output": error_msg,
            "current_agent": "main",  # Fallback to main agent
            "sub_agent_output": None,
            "saas_context": None,
            "success": False,
            "error": str(exc),
        }


def _format_tenant_requirements(tenant_reqs: dict[str, Any]) -> str:
    """Format tenant requirements for display."""
    if not tenant_reqs:
        return "No explicit tenant requirements provided. Please specify tenant model, expected count, and isolation needs."

    formatted = []
    if "expected_tenants" in tenant_reqs:
        formatted.append(f"- Expected Tenants: {tenant_reqs['expected_tenants']}")
    if "customer_type" in tenant_reqs:
        formatted.append(f"- Customer Type: {tenant_reqs['customer_type']}")
    if "isolation_level" in tenant_reqs:
        formatted.append(f"- Isolation Level: {tenant_reqs['isolation_level']}")
    if "compliance" in tenant_reqs:
        formatted.append(f"- Compliance: {', '.join(tenant_reqs['compliance'])}")
    if "tenant_tiers" in tenant_reqs:
        formatted.append(f"- Tenant Tiers: {', '.join(tenant_reqs['tenant_tiers'])}")

    return "\n".join(formatted) if formatted else "No explicit tenant requirements provided."


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
    if "excluded_services" in constraints:
        formatted.append(f"- Excluded Services: {', '.join(constraints['excluded_services'])}")

    return "\n".join(formatted) if formatted else "No explicit constraints provided."


def _extract_tenant_model(proposal: str) -> str:
    """
    Extract tenant model from SaaS proposal.

    Looks for keywords: Silo, Pool, Bridge in the proposal text.

    Args:
        proposal: SaaS architecture proposal text

    Returns:
        Tenant model: "silo", "pool", "bridge", or "unknown"
    """
    proposal_lower = proposal.lower()

    if "silo" in proposal_lower and "model" in proposal_lower:
        return "silo"
    if "pool" in proposal_lower and "model" in proposal_lower:
        return "pool"
    if "bridge" in proposal_lower and "model" in proposal_lower:
        return "bridge"

    # Fallback heuristics
    if "dedicated" in proposal_lower and "per tenant" in proposal_lower:
        return "silo"
    if "shared" in proposal_lower and "resources" in proposal_lower:
        return "pool"

    return "unknown"
