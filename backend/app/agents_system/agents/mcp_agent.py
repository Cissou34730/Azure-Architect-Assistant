"""
MCP-specialized agent.
Handles external tool discovery, execution, and result interpretation using LangChain ReAct pattern.
"""

import logging
from typing import Optional
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
    
    This agent:
    - Uses ReAct (Reasoning + Acting) pattern for tool orchestration
    - Queries Microsoft documentation via MCP tools
    - Provides architectural guidance aligned with Azure Well-Architected Framework
    - Never relies on assumptions - always grounds responses in official docs
    """
    
    def __init__(
        self,
        openai_api_key: str,
        mcp_client: MicrosoftLearnMCPClient,
        model: str,
        temperature: float = 0.1,
        max_iterations: int = 8,  # allow more tool calls before final answer
        max_execution_time: int = 60,  # seconds
        verbose: bool = True,
    ):
        """
        Initialize the MCP ReAct Agent.
        
        Args:
            openai_api_key: OpenAI API key for LLM
            mcp_client: Initialized MicrosoftLearnMCPClient for tool access
            model: OpenAI model to use
            temperature: Model temperature for response generation (default: 0.1 for consistency)
            max_iterations: Maximum ReAct iterations (default: 8 for more complex queries)
            max_execution_time: Maximum total execution time in seconds (default: 60)
            verbose: Enable detailed logging (default: True)
        """
        self.openai_api_key = openai_api_key
        self.mcp_client = mcp_client
        self.model = model
        self.temperature = temperature
        self.max_iterations = max_iterations
        self.max_execution_time = max_execution_time
        self.verbose = verbose
        
        # Initialize components
        self.llm: Optional[ChatOpenAI] = None
        self.tools: list[BaseTool] = []
        self.agent_executor: Optional[AgentExecutor] = None
        
        logger.info(f"MCPReActAgent initialized with model={model}, temperature={temperature}")
    
    async def initialize(self) -> None:
        """
        Initialize the agent components asynchronously.
        Must be called before using the agent.
        """
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            openai_api_key=self.openai_api_key,
        )
        
        # Create MCP tools
        self.tools = await create_mcp_tools(self.mcp_client)
        # Add KB/RAG tools (internal service wrappers)
        self.tools.extend(create_kb_tools())
        logger.info(f"Initialized {len(self.tools)} tools: {[t.name for t in self.tools]}")
        
        # Create ReAct prompt template
        prompt = PromptTemplate(
            template=f"{SYSTEM_PROMPT}\n\n{REACT_TEMPLATE}",
            input_variables=["input", "agent_scratchpad"],
            partial_variables={
                "tools": "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools]),
                "tool_names": ", ".join([tool.name for tool in self.tools]),
            },
        )
        
        # Custom parsing error handler to give LLM specific feedback
        def handle_parsing_error(error: Exception) -> str:
            """Provide clear guidance when LLM violates ReAct format."""
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
            return f"Parsing error: {error_msg}. Please follow the exact format specified."
        
        # Create ReAct agent
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt,
        )
        
        # Create agent executor
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=self.verbose,
            max_iterations=self.max_iterations,
            max_execution_time=self.max_execution_time,
            handle_parsing_errors=handle_parsing_error,
            return_intermediate_steps=True,
        )
        
        logger.info("MCPReActAgent initialization complete")
    
    async def execute(self, user_query: str, project_context: Optional[str] = None) -> dict:
        """
        Execute the agent on a user query.
        
        Args:
            user_query: User's architectural question or requirement
            project_context: Optional formatted project context to inject into prompt
            
        Returns:
            Dictionary with:
                - output: Final answer from the agent
                - intermediate_steps: List of (action, observation) tuples showing reasoning
                - success: Whether execution completed successfully
                
        Example:
            ```python
            agent = MCPReActAgent(api_key, mcp_client)
            await agent.initialize()
            
            result = await agent.execute("How do I secure Azure SQL Database?")
            print(result["output"])
            ```
        """
        if not self.agent_executor:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        
        logger.info(f"Executing agent on query: {user_query}")
        
        # Build input with optional project context
        agent_input = {"input": user_query}
        
        # If project context provided, prepend to query for context awareness
        if project_context:
            contextualized_query = f"""CURRENT PROJECT CONTEXT:
{project_context}

---

User Question: {user_query}

Please answer considering the project context above. If your answer clarifies or updates project requirements, mention what should be updated in the project state."""
            agent_input["input"] = contextualized_query
            logger.debug(f"Added project context to query")
        
        try:
            # Execute the agent
            result = await self.agent_executor.ainvoke(agent_input)
            
            logger.info(f"Agent execution completed")
            logger.debug(f"Intermediate steps: {len(result.get('intermediate_steps', []))}")
            
            return {
                "output": result.get("output", "No output generated"),
                "intermediate_steps": result.get("intermediate_steps", []),
                "success": True,
            }
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            err_text = str(e)
            hint = None
            if "max iterations" in err_text.lower():
                hint = "The agent reached its reasoning limit. Try asking a more specific question or I can increase limits further if needed."
            elif "exceeded time" in err_text.lower() or "timeout" in err_text.lower():
                hint = "The agent timed out while reasoning. Consider narrowing the query or I can raise the time limit."
            return {
                "output": f"I encountered an error while processing your query: {err_text}" + (f"\n\nTip: {hint}" if hint else ""),
                "intermediate_steps": [],
                "success": False,
                "error": err_text,
            }
    
    async def stream_execute(self, user_query: str, project_context: Optional[str] = None):
        """
        Execute the agent with streaming output (for future implementation).
        
        Args:
            user_query: User's architectural question
            project_context: Optional formatted project context
            
        Yields:
            Chunks of the agent's response as they're generated
        """
        # TODO: Implement streaming with LangChain's streaming callbacks
        # For now, just return the full result
        result = await self.execute(user_query, project_context)
        yield result
