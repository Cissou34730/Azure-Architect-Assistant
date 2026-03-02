"""SaaS Advisor routing and handoff logic."""

import logging
import re
from typing import Any

from ...state import GraphState
from ._helpers import format_requirements

logger = logging.getLogger(__name__)


def should_route_to_saas_advisor(state: GraphState) -> bool:
    """
    Determine if request should go to SaaS Advisor sub-agent.

    Route to SaaS Advisor ONLY when:
    - User explicitly mentions "SaaS", "multi-tenant", "B2B/B2C"
    - User asks "should this be SaaS?" or similar suitability questions

    DO NOT route for:
    - Regular web applications (even with authentication)
    - Single-tenant enterprise applications
    - Internal tools or CRUD apps

    This is a LOW priority routing check (after Architecture Planner and IaC Generator).

    Args:
        state: Current graph state

    Returns:
        True if should route to SaaS advisor
    """
    user_message = (state.get("user_message") or "").lower()

    # Explicit SaaS keywords (strict matching)
    saas_keywords = [
        "saas", "multi-tenant", "multitenant", "multi tenant",
        "b2b saas", "b2c saas", "tenant isolation",
        "subscription-based", "saas architecture",
        "deployment stamps", "noisy neighbor",
    ]

    explicit_saas = any(keyword in user_message for keyword in saas_keywords)

    if explicit_saas:
        logger.info("🏢 Routing to SaaS Advisor: explicit SaaS keywords detected")
        return True

    # User asks about SaaS suitability
    suitability_questions = [
        "should this be saas", "should this be a saas",
        "is saas appropriate", "is this suitable for saas",
        "saas or not", "multi-tenant or single-tenant",
        "should i use saas", "recommend saas",
    ]

    asking_about_saas = any(phrase in user_message for phrase in suitability_questions)

    if asking_about_saas:
        logger.info("🏢 Routing to SaaS Advisor: SaaS suitability question detected")
        return True

    # REMOVED: Context-based routing to avoid false positives
    # Only route based on explicit user message keywords

    return False


def prepare_saas_advisor_handoff(state: GraphState) -> dict[str, Any]:
    """
    Prepare handoff context for SaaS Advisor sub-agent.

    Extracts project requirements, tenant requirements, and constraints
    to pass to the specialized SaaS advisor agent.

    Args:
        state: Current graph state

    Returns:
        State update with agent_handoff_context for SaaS advisor
    """
    project_state = state.get("current_project_state") or {}
    context_summary = state.get("context_summary") or ""

    # Extract project requirements
    requirements = project_state.get("requirements") or {}
    requirements_text = format_requirements(requirements)

    # Extract tenant requirements from context
    tenant_requirements = _extract_tenant_requirements(state)

    # Extract current architecture if exists
    architectures = project_state.get("candidateArchitectures") or []
    current_architecture = ""
    if architectures:
        latest_arch = architectures[-1]
        current_architecture = latest_arch.get("description", "")
        diagram = latest_arch.get("diagram", "")
        if diagram:
            current_architecture += f"\n\n**Diagram:**\n{diagram}"

    # Extract constraints
    req_params = requirements if isinstance(requirements, dict) else {}
    constraints = {
        "budget": req_params.get("budget"),
        "timeline": req_params.get("timeline"),
        "compliance": req_params.get("compliance", []),
        "regions": req_params.get("allowedRegions", []),
    }

    handoff_context = {
        "project_context": context_summary,
        "requirements": requirements_text,
        "current_architecture": current_architecture,
        "tenant_requirements": tenant_requirements,
        "constraints": constraints,
        "user_request": state.get("user_message", ""),
        "routing_reason": "SaaS-specific architecture guidance requested",
    }

    logger.info(
        f"Prepared SaaS Advisor handoff context: "
        f"customer_type={tenant_requirements.get('customer_type', 'unknown')}, "
        f"expected_tenants={tenant_requirements.get('expected_tenants', 'unknown')}"
    )

    return {
        "agent_handoff_context": handoff_context,
        "current_agent": "saas_advisor",
    }


def _extract_tenant_requirements(state: GraphState) -> dict[str, Any]:
    """
    Extract tenant-specific requirements from state.

    Looks for:
    - Expected number of tenants
    - Customer type (B2B, B2C)
    - Isolation level (high, medium, low)
    - Compliance requirements

    Args:
        state: Current graph state

    Returns:
        Dictionary of tenant requirements
    """
    user_message = (state.get("user_message") or "").lower()
    context_summary = (state.get("context_summary") or "").lower()

    combined_text = f"{user_message} {context_summary}"

    tenant_reqs: dict[str, Any] = {}

    customer_type = _detect_customer_type(combined_text)
    if customer_type:
        tenant_reqs["customer_type"] = customer_type

    expected_tenants = _detect_expected_tenants(combined_text)
    if expected_tenants is not None:
        tenant_reqs["expected_tenants"] = expected_tenants

    isolation_level = _detect_isolation_level(combined_text)
    if isolation_level:
        tenant_reqs["isolation_level"] = isolation_level

    compliance = _detect_compliance_requirements(combined_text)

    if compliance:
        tenant_reqs["compliance"] = compliance

    tenant_tiers = _detect_tenant_tiers(combined_text)
    if tenant_tiers:
        tenant_reqs["tenant_tiers"] = tenant_tiers

    return tenant_reqs


def _detect_customer_type(combined_text: str) -> str | None:
    """Detect customer type (B2B/B2C) from text."""
    if "b2b" in combined_text:
        return "b2b"
    if "b2c" in combined_text:
        return "b2c"
    if "enterprise" in combined_text and ("customer" in combined_text or "client" in combined_text):
        return "b2b"
    if "consumer" in combined_text or "individual user" in combined_text:
        return "b2c"
    return None


def _detect_expected_tenants(combined_text: str) -> int | None:
    """Detect expected tenant count from text."""
    tenant_count_patterns = [
        r"(\d+)\s*tenants?",
        r"(\d+)\s*customers?",
        r"expect\s*(\d+)",
        r"support\s*(\d+)",
    ]

    for pattern in tenant_count_patterns:
        match = re.search(pattern, combined_text)
        if match:
            return int(match.group(1))
    return None


def _detect_isolation_level(combined_text: str) -> str | None:
    """Detect isolation level from text."""
    isolation_keywords = {
        "high": ["hipaa", "healthcare", "financial", "bank", "government", "dedicated", "isolated"],
        "medium": ["enterprise", "b2b", "custom sla"],
        "low": ["b2c", "shared", "freemium"],
    }

    for level, keywords in isolation_keywords.items():
        if any(kw in combined_text for kw in keywords):
            return level
    return None


def _detect_compliance_requirements(combined_text: str) -> list[str]:
    """Detect compliance requirements from text."""
    compliance_keywords = ["hipaa", "gdpr", "soc 2", "pci dss", "iso 27001"]
    return [comp.upper() for comp in compliance_keywords if comp in combined_text]


def _detect_tenant_tiers(combined_text: str) -> list[str] | None:
    """Detect tenant tiers mentioned in text."""
    if any(tier in combined_text for tier in ["free tier", "premium", "standard", "enterprise tier"]):
        return ["free", "standard", "premium"]
    return None
