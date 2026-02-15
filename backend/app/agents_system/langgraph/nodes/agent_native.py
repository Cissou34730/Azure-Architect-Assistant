"""
Stage-aware LangGraph-native agent execution using ToolNode.

Uses MCP + KB + AAA tools with explicit directives to research,
cite sources, and avoid pushback.
"""

import logging
from typing import Annotated, Any, Literal, TypedDict, cast

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool, Tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, add_messages
from langgraph.prebuilt import ToolNode

from config.settings import OpenAISettings

from ....services.mcp.learn_mcp_client import MicrosoftLearnMCPClient
from ...config.react_prompts import SYSTEM_PROMPT
from ...tools.aaa_candidate_tool import create_aaa_tools
from ...tools.kb_tool import create_kb_tools
from ...tools.mcp_tool import create_mcp_tools
from ...tools.tool_wrappers import make_single_input_wrapper
from ..state import MAX_AGENT_ITERATIONS, GraphState

logger = logging.getLogger(__name__)

DISCOVERY_STAGES = {"clarify", "propose_candidate"}
VALIDATION_STAGES = {"validate"}


class AgentState(TypedDict):
    """State for graph-native agent loop."""

    messages: Annotated[list[BaseMessage], add_messages]
    iterations: int


def _format_mindmap_gaps(coverage: Any) -> str:
    topics = []
    cov_topics = (coverage or {}).get("topics", {}) if isinstance(coverage, dict) else {}
    if isinstance(cov_topics, dict):
        for key, val in cov_topics.items():
            if isinstance(val, dict) and val.get("status") == "not-addressed":
                topics.append(key)
    return ", ".join(topics[:5]) if topics else ""


def _mindmap_guidance_section(mindmap_guidance: Any) -> str:
    if not isinstance(mindmap_guidance, dict):
        return ""

    prompts = mindmap_guidance.get("suggested_prompts")
    focus_topics = mindmap_guidance.get("focus_topics")

    lines: list[str] = []
    if isinstance(focus_topics, list) and focus_topics:
        topics = ", ".join(str(topic) for topic in focus_topics[:5])
        lines.append(f"Focus topics: {topics}")

    if isinstance(prompts, list) and prompts:
        lines.extend(f"- {prompt!s}" for prompt in prompts[:2])

    if not lines:
        return ""

    return "### Mind map advisory guidance\n" + "\n".join(lines)


def _stage_policy_notes(stage_value: str) -> str:
    if stage_value in VALIDATION_STAGES:
        return (
            "Validation stage policy: WAF checklist persistence and evidence capture take precedence over mind map exploration. "
            "Mind map prompts remain advisory."
        )
    if stage_value in DISCOVERY_STAGES:
        return (
            "Discovery stage policy: prioritize mind map prompts to uncover weak spots, while keeping all guidance non-blocking."
        )
    return (
        "Balanced stage policy: keep WAF and mind map guidance aligned without blocking the conversation flow."
    )


def _build_system_directives(state: GraphState) -> str:
    directives = [SYSTEM_PROMPT]
    stage_value = str(state.get("next_stage") or "clarify")

    specialist = state.get("selected_specialist") or state.get("specialist_used")
    if specialist:
        directives.append(f"### Specialist focus\nOperate as {specialist.replace('_', ' ')} and keep the scope tight.")

    stage_text = state.get("stage_directives")
    research_plan = state.get("research_plan") or []
    mindmap_guidance_text = _mindmap_guidance_section(state.get("mindmap_guidance"))

    if stage_value in DISCOVERY_STAGES:
        if mindmap_guidance_text:
            directives.append(mindmap_guidance_text)
        if stage_text:
            directives.append(f"### Stage directives\n{stage_text}")
    else:
        if stage_text:
            directives.append(f"### Stage directives\n{stage_text}")
        if mindmap_guidance_text:
            directives.append(mindmap_guidance_text)

    if research_plan:
        directives.append(
            "### Research plan (run MCP searches/fetches for these)\n"
            + "\n".join([f"- {item}" for item in research_plan])
        )

    mindmap_cov = state.get("mindmap_coverage")
    gaps = _format_mindmap_gaps(mindmap_cov) if mindmap_cov else ""
    if gaps:
        directives.append(f"### Mind map gaps to cover\n{gaps}")

    directives.append(f"### Guidance precedence\n{_stage_policy_notes(stage_value)}")

    directives.append(
        "### Behavioral guardrails\n"
        "- Always call MCP tools for at least one search and one fetch before final answer.\n"
        "- Cite Azure/WAF/ASB sources with names and URLs; include mind map node ids when adding artifacts.\n"
        "- Mind map guidance is advisory-only and must not enforce a rigid workflow.\n"
        "- In validation turns, checklist status updates and persistence rules take priority over exploratory prompts.\n"
        "- Challenge assumptions: If a user choice contradicts Azure WAF best practices or NFRs, you MUST explain the risk and offer alternatives.\n"
        "- Treat WAF checklist as first-class: when analysis supports a status change, proactively persist checklist updates (covered/partial/notCovered) without waiting for explicit user wording.\n"
        "- If evidence is insufficient for a status change, ask a focused status/evidence clarification and propose the next checklist completion step.\n"
        "- Persist decisions: Whenever a design choice is made, use the appropriate AAA tool and include the 'AAA_STATE_UPDATE' block in your response to confirm it reached the system.\n"
        "- Proactive driving: Drive the project forward. If requirements are clear, propose the architecture; if architecture is clear, move to ADRs."
    )

    context_summary = state.get("context_summary")
    if context_summary:
        directives.append(f"### Project context (read-only)\n{context_summary}")

    return "\n\n".join(directives)


def _normalize_tool(tool: Any) -> BaseTool | None:
    """Normalize a tool-like object into a LangChain BaseTool."""
    if isinstance(tool, BaseTool):
        return tool

    name = getattr(tool, "name", None) or getattr(tool, "__name__", None)
    if not name:
        return None

    desc = getattr(tool, "description", "")
    sync_fn = getattr(tool, "run", None)
    if sync_fn is None and callable(tool):
        sync_fn = tool

    async_fn = getattr(tool, "arun", None) or getattr(tool, "ainvoke", None)

    if sync_fn is None and async_fn is None:
        return None

    sync_wrapped, async_wrapped = make_single_input_wrapper(
        name, sync_fn or async_fn, async_fn
    )
    return Tool(
        name=name,
        func=sync_wrapped,
        coroutine=async_wrapped,
        description=desc,
    )


async def _build_tools(mcp_client: MicrosoftLearnMCPClient) -> list[BaseTool]:
    """Build a list of tools safe for ChatOpenAI.bind_tools + ToolNode."""
    mcp_tools = await create_mcp_tools(mcp_client)
    kb_tools_any = create_kb_tools()
    aaa_tools = create_aaa_tools()

    tools_any: list[Any] = [*mcp_tools, *kb_tools_any, *aaa_tools]
    normalized: list[BaseTool] = []

    for t in tools_any:
        tool = _normalize_tool(t)
        if tool:
            normalized.append(tool)

    return normalized


async def run_stage_aware_agent(
    state: GraphState,
    *,
    mcp_client: MicrosoftLearnMCPClient,
    openai_settings: OpenAISettings,
) -> dict[str, Any]:
    """Execute a stage-aware agent using LangGraph ToolNode."""
    if mcp_client is None or openai_settings is None:
        raise RuntimeError("Missing MCP client or OpenAI settings for agent execution")

    user_message = state["user_message"]
    system_directives = _build_system_directives(state)
    tools = await _build_tools(mcp_client)

    base_llm = ChatOpenAI(
        model=openai_settings.model,
        temperature=0.1,
        openai_api_key=openai_settings.api_key,
    )
    llm = base_llm.bind_tools(tools)

    agent_graph = _compile_agent_graph(llm, tools, base_llm)

    agent_initial_state: AgentState = {
        "messages": [
            SystemMessage(content=system_directives),
            HumanMessage(content=user_message),
        ],
        "iterations": 0,
    }

    logger.info("Running stage-aware native agent")
    result_state = cast(dict[str, Any], await agent_graph.ainvoke(agent_initial_state))

    return _parse_agent_results(result_state)


def _compile_agent_graph(llm: Any, tools: list[BaseTool], final_llm: Any) -> Any:
    """Helper to build and compile the internal agent graph."""
    tool_node = ToolNode(tools)
    final_directive = (
        "Tool iteration budget reached. Provide the best possible final answer now "
        "using the information already in the conversation and tool outputs. "
        "Do NOT call any tools. If key information is missing, ask up to 5 focused "
        "clarifying questions and propose the next concrete step."
    )

    def should_continue(agent_state: AgentState) -> Literal["tools", "final", "end"]:
        messages = agent_state["messages"]
        last_message = messages[-1]
        iterations = agent_state.get("iterations", 0)

        if iterations >= MAX_AGENT_ITERATIONS:
            logger.warning("Reached max iterations in native agent loop")
            return "final"

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "end"

    async def call_model(agent_state: AgentState) -> dict[str, Any]:
        messages = agent_state["messages"]
        iterations = agent_state.get("iterations", 0)
        response = await llm.ainvoke(messages)
        return {"messages": [response], "iterations": iterations + 1}

    async def call_final(agent_state: AgentState) -> dict[str, Any]:
        messages = agent_state["messages"]
        iterations = agent_state.get("iterations", 0)
        final_messages = [*messages, SystemMessage(content=final_directive)]
        response = await final_llm.ainvoke(final_messages)
        return {"messages": [response], "iterations": iterations + 1}

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    workflow.add_node("final", call_final)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "final": "final",
            "end": END,
        },
    )
    workflow.add_edge("tools", "agent")
    workflow.add_edge("final", END)
    return workflow.compile()


def _parse_agent_results(result_state: dict[str, Any]) -> dict[str, Any]:
    """Extract output and intermediate steps from the finished agent state."""
    messages = result_state.get("messages", [])
    agent_output = ""
    intermediate_steps = []

    for msg in messages:
        if isinstance(msg, AIMessage):
            if isinstance(msg.content, str) and msg.content:
                agent_output = msg.content
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    # Capture tool call details in a format compatible with AgentFacade
                    action = type(
                        "Action",
                        (),
                        {
                            "tool": tool_call.get("name", ""),
                            "tool_input": tool_call.get("args", {}),
                        },
                    )()
                    intermediate_steps.append((action, ""))
        elif isinstance(msg, ToolMessage):
            if intermediate_steps:
                action, _ = intermediate_steps[-1]
                intermediate_steps[-1] = (action, msg.content)

    return {
        "agent_output": agent_output,
        "intermediate_steps": intermediate_steps,
        "success": True,
        "error": None,
    }

