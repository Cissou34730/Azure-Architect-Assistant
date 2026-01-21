"""
Graph state definition for LangGraph workflow.

Defines the typed state that carries data through the project chat graph.
"""

from typing import Any, TypedDict


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
    context_summary: str | None
    current_project_state: dict[str, Any]
    mindmap: dict[str, Any] | None
    mindmap_coverage: dict[str, Any] | None

    # Agent execution
    agent_output: str
    intermediate_steps: list[Any]  # Tool call traces
    stage_directives: str | None
    research_plan: list[str]

    # Post-processing
    architect_choice_required_section: str | None
    derived_updates: dict[str, Any]  # MCP logs + iteration events
    state_updates: dict[str, Any] | None  # From AAA_STATE_UPDATE extraction
    combined_updates: dict[str, Any]
    updated_project_state: dict[str, Any] | None

    # Response
    final_answer: str
    success: bool
    error: str | None

    # Phase 4+ fields
    user_message_id: str | None
    agent_message_id: str | None

    # Phase 5 fields (stage routing and retry)
    next_stage: str | None
    retry_count: int

    # Phase 6 fields (multi-agent)
    selected_specialist: str | None
    specialist_used: str | None
    specialist_notes: str | None


# Graph configuration constants
MAX_AGENT_ITERATIONS = 10
MAX_EXECUTION_TIME_SECONDS = 60

