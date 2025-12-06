"""
Agent router.
FastAPI router for agent chat endpoints and request handling.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..runner import get_agent_runner

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/agent", tags=["agent"])


# Request/Response models
class ChatMessage(BaseModel):
    """Single chat message."""
    role: str = Field(description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(description="Message content")


class AgentChatRequest(BaseModel):
    """Request for agent chat endpoint."""
    message: str = Field(description="User's question or requirement")
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Optional conversation history for context (not yet implemented)"
    )


class AgentStep(BaseModel):
    """Single reasoning step from the agent."""
    action: str = Field(description="Tool or action taken")
    action_input: str = Field(description="Input to the action")
    observation: str = Field(description="Result from the action")


class AgentChatResponse(BaseModel):
    """Response from agent chat endpoint."""
    answer: str = Field(description="Agent's final answer")
    success: bool = Field(description="Whether execution was successful")
    reasoning_steps: List[AgentStep] = Field(
        default=[],
        description="Agent's reasoning steps (Thought/Action/Observation)"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")


class AgentHealthResponse(BaseModel):
    """Agent system health status."""
    status: str = Field(description="Health status: 'healthy', 'degraded', 'unhealthy'")
    mcp_client_connected: bool
    openai_configured: bool


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agent(request: AgentChatRequest) -> AgentChatResponse:
    """
    Chat with the Azure Architect Assistant agent.
    
    The agent uses ReAct reasoning to:
    1. Understand your architectural question
    2. Search Microsoft documentation for authoritative guidance
    3. Fetch detailed documentation when needed
    4. Find code examples and best practices
    5. Synthesize a comprehensive answer
    
    Example request:
    ```json
    {
        "message": "How should I secure my Azure SQL Database?"
    }
    ```
    
    Returns the agent's answer along with reasoning steps showing:
    - Which tools were called
    - What documentation was retrieved
    - How the answer was constructed
    """
    try:
        logger.info(f"Received chat request: {request.message[:100]}...")
        
        # Get the agent runner
        runner = await get_agent_runner()
        
        # Execute the query
        result = await runner.execute_query(request.message)
        
        # Format intermediate steps for response
        reasoning_steps = []
        for action, observation in result.get("intermediate_steps", []):
            reasoning_steps.append(
                AgentStep(
                    action=action.tool if hasattr(action, "tool") else str(action),
                    action_input=action.tool_input if hasattr(action, "tool_input") else "",
                    observation=str(observation)[:500],  # Truncate long observations
                )
            )
        
        return AgentChatResponse(
            answer=result["output"],
            success=result["success"],
            reasoning_steps=reasoning_steps,
            error=result.get("error"),
        )
        
    except RuntimeError as e:
        logger.error(f"Agent not initialized: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent system not initialized. Please try again later."
        )
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat request: {str(e)}"
        )


@router.get("/health", response_model=AgentHealthResponse)
async def get_agent_health() -> AgentHealthResponse:
    """
    Check the health status of the agent system.
    
    Returns information about:
    - Overall agent status
    - MCP client connection
    - OpenAI configuration
    """
    try:
        runner = await get_agent_runner()
        health = runner.health_check()
        
        return AgentHealthResponse(
            status=health["status"],
            mcp_client_connected=health["mcp_client_connected"],
            openai_configured=health["openai_configured"],
        )
    except RuntimeError:
        return AgentHealthResponse(
            status="not_initialized",
            mcp_client_connected=False,
            openai_configured=False,
        )


@router.get("/capabilities")
async def get_agent_capabilities():
    """
    Get information about the agent's capabilities and available tools.
    
    Returns:
    - List of available tools
    - Tool descriptions
    - Agent capabilities
    """
    return {
        "agent_type": "ReAct (Reasoning + Acting)",
        "primary_function": "Azure Architecture Assistance",
        "tools": [
            {
                "name": "microsoft_docs_search",
                "description": "Search Microsoft/Azure documentation semantically",
                "use_cases": ["Find best practices", "Get architectural guidance", "Discover Azure services"]
            },
            {
                "name": "microsoft_docs_fetch",
                "description": "Fetch complete documentation pages as markdown",
                "use_cases": ["Get detailed tutorials", "Read full guides", "Access comprehensive documentation"]
            },
            {
                "name": "microsoft_code_samples_search",
                "description": "Find official Microsoft code examples",
                "use_cases": ["Get implementation examples", "Find SDK usage", "See code patterns"]
            }
        ],
        "specializations": [
            "Azure Well-Architected Framework",
            "Security best practices",
            "Cost optimization",
            "Reliability patterns",
            "Performance optimization"
        ],
        "limitations": [
            "Only provides guidance from official Microsoft documentation",
            "Cannot execute code or make changes to Azure resources",
            "Requires internet connectivity for documentation access"
        ]
    }
