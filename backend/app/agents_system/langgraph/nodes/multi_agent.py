"""
Multi-agent supervisor and specialist nodes.

Phase 6: Supervisor selects specialist subgraphs for focused tasks.
"""

import logging
from typing import Dict, Any, Literal, List
from enum import Enum

from ..state import GraphState

logger = logging.getLogger(__name__)


class SpecialistType(str, Enum):
    """Specialist agent types."""
    ADR_SPECIALIST = "adr_specialist"
    VALIDATION_SPECIALIST = "validation_specialist"
    PRICING_SPECIALIST = "pricing_specialist"
    IAC_SPECIALIST = "iac_specialist"
    GENERAL = "general"


def supervisor_node(state: GraphState) -> Dict[str, Any]:
    """
    Supervisor node that selects appropriate specialist.
    
    Phase 6: Routes to specialist subgraphs based on task type.
    
    Args:
        state: Current graph state
        
    Returns:
        State update with selected_specialist
    """
    user_message = state.get("user_message", "").lower()
    next_stage = state.get("next_stage", "")
    
    # Route based on stage and keywords
    if "adr" in next_stage or any(kw in user_message for kw in ["adr", "decision", "architecture decision"]):
        specialist = SpecialistType.ADR_SPECIALIST
    elif "validate" in next_stage or any(kw in user_message for kw in ["validate", "waf", "security", "compliance"]):
        specialist = SpecialistType.VALIDATION_SPECIALIST
    elif "pricing" in next_stage or any(kw in user_message for kw in ["cost", "price", "pricing", "budget"]):
        specialist = SpecialistType.PRICING_SPECIALIST
    elif "iac" in next_stage or any(kw in user_message for kw in ["terraform", "bicep", "iac", "infrastructure"]):
        specialist = SpecialistType.IAC_SPECIALIST
    else:
        specialist = SpecialistType.GENERAL
    
    logger.info(f"Supervisor selected specialist: {specialist.value}")
    
    return {
        "selected_specialist": specialist.value,
    }


def adr_specialist_node(state: GraphState) -> Dict[str, Any]:
    """
    ADR specialist focuses on architecture decision records.
    
    Phase 6: Narrowed toolset for ADR management.
    
    Args:
        state: Current graph state
        
    Returns:
        State update with specialist output
    """
    logger.info("ADR specialist processing request")
    
    # In full implementation, this would:
    # 1. Use only aaa_manage_adr tool + research tools
    # 2. Have specialized prompt for ADR creation
    # 3. Validate ADR structure and completeness
    
    return {
        "specialist_used": SpecialistType.ADR_SPECIALIST.value,
        "specialist_notes": "ADR specialist: Focused on architecture decision documentation",
    }


def validation_specialist_node(state: GraphState) -> Dict[str, Any]:
    """
    Validation specialist focuses on WAF and security validation.
    
    Phase 6: Narrowed toolset for validation tasks.
    
    Args:
        state: Current graph state
        
    Returns:
        State update with specialist output
    """
    logger.info("Validation specialist processing request")
    
    # In full implementation, this would:
    # 1. Use only aaa_record_validation_results tool + research tools
    # 2. Have specialized prompt for validation checks
    # 3. Focus on security, compliance, and WAF pillars
    
    return {
        "specialist_used": SpecialistType.VALIDATION_SPECIALIST.value,
        "specialist_notes": "Validation specialist: Focused on WAF and security validation",
    }


def pricing_specialist_node(state: GraphState) -> Dict[str, Any]:
    """
    Pricing specialist focuses on cost estimation.
    
    Phase 6: Narrowed toolset for pricing tasks.
    
    Args:
        state: Current graph state
        
    Returns:
        State update with specialist output
    """
    logger.info("Pricing specialist processing request")
    
    # In full implementation, this would:
    # 1. Use pricing-only portion of aaa_record_iac_and_cost tool
    # 2. Have specialized prompt for cost analysis
    # 3. Focus on TCO and cost optimization
    
    return {
        "specialist_used": SpecialistType.PRICING_SPECIALIST.value,
        "specialist_notes": "Pricing specialist: Focused on cost estimation and optimization",
    }


def iac_specialist_node(state: GraphState) -> Dict[str, Any]:
    """
    IaC specialist focuses on infrastructure code generation.
    
    Phase 6: Narrowed toolset for IaC tasks.
    
    Args:
        state: Current graph state
        
    Returns:
        State update with specialist output
    """
    logger.info("IaC specialist processing request")
    
    # In full implementation, this would:
    # 1. Use IaC-only portion of aaa_record_iac_and_cost tool
    # 2. Have specialized prompt for Terraform/Bicep generation
    # 3. Focus on IaC best practices and validation
    
    return {
        "specialist_used": SpecialistType.IAC_SPECIALIST.value,
        "specialist_notes": "IaC specialist: Focused on infrastructure as code generation",
    }


def route_to_specialist(state: GraphState) -> Literal["adr", "validation", "pricing", "iac", "general"]:
    """
    Router function for specialist selection.
    
    Phase 6: Determines which specialist node to execute.
    
    Args:
        state: Current graph state
        
    Returns:
        Specialist route key
    """
    selected_specialist = state.get("selected_specialist", SpecialistType.GENERAL.value)
    
    routing_map = {
        SpecialistType.ADR_SPECIALIST.value: "adr",
        SpecialistType.VALIDATION_SPECIALIST.value: "validation",
        SpecialistType.PRICING_SPECIALIST.value: "pricing",
        SpecialistType.IAC_SPECIALIST.value: "iac",
        SpecialistType.GENERAL.value: "general",
    }
    
    route = routing_map.get(selected_specialist, "general")
    logger.info(f"Routing to specialist: {route}")
    
    return route
