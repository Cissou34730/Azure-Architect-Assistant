"""
Stage routing and retry nodes for LangGraph workflow.

Phase 5: Add explicit stage routing and retry semantics.
"""

import logging
from typing import Dict, Any, Literal
from enum import Enum

from ..state import GraphState

logger = logging.getLogger(__name__)


class ProjectStage(str, Enum):
    """Project workflow stages."""
    CLARIFY = "clarify"
    PROPOSE_CANDIDATE = "propose_candidate"
    MANAGE_ADR = "manage_adr"
    VALIDATE = "validate"
    PRICING = "pricing"
    IAC = "iac"
    EXPORT = "export"


def classify_next_stage(state: GraphState) -> Dict[str, Any]:
    """
    Classify which stage should be executed next.
    
    Phase 5: Determines the next stage based on user message and project state.
    
    Args:
        state: Current graph state
        
    Returns:
        State update with next_stage
    """
    user_message = state.get("user_message", "").lower()
    project_state = state.get("current_project_state", {})
    agent_output = state.get("agent_output", "").lower()
    
    # Keyword-based stage classification
    if any(kw in user_message for kw in ["what", "why", "how", "explain", "clarify", "?"]):
        next_stage = ProjectStage.CLARIFY
    elif any(kw in user_message for kw in ["adr", "decision", "record", "architecture decision"]):
        next_stage = ProjectStage.MANAGE_ADR
    elif any(kw in user_message for kw in ["validate", "validation", "waf", "security", "compliance", "benchmark"]):
        next_stage = ProjectStage.VALIDATE
    elif any(kw in user_message for kw in ["cost", "price", "pricing", "budget", "estimate"]):
        next_stage = ProjectStage.PRICING
    elif any(kw in user_message for kw in ["terraform", "bicep", "iac", "infrastructure", "code"]):
        next_stage = ProjectStage.IAC
    elif any(kw in user_message for kw in ["export", "document", "report", "summary"]):
        next_stage = ProjectStage.EXPORT
    elif any(kw in agent_output for kw in ["candidate", "solution", "propose", "suggest"]):
        next_stage = ProjectStage.PROPOSE_CANDIDATE
    else:
        # Default to clarify
        next_stage = ProjectStage.CLARIFY
    
    logger.info(f"Classified next stage: {next_stage.value}")
    
    return {
        "next_stage": next_stage.value,
    }


def check_for_retry(state: GraphState) -> Literal["retry", "continue"]:
    """
    Check if agent output requires a retry.
    
    Phase 5: Detects ERROR: prefixes and suggests retry.
    
    Args:
        state: Current graph state
        
    Returns:
        "retry" if error detected, "continue" otherwise
    """
    agent_output = state.get("agent_output", "")
    retry_count = state.get("retry_count", 0)
    
    # Check for ERROR: prefix
    if agent_output.strip().startswith("ERROR:") and retry_count < 1:
        logger.warning("Error detected in agent output, suggesting retry")
        return "retry"
    
    return "continue"


def build_retry_prompt(state: GraphState) -> Dict[str, Any]:
    """
    Build a retry prompt asking for missing fields.
    
    Phase 5: Extracts error and asks user to provide missing information.
    
    Args:
        state: Current graph state
        
    Returns:
        State update with retry prompt
    """
    agent_output = state.get("agent_output", "")
    retry_count = state.get("retry_count", 0)
    
    # Extract error message
    error_lines = [line for line in agent_output.split("\n") if line.strip().startswith("ERROR:")]
    error_message = error_lines[0] if error_lines else "An error occurred"
    
    retry_prompt = (
        f"{error_message}\n\n"
        f"Please provide the missing information or clarify your request."
    )
    
    logger.info(f"Built retry prompt (attempt {retry_count + 1})")
    
    return {
        "agent_output": retry_prompt,
        "retry_count": retry_count + 1,
    }


def propose_next_step(state: GraphState) -> Dict[str, Any]:
    """
    Always propose next step if no artifact was persisted.
    
    Phase 5: Ensures system returns either persisted update or clarifying questions.
    
    Args:
        state: Current graph state
        
    Returns:
        State update with next step questions
    """
    combined_updates = state.get("combined_updates", {})
    final_answer = state.get("final_answer", "")
    
    # Check if any artifact was persisted
    has_artifacts = any(
        key in combined_updates and combined_updates[key]
        for key in ["candidates", "adrs", "validationResults", "costEstimate", "iacCode"]
    )
    
    if has_artifacts:
        # Artifact persisted, no need for next step questions
        return {}
    
    # Generate high-impact questions based on project state
    current_state = state.get("current_project_state", {})
    questions = []
    
    if not current_state.get("candidates"):
        questions.append("What solution approaches should we explore?")
    if not current_state.get("adrs"):
        questions.append("What architectural decisions need to be documented?")
    if not current_state.get("validationResults"):
        questions.append("Should we validate this against WAF or security benchmarks?")
    if not current_state.get("costEstimate"):
        questions.append("Do you need a cost estimate for this architecture?")
    if not current_state.get("iacCode"):
        questions.append("Should we generate Infrastructure as Code?")
    
    # Take top 3-5 questions
    next_step_questions = questions[:5]
    
    if next_step_questions:
        next_step_prompt = "\n\n**Next steps to consider:**\n" + "\n".join(
            [f"- {q}" for q in next_step_questions]
        )
        
        logger.info(f"Proposed {len(next_step_questions)} next step questions")
        
        return {
            "final_answer": final_answer + next_step_prompt,
        }
    
    return {}
