"""
Tests for Phase 6: Multi-agent supervisor and specialists.
"""

from app.agents_system.langgraph.nodes.multi_agent import (
    SpecialistType,
    adr_specialist_node,
    iac_specialist_node,
    pricing_specialist_node,
    route_to_specialist,
    supervisor_node,
    validation_specialist_node,
)
from app.agents_system.langgraph.state import GraphState


def test_supervisor_selects_adr_specialist():
    """Test supervisor selects ADR specialist for decision-related tasks."""
    state: GraphState = {
        "user_message": "Let's create an ADR for choosing Azure SQL over Cosmos DB",
        "next_stage": "manage_adr",
    }

    result = supervisor_node(state)

    assert result["selected_specialist"] == SpecialistType.ADR_SPECIALIST.value


def test_supervisor_selects_validation_specialist():
    """Test supervisor selects validation specialist for WAF/security tasks."""
    state: GraphState = {
        "user_message": "Validate this architecture against WAF security pillar",
        "next_stage": "validate",
    }

    result = supervisor_node(state)

    assert result["selected_specialist"] == SpecialistType.VALIDATION_SPECIALIST.value


def test_supervisor_selects_pricing_specialist():
    """Test supervisor selects pricing specialist for cost tasks."""
    state: GraphState = {
        "user_message": "What will this cost per month?",
        "next_stage": "pricing",
    }

    result = supervisor_node(state)

    assert result["selected_specialist"] == SpecialistType.PRICING_SPECIALIST.value


def test_supervisor_selects_iac_specialist():
    """Test supervisor selects IaC specialist for infrastructure code tasks."""
    state: GraphState = {
        "user_message": "Generate Terraform for this solution",
        "next_stage": "iac",
    }

    result = supervisor_node(state)

    assert result["selected_specialist"] == SpecialistType.IAC_SPECIALIST.value


def test_supervisor_selects_general():
    """Test supervisor selects general agent for non-specialist tasks."""
    state: GraphState = {
        "user_message": "Tell me about Azure services",
        "next_stage": "clarify",
    }

    result = supervisor_node(state)

    assert result["selected_specialist"] == SpecialistType.GENERAL.value


def test_adr_specialist_execution():
    """Test ADR specialist node execution."""
    state: GraphState = {
        "user_message": "Create ADR for database choice",
    }

    result = adr_specialist_node(state)

    assert result["specialist_used"] == SpecialistType.ADR_SPECIALIST.value
    assert "ADR specialist" in result["specialist_notes"]


def test_validation_specialist_execution():
    """Test validation specialist node execution."""
    state: GraphState = {
        "user_message": "Validate against security benchmarks",
    }

    result = validation_specialist_node(state)

    assert result["specialist_used"] == SpecialistType.VALIDATION_SPECIALIST.value
    assert "Validation specialist" in result["specialist_notes"]


def test_pricing_specialist_execution():
    """Test pricing specialist node execution."""
    state: GraphState = {
        "user_message": "Estimate costs",
    }

    result = pricing_specialist_node(state)

    assert result["specialist_used"] == SpecialistType.PRICING_SPECIALIST.value
    assert "Pricing specialist" in result["specialist_notes"]


def test_iac_specialist_execution():
    """Test IaC specialist node execution."""
    state: GraphState = {
        "user_message": "Generate IaC",
    }

    result = iac_specialist_node(state)

    assert result["specialist_used"] == SpecialistType.IAC_SPECIALIST.value
    assert "IaC specialist" in result["specialist_notes"]


def test_route_to_specialist_adr():
    """Test routing to ADR specialist."""
    state: GraphState = {
        "selected_specialist": SpecialistType.ADR_SPECIALIST.value,
    }

    route = route_to_specialist(state)

    assert route == "adr"


def test_route_to_specialist_validation():
    """Test routing to validation specialist."""
    state: GraphState = {
        "selected_specialist": SpecialistType.VALIDATION_SPECIALIST.value,
    }

    route = route_to_specialist(state)

    assert route == "validation"


def test_route_to_specialist_pricing():
    """Test routing to pricing specialist."""
    state: GraphState = {
        "selected_specialist": SpecialistType.PRICING_SPECIALIST.value,
    }

    route = route_to_specialist(state)

    assert route == "pricing"


def test_route_to_specialist_iac():
    """Test routing to IaC specialist."""
    state: GraphState = {
        "selected_specialist": SpecialistType.IAC_SPECIALIST.value,
    }

    route = route_to_specialist(state)

    assert route == "iac"


def test_route_to_specialist_general():
    """Test routing to general agent."""
    state: GraphState = {
        "selected_specialist": SpecialistType.GENERAL.value,
    }

    route = route_to_specialist(state)

    assert route == "general"


def test_route_to_specialist_missing():
    """Test routing defaults to general when specialist not set."""
    state: GraphState = {}

    route = route_to_specialist(state)

    assert route == "general"

