"""
Graph state definition for LangGraph workflow.

Defines the typed state that carries data through the project chat graph.
"""

from typing import TypedDict, Optional, Dict, Any, List


class GraphState(TypedDict, total=False):
    """
    State for project-aware chat graph (per turn).
    
    Carries all data needed for a single user message through the workflow.
    Fields are accumulated as nodes execute.
    """
    
    # Input
    project_id: str
    user_message: str
    
    # Context loading
    context_summary: Optional[str]
    current_project_state: Dict[str, Any]
    
    # Agent execution
    agent_output: str
    intermediate_steps: List[Any]  # Tool call traces
    
    # Post-processing
    architect_choice_required_section: Optional[str]
    derived_updates: Dict[str, Any]  # MCP logs + iteration events
    state_updates: Optional[Dict[str, Any]]  # From AAA_STATE_UPDATE extraction
    combined_updates: Dict[str, Any]
    updated_project_state: Optional[Dict[str, Any]]
    
    # Response
    final_answer: str
    success: bool
    error: Optional[str]


# Graph configuration constants
MAX_AGENT_ITERATIONS = 10
MAX_EXECUTION_TIME_SECONDS = 60
