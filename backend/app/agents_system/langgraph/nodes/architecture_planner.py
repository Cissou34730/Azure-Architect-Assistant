"""
Architecture Planner Node - Specialized agent for architecture design.

This module provides a specialized sub-agent for handling complex architecture
design requests with NFR analysis and diagram generation.
"""

import logging
from typing import Any

from app.agents_system.agents.mcp_react_agent import MCPReActAgent
from app.agents_system.config.prompt_loader import PromptLoader
from app.agents_system.tools.aaa_candidate_tool import create_aaa_tools

from ..state import GraphState

logger = logging.getLogger(__name__)


async def architecture_planner_node(state: GraphState) -> dict[str, Any]:
    """
    Specialized node for architecture planning and diagram generation.

    This node is invoked when:
    - User requests architecture proposal
    - Project stage is "propose_candidate"
    - Complexity threshold exceeded

    The Architecture Planner specializes in:
    - Target architecture design (complete, production-ready)
    - NFR analysis (Scalability, Performance, Security, Reliability, Maintainability)
    - C4 model diagrams (System Context, Container)
    - Functional flow diagrams (user journeys, business processes)
    - Phased delivery planning (MVP when requested)

    Args:
        state: Current graph state with project context

    Returns:
        Updated state with architecture proposal
    """
    logger.info("🏗️ Architecture Planner Agent activated")

    try:
        # Load architecture planner prompt
        prompt_loader = PromptLoader()
        arch_planner_prompt = prompt_loader.load_prompt("architecture_planner_prompt.yaml")

        # Prepare handoff context for architecture planner
        handoff_context = state.get("agent_handoff_context", {})
        project_context = handoff_context.get("project_context", "")
        requirements = handoff_context.get("requirements", "")
        nfr_summary = handoff_context.get("nfr_summary", "")
        constraints = handoff_context.get("constraints", {})
        previous_decisions = handoff_context.get("previous_decisions", [])

        # Get user's original request
        user_message = state.get("user_message", "")

        # Construct comprehensive input for architecture planner
        arch_planner_input = f"""
{user_message}

**Context from Main Agent:**

**Project Context:**
{project_context}

**Requirements:**
{requirements}

**Non-Functional Requirements (NFR):**
{nfr_summary}

**Constraints:**
{_format_constraints(constraints)}

**Previous Architectural Decisions (ADRs):**
{_format_previous_decisions(previous_decisions)}

---

**Task:** Design the complete target architecture for this project. Include:

1. **Target Architecture Design** (complete, production-ready)
2. **System Context Diagram** [Target Architecture]
3. **Container Diagram** [Target Architecture]
4. **User Journey Flow** (if user-facing system)
5. **NFR Analysis** for each diagram (Scalability, Performance, Security, Reliability, Maintainability, Trade-offs)
6. After presenting target, ask if user wants MVP path

Ensure all diagrams use valid Mermaid syntax and include comprehensive NFR analysis.
"""

        # Create architecture planner agent with specialized prompt
        # Note: We use GPT-4 for complex architectural reasoning
        arch_agent = MCPReActAgent(
            system_prompt=arch_planner_prompt["system_prompt"],
            react_template=arch_planner_prompt["react_template"],
            tools=create_aaa_tools(state),  # Reuse AAA tools
            model_name="gpt-4o",  # More capable model for complex reasoning
            temperature=0.1,  # Low temperature for consistency
        )

        logger.info("Architecture Planner agent initialized, invoking...")

        # Invoke architecture planner agent
        result = await arch_agent.ainvoke({
            "input": arch_planner_input,
            "context": project_context,
        })

        arch_proposal = result.get("output", "")
        intermediate_steps = result.get("intermediate_steps", [])

        logger.info(f"✅ Architecture Planner completed with {len(intermediate_steps)} tool calls")

        return {
            "agent_output": arch_proposal,
            "intermediate_steps": state.get("intermediate_steps", []) + intermediate_steps,
            "current_agent": "architecture_planner",
            "sub_agent_output": arch_proposal,
            "success": True,
            "error": None,
        }

    except Exception as exc:
        logger.error(f"❌ Architecture Planner failed: {exc}", exc_info=True)

        # Graceful fallback: Return error but don't break the workflow
        error_msg = (
            f"Architecture Planner encountered an error: {exc!s}\n\n"
            "Falling back to main agent for architecture planning. "
            "The main agent will provide a best-effort architecture proposal."
        )

        return {
            "agent_output": error_msg,
            "current_agent": "main",  # Fallback to main agent
            "sub_agent_output": None,
            "success": False,
            "error": str(exc),
        }


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


def _format_previous_decisions(decisions: list[dict[str, Any]]) -> str:
    """Format previous ADRs for display."""
    if not decisions:
        return "No previous architectural decisions recorded."

    formatted = []
    for idx, decision in enumerate(decisions, 1):
        title = decision.get("title", "Untitled Decision")
        rationale = decision.get("rationale", "No rationale provided")
        formatted.append(f"{idx}. **{title}**\n   Rationale: {rationale}")

