"""
Agent router.
FastAPI router for agent chat endpoints and request handling.
"""

import logging
import re
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..runner import get_agent_runner
from ..services.project_context import (
    read_project_state,
    update_project_state,
    get_project_context_summary
)
from ...projects_database import get_db

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


class ProjectAgentChatRequest(BaseModel):
    """Request for project-aware agent chat."""
    message: str = Field(description="User's question or requirement")


class ProjectAgentChatResponse(BaseModel):
    """Response from project-aware agent chat."""
    answer: str = Field(description="Agent's final answer")
    success: bool = Field(description="Whether execution was successful")
    project_state: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Updated project state if modified"
    )
    reasoning_steps: List[AgentStep] = Field(
        default=[],
        description="Agent's reasoning steps"
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


@router.post("/projects/{project_id}/chat", response_model=ProjectAgentChatResponse)
async def chat_with_project_context(
    project_id: str,
    request: ProjectAgentChatRequest,
    db: AsyncSession = Depends(get_db)
) -> ProjectAgentChatResponse:
    """
    Chat with the agent in the context of a specific architecture project.
    
    The agent will:
    1. Load the current project state (requirements, NFRs, architecture)
    2. Consider project context when answering questions
    3. Search Azure documentation for relevant guidance
    4. Detect if the answer updates project requirements
    5. Update the project state if needed
    
    Example request:
    ```json
    {
        "message": "We need 99.9% availability for our web app"
    }
    ```
    
    The agent will understand this is an NFR and may update the project state accordingly.
    """
    try:
        logger.info(f"Project {project_id}: Received agent chat request")
        
        # Load project context
        project_state = await read_project_state(project_id, db)
        if not project_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project state not found for {project_id}. Please analyze documents first."
            )
        
        # Get formatted context summary
        context_summary = await get_project_context_summary(project_id, db)
        
        # Get the agent runner
        runner = await get_agent_runner()
        
        # Execute with project context
        result = await runner.execute_query(request.message, project_context=context_summary)
        
        # Parse response for potential state updates
        updated_state = None
        answer = result["output"]
        
        # Look for state update suggestions in the answer
        state_updates = _extract_state_updates(answer, request.message, project_state)
        
        if state_updates:
            logger.info(f"Project {project_id}: Detected state updates, applying...")
            try:
                updated_state = await update_project_state(project_id, state_updates, db)
                logger.info(f"Project {project_id}: State updated successfully")
            except Exception as update_error:
                logger.error(f"Failed to update state: {update_error}")
                # Don't fail the request, just log the error
        
        # Format reasoning steps
        reasoning_steps = []
        for action, observation in result.get("intermediate_steps", []):
            reasoning_steps.append(
                AgentStep(
                    action=action.tool if hasattr(action, "tool") else str(action),
                    action_input=action.tool_input if hasattr(action, "tool_input") else "",
                    observation=str(observation)[:500],
                )
            )
        
        return ProjectAgentChatResponse(
            answer=answer,
            success=result["success"],
            project_state=updated_state,
            reasoning_steps=reasoning_steps,
            error=result.get("error"),
        )
        
    except HTTPException:
        raise
    except RuntimeError as e:
        logger.error(f"Agent not initialized: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent system not initialized. Please try again later."
        )
    except Exception as e:
        logger.error(f"Project chat endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat request: {str(e)}"
        )


def _extract_state_updates(
    agent_response: str,
    user_message: str,
    current_state: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Extract potential ProjectState updates from agent response.
    
    This is a simple heuristic parser. For more robust parsing,
    we could ask the agent to output structured JSON.
    """
    updates = {}
    
    # Detect availability requirements
    availability_match = re.search(
        r'(\d{2,3}(?:\.\d+)?%)\s+(?:availability|uptime|SLA)',
        user_message + " " + agent_response,
        re.IGNORECASE
    )
    if availability_match:
        updates.setdefault("nfrs", {})["availability"] = f"{availability_match.group(1)} SLA requirement"
    
    # Detect security requirements
    security_keywords = ["security", "authentication", "authorization", "encryption", "compliance"]
    if any(keyword in user_message.lower() for keyword in security_keywords):
        if "security" not in current_state.get("nfrs", {}) or not current_state["nfrs"]["security"]:
            # Extract security-related content from agent response
            security_mentions = []
            for line in agent_response.split("\n"):
                if any(kw in line.lower() for kw in security_keywords):
                    security_mentions.append(line.strip())
            
            if security_mentions:
                updates.setdefault("nfrs", {})["security"] = "; ".join(security_mentions[:3])
    
    # Detect performance requirements
    perf_match = re.search(
        r'(\d+(?:\.\d+)?)\s*(ms|seconds?|milliseconds?)\s+(?:latency|response time)',
        user_message + " " + agent_response,
        re.IGNORECASE
    )
    if perf_match:
        updates.setdefault("nfrs", {})["performance"] = f"{perf_match.group(1)} {perf_match.group(2)} target"
    
    # Detect cost constraints
    if "cost" in user_message.lower() or "budget" in user_message.lower():
        cost_match = re.search(r'\$[\d,]+(?:\.\d{2})?', user_message)
        if cost_match:
            updates.setdefault("nfrs", {})["costConstraints"] = f"Budget: {cost_match.group(0)}"
    
    return updates if updates else None


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
