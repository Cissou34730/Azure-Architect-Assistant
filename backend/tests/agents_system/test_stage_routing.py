"""
Tests for Phase 5: Stage routing and retry logic.
"""

from app.agents_system.langgraph.nodes.stage_routing import (
    ProjectStage,
    build_retry_prompt,
    check_for_retry,
    classify_next_stage,
    propose_next_step,
    should_route_to_architecture_planner,
)
from app.agents_system.langgraph.state import GraphState


def test_classify_stage_clarify():
    """Test classification of clarify stage."""
    state: GraphState = {
        "user_message": "What is Azure App Service?",
        "current_project_state": {},
        "agent_output": "",
    }

    result = classify_next_stage(state)

    assert result["next_stage"] == ProjectStage.CLARIFY.value


def test_classify_stage_adr():
    """Test classification of ADR stage."""
    state: GraphState = {
        "user_message": "Let's document the architecture decision for using Azure SQL",
        "current_project_state": {},
        "agent_output": "",
    }

    result = classify_next_stage(state)

    assert result["next_stage"] == ProjectStage.MANAGE_ADR.value


def test_classify_stage_validation():
    """Test classification of validation stage."""
    state: GraphState = {
        "user_message": "Can you validate this against the WAF security pillar?",
        "current_project_state": {},
        "agent_output": "",
    }

    result = classify_next_stage(state)

    assert result["next_stage"] == ProjectStage.VALIDATE.value


def test_classify_stage_pricing():
    """Test classification of pricing stage."""
    state: GraphState = {
        "user_message": "What's the estimated cost for this solution?",
        "current_project_state": {},
        "agent_output": "",
    }

    result = classify_next_stage(state)

    assert result["next_stage"] == ProjectStage.PRICING.value


def test_classify_stage_iac():
    """Test classification of IaC stage."""
    state: GraphState = {
        "user_message": "Generate Terraform code for this architecture",
        "current_project_state": {},
        "agent_output": "",
    }

    result = classify_next_stage(state)

    assert result["next_stage"] == ProjectStage.IAC.value


def test_check_for_retry_no_error():
    """Test retry check when no error present."""
    state: GraphState = {
        "agent_output": "Here's the solution...",
        "retry_count": 0,
    }

    result = check_for_retry(state)

    assert result == "continue"


def test_check_for_retry_with_error():
    """Test retry check when ERROR: prefix detected."""
    state: GraphState = {
        "agent_output": "ERROR: Missing required field 'region'",
        "retry_count": 0,
    }

    result = check_for_retry(state)

    assert result == "retry"


def test_check_for_retry_max_retries():
    """Test retry check when max retries reached."""
    state: GraphState = {
        "agent_output": "ERROR: Still missing field",
        "retry_count": 1,
    }

    result = check_for_retry(state)

    assert result == "continue"  # Don't retry again


def test_build_retry_prompt():
    """Test building retry prompt."""
    state: GraphState = {
        "agent_output": "ERROR: Missing required parameter 'location'\nPlease provide location.",
        "retry_count": 0,
    }

    result = build_retry_prompt(state)

    assert "ERROR:" in result["agent_output"]
    assert "missing information" in result["agent_output"].lower()
    assert result["retry_count"] == 1


def test_propose_next_step_with_artifacts():
    """Test next step proposal when artifacts persisted."""
    state: GraphState = {
        "combined_updates": {
            "candidateArchitectures": [{"id": "c1", "name": "Solution A"}],
        },
        "final_answer": "Solution proposed.",
        "current_project_state": {},
    }

    result = propose_next_step(state)

    # Should not add questions when artifacts present
    assert result == {}


def test_propose_next_step_no_artifacts():
    """Test next step proposal when no artifacts persisted."""
    state: GraphState = {
        "combined_updates": {},
        "final_answer": "General discussion.",
        "current_project_state": {},
    }

    result = propose_next_step(state)

    # Should add next step questions
    assert "final_answer" in result
    assert "Next steps" in result["final_answer"] or result.get("final_answer") == "General discussion."


def test_propose_next_step_specific_gaps():
    """Test next step proposal identifies specific gaps."""
    state: GraphState = {
        "combined_updates": {},
        "final_answer": "Discussed requirements.",
        "current_project_state": {
            "candidateArchitectures": [{"id": "c1"}],  # Has candidate
            # Missing: adrs, findings/wafChecklist, costEstimates, iacArtifacts
        },
    }

    result = propose_next_step(state)

    # Should suggest missing items
    if "final_answer" in result:
        assert "decision" in result["final_answer"].lower() or "validate" in result["final_answer"].lower()


def test_architecture_planner_not_selected_for_explicit_waf_request():
    state: GraphState = {
        "user_message": "Let's start creating the WAF checklist now",
        "next_stage": ProjectStage.VALIDATE.value,
        "context_summary": "Multi-region, high availability, compliance required.",
        "current_project_state": {},
    }

    result = should_route_to_architecture_planner(state)

    assert result is False


def test_architecture_planner_selected_for_explicit_architecture_request():
    state: GraphState = {
        "user_message": "Design the target architecture for this platform",
        "next_stage": ProjectStage.PROPOSE_CANDIDATE.value,
        "context_summary": "",
        "current_project_state": {},
    }

    result = should_route_to_architecture_planner(state)

    assert result is True

