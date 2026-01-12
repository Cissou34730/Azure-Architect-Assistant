"""
Graph-native agent execution using LangGraph ToolNode.

Phase 4: Replace LangChain AgentExecutor with LangGraph-native tool loop.
"""

import logging
from typing import Any, Dict, List, Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, END

from ...tools.mcp_tool import create_mcp_tools
from ...tools.kb_tool import create_kb_tools
from ...tools.aaa_candidate_tool import create_aaa_tools
from ...config.react_prompts import SYSTEM_PROMPT
from ...services.mcp.learn_mcp_client import MicrosoftLearnMCPClient
from config.settings import OpenAISettings
from ..state import GraphState, MAX_AGENT_ITERATIONS, MAX_EXECUTION_TIME_SECONDS

logger = logging.getLogger(__name__)


class AgentState(Dict):
    """State for graph-native agent loop."""
    messages: List[BaseMessage]
    iterations: int
    

async def create_graph_native_agent_node(
    mcp_client: MicrosoftLearnMCPClient,
    openai_settings: OpenAISettings,
) -> callable:
    """
    Create a graph-native agent node using LangGraph ToolNode.
    
    Phase 4: Replaces AgentExecutor with LangGraph tool loop.
    
    Args:
        mcp_client: MCP client for tool creation
        openai_settings: OpenAI configuration
        
    Returns:
        Async function that executes graph-native agent
    """
    # Create tools
    mcp_tools = await create_mcp_tools(mcp_client)
    kb_tools = create_kb_tools()
    aaa_tools = create_aaa_tools()
    tools: List[BaseTool] = [*mcp_tools, *kb_tools, *aaa_tools]
    
    # Create LLM with tools
    llm = ChatOpenAI(
        model=openai_settings.model,
        temperature=0.1,
        openai_api_key=openai_settings.api_key,
    ).bind_tools(tools)
    
    # Create tool node
    tool_node = ToolNode(tools)
    
    def should_continue(state: AgentState) -> Literal["tools", "end"]:
        """Decide whether to continue with tools or end."""
        messages = state["messages"]
        last_message = messages[-1]
        iterations = state.get("iterations", 0)
        
        # Check iteration limit
        if iterations >= MAX_AGENT_ITERATIONS:
            logger.warning(f"Reached max iterations: {MAX_AGENT_ITERATIONS}")
            return "end"
        
        # If LLM makes a tool call, continue
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        
        return "end"
    
    async def call_model(state: AgentState) -> Dict:
        """Call LLM with current messages."""
        messages = state["messages"]
        iterations = state.get("iterations", 0)
        
        response = await llm.ainvoke(messages)
        
        return {
            "messages": [response],
            "iterations": iterations + 1,
        }
    
    # Build agent graph
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {
        "tools": "tools",
        "end": END,
    })
    workflow.add_edge("tools", "agent")
    
    agent_graph = workflow.compile()
    
    async def execute_agent(state: GraphState) -> Dict[str, Any]:
        """Execute graph-native agent."""
        user_message = state["user_message"]
        context_summary = state.get("context_summary")
        
        try:
            # Build system message with context
            system_content = SYSTEM_PROMPT
            if context_summary:
                system_content += f"\n\n### Project Context:\n{context_summary}"
            
            # Initialize agent state
            initial_messages = [
                HumanMessage(content=f"{system_content}\n\n{user_message}")
            ]
            
            agent_state: AgentState = {
                "messages": initial_messages,
                "iterations": 0,
            }
            
            logger.info(f"Executing graph-native agent for message: {user_message[:100]}...")
            
            # Execute agent graph
            result_state = await agent_graph.ainvoke(agent_state)
            
            # Extract output and intermediate steps
            messages = result_state["messages"]
            agent_output = ""
            intermediate_steps = []
            
            for msg in messages:
                if isinstance(msg, AIMessage):
                    if msg.content:
                        agent_output = msg.content
                    # Capture tool calls as intermediate steps
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            intermediate_steps.append((
                                type('Action', (), {
                                    'tool': tool_call.get("name", ""),
                                    'tool_input': tool_call.get("args", {}),
                                })(),
                                ""  # Observation will come from ToolMessage
                            ))
                elif isinstance(msg, ToolMessage):
                    # Update observation in last step
                    if intermediate_steps:
                        action, _ = intermediate_steps[-1]
                        intermediate_steps[-1] = (action, msg.content)
            
            logger.info(
                f"Graph-native agent finished (iterations={result_state['iterations']}, "
                f"steps={len(intermediate_steps)})"
            )
            
            return {
                "agent_output": agent_output,
                "intermediate_steps": intermediate_steps,
                "success": True,
                "error": None,
            }
            
        except Exception as e:
            logger.error(f"Graph-native agent execution failed: {e}", exc_info=True)
            return {
                "agent_output": "",
                "intermediate_steps": [],
                "success": False,
                "error": f"Agent execution failed: {str(e)}",
            }
    
    return execute_agent
