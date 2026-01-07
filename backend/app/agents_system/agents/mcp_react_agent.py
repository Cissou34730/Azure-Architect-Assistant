"""
MCP-specialized ReAct agent (extracted module).
Handles external tool discovery, execution, and result interpretation using LangChain ReAct pattern.

Phase 2: Allows optional injection of LLM, tools, and prompt to enable orchestration control.
Falls back to internal initialization when not provided to preserve behavior.
"""

import logging
from typing import Optional, List
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.tools import BaseTool

from ..config.react_prompts import SYSTEM_PROMPT, REACT_TEMPLATE
from ..tools.mcp_tool import create_mcp_tools
from ..tools.kb_tool import create_kb_tools
from ...services.mcp.learn_mcp_client import MicrosoftLearnMCPClient

logger = logging.getLogger(__name__)


class MCPReActAgent:
    """
    ReAct agent specialized for Azure architecture assistance using MCP tools.

    Supports dependency injection for `llm`, `tools`, and `prompt` to enable orchestration-driven setup.
    If not provided, builds defaults internally (backward compatible).
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        mcp_client: Optional[MicrosoftLearnMCPClient] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_iterations: int = 8,
        max_execution_time: int = 60,
        verbose: bool = True,
        # Optional injected dependencies
        llm: Optional[ChatOpenAI] = None,
        tools: Optional[List[BaseTool]] = None,
        prompt: Optional[PromptTemplate] = None,
    ):
        self.openai_api_key = openai_api_key
        self.mcp_client = mcp_client
        self.model = model
        self.temperature = temperature
        self.max_iterations = max_iterations
        self.max_execution_time = max_execution_time
        self.verbose = verbose

        # Injected or to be initialized
        self.llm: Optional[ChatOpenAI] = llm
        self.tools: List[BaseTool] = tools or []
        self.prompt: Optional[PromptTemplate] = prompt
        self.agent_executor: Optional[AgentExecutor] = None

        logger.info(
            f"MCPReActAgent initialized (model={model}, temperature={temperature}, injected_llm={'yes' if llm else 'no'})"
        )

    async def initialize(self) -> None:
        """Initialize the agent components asynchronously. Must be called before use."""
        # Initialize LLM if not injected
        if self.llm is None:
            if not self.openai_api_key or not self.model:
                raise ValueError(
                    "LLM not injected and OpenAI credentials/model not provided"
                )
            self.llm = ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                openai_api_key=self.openai_api_key,
            )

        # Create tools if not injected
        if not self.tools:
            if not self.mcp_client:
                raise ValueError("MCP client required to build tools")
            mcp_tools = await create_mcp_tools(self.mcp_client)
            kb_tools = create_kb_tools()
            self.tools = [*mcp_tools, *kb_tools]
            logger.info(
                f"Initialized {len(self.tools)} tools: {[t.name for t in self.tools]}"
            )

        # Create prompt if not injected
        prompt = self.prompt or PromptTemplate(
            template=f"{SYSTEM_PROMPT}\n\n{REACT_TEMPLATE}",
            input_variables=["input", "agent_scratchpad"],
            partial_variables={
                "tools": "\n".join(
                    [f"{tool.name}: {tool.description}" for tool in self.tools]
                ),
                "tool_names": ", ".join([tool.name for tool in self.tools]),
            },
        )
        self.prompt = prompt

        # Custom parsing error handler to give LLM specific feedback
        def handle_parsing_error(error: Exception) -> str:
            error_msg = str(error)
            if "Missing 'Action:' after 'Thought:'" in error_msg:
                return (
                    "ERROR: You wrote 'Thought:' but did not follow it with 'Action:' or 'Final Answer:'. "
                    "You MUST write either:\n"
                    "Action: [tool_name]\nAction Input: [json]\n"
                    "OR\n"
                    "Final Answer: [your answer]\n"
                    "Please continue with the correct format."
                )
            return (
                f"Parsing error: {error_msg}. Please follow the exact format specified."
            )

        # Create ReAct agent and executor
        agent = create_react_agent(llm=self.llm, tools=self.tools, prompt=self.prompt)
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=self.verbose,
            max_iterations=self.max_iterations,
            max_execution_time=self.max_execution_time,
            handle_parsing_errors=handle_parsing_error,
            early_stopping_method="generate",
            return_intermediate_steps=True,
        )

        logger.info("MCPReActAgent initialization complete")

    async def execute(
        self, user_query: str, project_context: Optional[str] = None
    ) -> dict:
        if not self.agent_executor:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        logger.info(f"Executing agent on query: {user_query}")
        agent_input = {"input": user_query}
        if project_context:
            contextualized_query = f"""CURRENT PROJECT CONTEXT:
{project_context}

---

User Question: {user_query}

Please answer considering the project context above. If your answer clarifies or updates project requirements, mention what should be updated in the project state."""
            agent_input["input"] = contextualized_query

        try:
            result = await self.agent_executor.ainvoke(agent_input)
            return {
                "output": result.get("output", "No output generated"),
                "intermediate_steps": result.get("intermediate_steps", []),
                "success": True,
            }
        except Exception as e:
            err_text = str(e)
            hint = None
            if "max iterations" in err_text.lower():
                hint = "The agent reached its reasoning limit. Try asking a more specific question or I can increase limits further if needed."
            elif "exceeded time" in err_text.lower() or "timeout" in err_text.lower():
                hint = "The agent timed out while reasoning. Consider narrowing the query or I can raise the time limit."
            return {
                "output": f"I encountered an error while processing your query: {err_text}"
                + (f"\n\nTip: {hint}" if hint else ""),
                "intermediate_steps": [],
                "success": False,
                "error": err_text,
            }

    async def stream_execute(
        self, user_query: str, project_context: Optional[str] = None
    ):
        # TODO: Implement streaming with LangChain's streaming callbacks
        result = await self.execute(user_query, project_context)
        yield result
