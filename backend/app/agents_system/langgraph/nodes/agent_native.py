"""
Stage-aware LangGraph-native agent execution using ToolNode.

Uses MCP + KB + AAA tools with explicit directives to research,
cite sources, and avoid pushback.
"""

import logging
from typing import Any, Dict, List, Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    BaseMessage,
)
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from ...langchain.facade_utils import make_single_input_wrapper

from ...tools.mcp_tool import create_mcp_tools
from ...tools.kb_tool import create_kb_tools
from ...tools.aaa_candidate_tool import create_aaa_tools
from ...config.react_prompts import SYSTEM_PROMPT
from ....services.mcp.learn_mcp_client import MicrosoftLearnMCPClient
from config.settings import OpenAISettings
from ..state import GraphState, MAX_AGENT_ITERATIONS

logger = logging.getLogger(__name__)


class AgentState(Dict):
    """State for graph-native agent loop."""

    messages: List[BaseMessage]
    iterations: int


def _format_mindmap_gaps(coverage: Dict[str, Any]) -> str:
    topics = []
    cov_topics = (coverage or {}).get("topics", {}) if isinstance(coverage, dict) else {}
    if isinstance(cov_topics, dict):
        for key, val in cov_topics.items():
            if (val or {}).get("status") == "not-addressed":
                topics.append(key)
    return ", ".join(topics[:5]) if topics else ""


def _build_system_directives(state: GraphState) -> str:
    directives = [SYSTEM_PROMPT]

    specialist = state.get("selected_specialist") or state.get("specialist_used")
    if specialist:
        directives.append(f"### Specialist focus\nOperate as {specialist.replace('_', ' ')} and keep the scope tight.")

    stage_text = state.get("stage_directives")
    if stage_text:
        directives.append(f"### Stage directives\n{stage_text}")

    research_plan = state.get("research_plan") or []
    if research_plan:
        directives.append(
            "### Research plan (run MCP searches/fetches for these)\n"
            + "\n".join([f"- {item}" for item in research_plan])
        )

    mindmap_cov = state.get("mindmap_coverage")
    gaps = _format_mindmap_gaps(mindmap_cov) if mindmap_cov else ""
    if gaps:
        directives.append(f"### Mind map gaps to cover\n{gaps}")

    directives.append(
        "### Behavioral guardrails\n"
        "- Always call MCP tools for at least one search and one fetch before final answer.\n"
        "- Cite Azure/WAF/ASB sources with names and URLs; include mind map node ids when adding artifacts.\n"
        "- Challenge assumptions: If a user choice contradicts Azure WAF best practices or NFRs, you MUST explain the risk and offer alternatives.\n"
        "- Persist decisions: Whenever a design choice is made, use the appropriate AAA tool and include the 'AAA_STATE_UPDATE' block in your response to confirm it reached the system.\n"
        "- Proactive driving: Drive the project forward. If requirements are clear, propose the architecture; if architecture is clear, move to ADRs."
    )

    context_summary = state.get("context_summary")
    if context_summary:
        directives.append(f"### Project context (read-only)\n{context_summary}")

    return "\n\n".join(directives)


async def _build_tools(mcp_client: MicrosoftLearnMCPClient) -> List[BaseTool]:
    """Build a list of tools safe for ChatOpenAI.bind_tools + ToolNode.

    Some factories return lightweight wrappers for testability (e.g. kb_search).
    LangGraph's native ToolNode requires real BaseTool instances, so we normalize
    any legacy wrappers into proper Tool objects.
    """
    from langchain.tools import Tool as LcTool

    mcp_tools = await create_mcp_tools(mcp_client)
    kb_tools_any = create_kb_tools()
    aaa_tools = create_aaa_tools()

    tools_any = [*mcp_tools, *kb_tools_any, *aaa_tools]
    normalized: List[BaseTool] = []

    for t in tools_any:
        if isinstance(t, BaseTool):
            normalized.append(t)
            continue

        name = getattr(t, "name", None) or getattr(t, "__name__", None)
        desc = getattr(t, "description", "")
        sync_fn = getattr(t, "run", None) or getattr(t, "__call__", None)
        async_fn = getattr(t, "arun", None) or getattr(t, "ainvoke", None)
        if not name or (sync_fn is None and async_fn is None):
            continue

        sync_wrapped, async_wrapped = make_single_input_wrapper(name, sync_fn or async_fn, async_fn)
        normalized.append(
            LcTool(
                name=name,
                func=sync_wrapped,
                coroutine=async_wrapped,
                description=desc,
            )
        )

    return normalized


async def run_stage_aware_agent(
    state: GraphState,
    *,
    mcp_client: MicrosoftLearnMCPClient,
    openai_settings: OpenAISettings,
) -> Dict[str, Any]:
    """
    Execute a stage-aware agent using LangGraph ToolNode.
    """
    if mcp_client is None or openai_settings is None:
        raise RuntimeError("Missing MCP client or OpenAI settings for agent execution")

    user_message = state["user_message"]
    system_directives = _build_system_directives(state)

    tools = await _build_tools(mcp_client)
    llm = ChatOpenAI(
        model=openai_settings.model,
        temperature=0.1,
        openai_api_key=openai_settings.api_key,
    ).bind_tools(tools)

    tool_node = ToolNode(tools)

    def should_continue(agent_state: AgentState) -> Literal["tools", "end"]:
        messages = agent_state["messages"]
        last_message = messages[-1]
        iterations = agent_state.get("iterations", 0)

        if iterations >= MAX_AGENT_ITERATIONS:
            logger.warning("Reached max iterations in native agent loop")
            return "end"

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "end"

    async def call_model(agent_state: AgentState) -> Dict[str, Any]:
        messages = agent_state["messages"]
        iterations = agent_state.get("iterations", 0)
        response = await llm.ainvoke(messages)
        return {"messages": [response], "iterations": iterations + 1}

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )
    workflow.add_edge("tools", "agent")
    agent_graph = workflow.compile()

    initial_messages: List[BaseMessage] = [
        SystemMessage(content=system_directives),
        HumanMessage(content=user_message),
    ]
    agent_state: AgentState = {"messages": initial_messages, "iterations": 0}

    logger.info("Running stage-aware native agent")
    result_state = await agent_graph.ainvoke(agent_state)

    # Extract output and intermediate steps
    messages = result_state["messages"]
    agent_output = ""
    intermediate_steps = []

    for msg in messages:
        if isinstance(msg, AIMessage):
            if msg.content:
                agent_output = msg.content
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    intermediate_steps.append(
                        (
                            type(
                                "Action",
                                (),
                                {
                                    "tool": tool_call.get("name", ""),
                                    "tool_input": tool_call.get("args", {}),
                                },
                            )(),
                            "",
                        )
                    )
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
