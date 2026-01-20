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

    requirements = project_state.get("requirements") or []
    candidates = project_state.get("candidateArchitectures") or []
    adrs = project_state.get("adrs") or []
    findings = project_state.get("findings") or []
    iac = project_state.get("iacArtifacts") or []
    cost_estimates = project_state.get("costEstimates") or []
    waf = project_state.get("wafChecklist") or {}

    has_requirements = bool(requirements)
    has_candidate = bool(candidates)
    has_adrs = bool(adrs)
    has_findings = bool(findings)
    has_iac = bool(iac)
    has_cost = bool(cost_estimates)
    has_waf = bool(waf)

    # Keyword-first for explicit intent
    if any(kw in user_message for kw in ["adr", "decision", "record", "architecture decision"]):
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
        # State-aware defaults
        if not has_requirements:
            next_stage = ProjectStage.CLARIFY
        elif not has_candidate:
            next_stage = ProjectStage.PROPOSE_CANDIDATE
        elif not has_adrs:
            next_stage = ProjectStage.MANAGE_ADR
        elif not has_findings or not has_waf:
            next_stage = ProjectStage.VALIDATE
        elif not has_cost:
            next_stage = ProjectStage.PRICING
        elif not has_iac:
            next_stage = ProjectStage.IAC
        else:
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
        for key in [
            "candidateArchitectures",
            "adrs",
            "findings",
            "iacArtifacts",
            "costEstimates",
            "diagrams",
        ]
    )
    
    if has_artifacts:
        # Artifact persisted, no need for next step questions
        return {}
    
    # Generate high-impact questions based on project state
    current_state = state.get("current_project_state", {})
    questions = []

    if not current_state.get("candidateArchitectures"):
        questions.append("Should we propose 1-2 candidate Azure architectures and generate the first C4 L1 diagram?")
    if not current_state.get("adrs"):
        questions.append("Which decisions should be captured as ADRs with WAF or diagram evidence?")
    if not current_state.get("findings") or not current_state.get("wafChecklist"):
        questions.append("Do you want validation against WAF + Azure Security Benchmark now?")
    if not current_state.get("iacArtifacts"):
        questions.append("Should we generate Terraform/Bicep for the proposed components?")
    if not current_state.get("costEstimates"):
        questions.append("Do you need a cost estimate with key usage assumptions?")

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
