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

    # Thread memory (Phase 1+)
    thread_id: str | None
    thread_summary: str | None
    compaction_applied: bool
    context_budget_meta: dict[str, Any] | None

    # Context loading
    context_summary: str | None
    context_pack: dict[str, Any] | None  # Stage-specific context pack (Phase 3)
    current_project_state: dict[str, Any]
    mindmap: dict[str, Any] | None
    mindmap_coverage: dict[str, Any] | None

    # Agent execution
    agent_output: str
    intermediate_steps: list[Any]  # Tool call traces
    stage_directives: str | None
    research_plan: list[str]
    research_evidence_packets: list[dict[str, Any]]
    research_execution_artifact: dict[str, Any] | None
    architecture_synthesis_execution_artifact: dict[str, Any] | None
    validation_execution_artifact: dict[str, Any] | None
    mindmap_guidance: dict[str, Any] | None

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
    handled_by_stage_worker: bool

    # Phase 4+ fields
    user_message_id: str | None
    agent_message_id: str | None
    event_callback: Any

    # Phase 5 fields (stage routing and retry)
    next_stage: str | None
    retry_count: int

    # Phase 2 fields (multi-agent handoff)
    current_agent: str | None  # "main", "architecture_planner", "iac_generator"
    agent_handoff_context: dict[str, Any] | None  # Context passed between agents
    routing_decision: dict[str, str] | None  # {"agent": "...", "reason": "..."}
    sub_agent_input: str | None  # Prepared input for sub-agent
    sub_agent_output: str | None  # Output from sub-agent


# Graph configuration constants
MAX_AGENT_ITERATIONS = 10
MAX_EXECUTION_TIME_SECONDS = 60

