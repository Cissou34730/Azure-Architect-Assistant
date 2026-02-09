"""
Stage routing and retry nodes for LangGraph workflow.

Phase 5: Add explicit stage routing and retry semantics.
"""

import logging
import re
from enum import Enum
from typing import Any, Literal

from ..state import GraphState

logger = logging.getLogger(__name__)

COMPLEXITY_THRESHOLD = 3


_NON_ARCH_INTENT_KEYWORDS = [
    "waf",
    "checklist",
    "validate",
    "validation",
    "security benchmark",
    "aaa_record_validation_results",
    "adr",
    "decision",
    "cost",
    "price",
    "pricing",
    "budget",
    "terraform",
    "bicep",
    "iac",
    "infrastructure as code",
]


class ProjectStage(str, Enum):
    """Project workflow stages."""
    CLARIFY = "clarify"
    PROPOSE_CANDIDATE = "propose_candidate"
    MANAGE_ADR = "manage_adr"
    VALIDATE = "validate"
    PRICING = "pricing"
    IAC = "iac"
    EXPORT = "export"


def classify_next_stage(state: GraphState) -> dict[str, Any]:
    """
    Classify which stage should be executed next.
    """
    user_message = (state.get("user_message") or "").lower()
    project_state = state.get("current_project_state") or {}
    agent_output = (state.get("agent_output") or "").lower()

    # 1. Keyword-based intent detection (highest priority)
    next_stage = _detect_intent_from_keywords(user_message, agent_output)

    # 2. State-aware defaults
    if next_stage is None:
        next_stage = _detect_intent_from_state(project_state)

    final_stage = next_stage or ProjectStage.CLARIFY
    logger.info(f"Classified next stage: {final_stage.value}")

    return {
        "next_stage": final_stage.value,
    }


def _detect_intent_from_keywords(user_message: str, agent_output: str) -> ProjectStage | None:
    """Detect intended stage from keywords in user message or agent output."""
    mapping = [
        (["validate", "validation", "waf", "security", "compliance", "benchmark"], ProjectStage.VALIDATE),
        (["adr", "decision", "architecture decision"], ProjectStage.MANAGE_ADR),
        (["cost", "price", "pricing", "budget", "estimate"], ProjectStage.PRICING),
        (["terraform", "bicep", "iac", "infrastructure", "code"], ProjectStage.IAC),
        (["export", "document", "report", "summary"], ProjectStage.EXPORT),
    ]

    for keywords, stage in mapping:
        if any(kw in user_message for kw in keywords):
            return stage

    # Check agent output for proposal intents
    if any(kw in agent_output for kw in ["candidate", "solution", "propose", "suggest"]):
        return ProjectStage.PROPOSE_CANDIDATE

    return None


def _detect_intent_from_state(project_state: dict[str, Any]) -> ProjectStage:
    """Detect next stage based on gaps in current project state."""
    # List of required fields and their corresponding stages
    requirements = [
        ("requirements", ProjectStage.CLARIFY),
        ("candidateArchitectures", ProjectStage.PROPOSE_CANDIDATE),
        ("adrs", ProjectStage.MANAGE_ADR),
    ]

    for field, stage in requirements:
        if not project_state.get(field):
            return stage

    waf = project_state.get("wafChecklist") or {}
    if not project_state.get("findings") or not waf:
        return ProjectStage.VALIDATE

    # Post-validation stages
    post_val = [
        ("costEstimates", ProjectStage.PRICING),
        ("iacArtifacts", ProjectStage.IAC),
    ]

    for field, stage in post_val:
        if not project_state.get(field):
            return stage

    return ProjectStage.CLARIFY


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


def build_retry_prompt(state: GraphState) -> dict[str, Any]:
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


def _generate_next_step_questions(current_state: dict[str, Any]) -> list[str]:
    """Generate high-impact follow-up questions based on missing project artifacts."""
    questions = []
    if not current_state.get("candidateArchitectures"):
        questions.append(
            "Should we propose 1-2 candidate Azure architectures and generate the first C4 L1 diagram?"
        )
    if not current_state.get("adrs"):
        questions.append(
            "Which decisions should be captured as ADRs with WAF or diagram evidence?"
        )
    if not current_state.get("findings") or not current_state.get("wafChecklist"):
        questions.append(
            "Do you want validation against WAF + Azure Security Benchmark now?"
        )
    if not current_state.get("iacArtifacts"):
        questions.append(
            "Should we generate Terraform/Bicep for the proposed components?"
        )
    if not current_state.get("costEstimates"):
        questions.append("Do you need a cost estimate with key usage assumptions?")

    return questions[:5]


def propose_next_step(state: GraphState) -> dict[str, Any]:
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
    artifact_keys = [
        "candidateArchitectures",
        "adrs",
        "findings",
        "iacArtifacts",
        "costEstimates",
        "diagrams",
    ]
    if any(combined_updates.get(k) for k in artifact_keys):
        return {}

    # Generate high-impact questions based on project state
    questions = _generate_next_step_questions(state.get("current_project_state", {}))

    if not questions:
        return {}

    next_step_prompt = "\n\n**Next steps to consider:**\n" + "\n".join(
        [f"- {q}" for q in questions]
    )

    logger.info(f"Proposed {len(questions)} next step questions")
    return {
        "final_answer": final_answer + next_step_prompt,
    }


# Phase 2: Multi-Agent Routing
# -----------------------------------------------------------------------------


def should_route_to_architecture_planner(state: GraphState) -> bool:
    """
    Determine if request should go to Architecture Planner sub-agent.

    Route to Architecture Planner when:
    - User explicitly requests "architecture", "design", "proposal"
    - Project stage suggests architecture planning needed
    - Complexity indicators detected (multi-region, HA, DR, compliance)

    Args:
        state: Current graph state

    Returns:
        True if should route to architecture planner
    """
    user_message = (state.get("user_message") or "").lower()
    next_stage = state.get("next_stage")

    # Stage guard: if workflow stage already indicates a non-architecture task,
    # do not hijack routing with complexity heuristics.
    blocked_stages = {
        ProjectStage.VALIDATE.value,
        ProjectStage.MANAGE_ADR.value,
        ProjectStage.PRICING.value,
        ProjectStage.IAC.value,
        ProjectStage.EXPORT.value,
    }
    if next_stage in blocked_stages:
        logger.info(
            "Skipping Architecture Planner routing: stage=%s indicates a non-architecture task",
            next_stage,
        )
        return False

    # Intent guard: explicit WAF/validation/checklist/pricing/IaC requests
    # should not be routed to Architecture Planner.
    if any(keyword in user_message for keyword in _NON_ARCH_INTENT_KEYWORDS):
        logger.info(
            "Skipping Architecture Planner routing: explicit non-architecture intent detected"
        )
        return False

    # Explicit architecture request keywords
    arch_keywords = [
        "architecture", "design the architecture", "propose architecture",
        "candidate architecture", "architecture proposal", "system design",
        "how should i architect", "what should the architecture look like",
        "design solution", "propose solution", "architecture diagram",
    ]

    if any(keyword in user_message for keyword in arch_keywords):
        logger.info("🎯 Routing to Architecture Planner: explicit request detected")
        return True

    # Check project stage
    if next_stage == ProjectStage.PROPOSE_CANDIDATE.value and any(
        kw in user_message for kw in ["architecture", "design", "propose", "solution"]
    ):
        logger.info("🎯 Routing to Architecture Planner: proposal stage + design request")
        return True

    # Check complexity indicators
    context_summary = state.get("context_summary") or ""
    project_state = state.get("current_project_state") or {}

    # Extract NFR requirements from project state
    requirements = project_state.get("requirements") or {}
    nfr_text = (context_summary + " " + str(requirements)).lower()

    complexity_indicators = [
        "multi-region", "high availability", "disaster recovery",
        "compliance", "soc 2", "hipaa", "gdpr", "pci dss",
        "microservices", "event-driven", "real-time",
        "99.9%", "99.95%", "99.99%",  # SLA indicators
        "global", "worldwide", "distributed",
    ]

    complexity_count = sum(1 for indicator in complexity_indicators if indicator in nfr_text)
    has_design_language = any(
        kw in user_message for kw in ["architecture", "design", "propose", "solution"]
    )
    if complexity_count >= COMPLEXITY_THRESHOLD and (
        next_stage == ProjectStage.PROPOSE_CANDIDATE.value or has_design_language
    ):
        logger.info(
            f"🎯 Routing to Architecture Planner: complexity threshold "
            f"({complexity_count} indicators)"
        )
        return True

    return False


def prepare_architecture_planner_handoff(state: GraphState) -> dict[str, Any]:
    """
    Prepare handoff context for Architecture Planner sub-agent.

    Extracts requirements, NFR constraints, and project context to pass
    to the specialized architecture planning agent.

    Args:
        state: Current graph state

    Returns:
        State update with agent_handoff_context
    """
    project_state = state.get("current_project_state") or {}
    context_summary = state.get("context_summary") or ""

    # Extract requirements (handle legacy dict or modern artifact list)
    requirements = project_state.get("requirements") or {}
    
    # Normalize for parameter extraction
    req_params = requirements if isinstance(requirements, dict) else {}
    
    requirements_text = _format_requirements(requirements)

    # Extract NFR summary (handles both types)
    nfr_summary = _extract_nfr_summary(requirements, context_summary)

    # Extract constraints
    constraints = {
        "budget": req_params.get("budget"),
        "timeline": req_params.get("timeline"),
        "compliance": req_params.get("compliance", []),
        "regions": req_params.get("allowedRegions", []),
        "excluded_services": req_params.get("excludedServices", []),
    }
    # Remove None values
    constraints = {k: v for k, v in constraints.items() if v}

    # Extract previous architectural decisions
    previous_decisions = project_state.get("adrs") or []

    handoff_context = {
        "project_context": context_summary,
        "requirements": requirements_text,
        "nfr_summary": nfr_summary,
        "constraints": constraints,
        "previous_decisions": previous_decisions,
        "user_request": state.get("user_message", ""),
        "routing_reason": "Complex architecture design required with NFR analysis",
    }

    logger.info(
        f"Prepared Architecture Planner handoff context: "
        f"{len(nfr_summary)} chars NFR, {len(previous_decisions)} ADRs"
    )

    return {
        "agent_handoff_context": handoff_context,
        "current_agent": "architecture_planner",
    }


def _format_requirements(requirements: Any) -> str:
    """Format requirements dictionary or list for handoff."""
    if not requirements:
        return "No explicit requirements provided."

    if isinstance(requirements, list):
        items = []
        for req in requirements:
            if isinstance(req, dict):
                title = req.get("title") or req.get("text") or "Requirement"
                desc = req.get("description") or ""
                items.append(f"- {title}: {desc}" if desc else f"- {title}")
            else:
                items.append(f"- {str(req)}")
        return "\n".join(items) if items else "No explicit requirements provided."

    formatted = []
    if "workloadType" in requirements:
        formatted.append(f"- Workload Type: {requirements['workloadType']}")
    if "expectedUsers" in requirements:
        formatted.append(f"- Expected Users: {requirements['expectedUsers']}")
    if "dataVolume" in requirements:
        formatted.append(f"- Data Volume: {requirements['dataVolume']}")
    if "sla" in requirements:
        formatted.append(f"- SLA Target: {requirements['sla']}")
    if "rto" in requirements:
        formatted.append(f"- RTO: {requirements['rto']}")
    if "rpo" in requirements:
        formatted.append(f"- RPO: {requirements['rpo']}")

    return "\n".join(formatted) if formatted else str(requirements)


def _extract_nfr_summary(requirements: Any, context: str) -> str:
    """Extract non-functional requirements summary."""
    nfr_parts = _build_nfr_sections(requirements)
    return "\n".join(nfr_parts) if nfr_parts else "No explicit NFR requirements provided."


def _build_nfr_sections(requirements: Any) -> list[str]:
    """Build formatted NFR sections from requirements."""
    nfr_parts = []
    
    # Normalize for parameter extraction
    req_params = requirements if isinstance(requirements, dict) else {}

    performance = req_params.get("sla")
    if performance:
        nfr_parts.append(f"**Performance:** SLA target: {performance}")

    scale_info = _format_keyed_values(requirements, [("Users", "expectedUsers"), ("Data", "dataVolume")])
    if scale_info:
        nfr_parts.append(f"**Scalability:** {scale_info}")

    reliability_info = _format_keyed_values(requirements, [("RTO", "rto"), ("RPO", "rpo")])
    if reliability_info:
        nfr_parts.append(f"**Reliability:** {reliability_info}")

    compliance_list = req_params.get("compliance", []) if isinstance(req_params.get("compliance", []), list) else []
    if compliance_list:
        nfr_parts.append(f"**Security/Compliance:** {', '.join(compliance_list)}")

    budget = req_params.get("budget")
    if budget:
        nfr_parts.append(f"**Cost:** Budget constraint: {budget}")

    return nfr_parts


def _format_keyed_values(requirements: Any, labels: list[tuple[str, str]]) -> str | None:
    """Format a list of requirement keys as labeled values."""
    if not isinstance(requirements, dict):
        return None
        
    parts = []
    for label, key in labels:
        value = requirements.get(key)
        if value:
            parts.append(f"{label}: {value}")
    return ", ".join(parts) if parts else None


def should_route_to_iac_generator(state: GraphState) -> bool:
    """
    Determine if request should go to IaC Generator sub-agent.

    Route to IaC Generator when:
    - User explicitly requests "terraform", "bicep", "iac"
    - Project stage is "iac"
    - Architecture is finalized (candidateArchitectures exists)

    Args:
        state: Current graph state

    Returns:
        True if should route to IaC generator
    """
    user_message = (state.get("user_message") or "").lower()

    # Explicit IaC keywords
    iac_keywords = [
        "terraform", "bicep", "iac", "infrastructure as code",
        "infrastructure code", "deploy", "provision",
        "generate bicep", "generate terraform", "create iac",
    ]

    if any(keyword in user_message for keyword in iac_keywords):
        # Only route if architecture is finalized
        project_state = state.get("current_project_state") or {}
        has_architecture = bool(project_state.get("candidateArchitectures"))

        if has_architecture:
            logger.info("🎯 Routing to IaC Generator: explicit request + architecture exists")
            return True
        else:
            logger.warning(
                "IaC request detected but no architecture finalized. "
                "Will not route to IaC Generator."
            )
            return False

    # Check project stage
    next_stage = state.get("next_stage")
    if next_stage == ProjectStage.IAC.value:
        logger.info("🎯 Routing to IaC Generator: project stage is 'iac'")
        return True

    return False


def prepare_iac_generator_handoff(state: GraphState) -> dict[str, Any]:
    """
    Prepare handoff context for IaC Generator sub-agent.

    Extracts architecture, resource list, and constraints to pass
    to the specialized IaC generation agent.

    Args:
        state: Current graph state

    Returns:
        State update with agent_handoff_context
    """
    project_state = state.get("current_project_state") or {}
    context_summary = state.get("context_summary") or ""

    # Extract architecture (use first candidate if multiple)
    candidate_architectures = project_state.get("candidateArchitectures") or []
    architecture = candidate_architectures[0] if candidate_architectures else {}

    # Extract resource list from architecture
    resource_list = _extract_resource_list(architecture, context_summary)

    # Detect IaC format from user message
    user_message = state.get("user_message", "").lower()
    iac_format = _detect_iac_format(user_message)

    # Extract constraints
    requirements = project_state.get("requirements") or {}
    
    # Handle list requirements by normalizing for parameter extraction
    req_params = requirements if isinstance(requirements, dict) else {}
    
    constraints = {
        "regions": req_params.get("allowedRegions", []),
        "naming_convention": req_params.get("namingConvention"),
        "tagging_policy": req_params.get("taggingPolicy", {}),
        "compliance": req_params.get("compliance", []),
    }
    # Remove None values
    constraints = {k: v for k, v in constraints.items() if v}

    handoff_context = {
        "project_context": context_summary,
        "architecture": architecture,
        "resource_list": resource_list,
        "constraints": constraints,
        "iac_format": iac_format,
        "user_request": state.get("user_message", ""),
        "routing_reason": "IaC generation for finalized architecture",
    }

    logger.info(
        f"Prepared IaC Generator handoff context: "
        f"format={iac_format}, {len(resource_list)} resources"
    )

    return {
        "agent_handoff_context": handoff_context,
        "current_agent": "iac_generator",
    }


def _extract_resource_list(architecture: dict[str, Any], context: str) -> list[str]:
    """Extract list of Azure resources from architecture."""
    resources = []

    # Try to extract from architecture components
    if "components" in architecture:
        components = architecture["components"]
        if isinstance(components, list):
            for component in components:
                if isinstance(component, dict) and "type" in component:
                    resources.append(f"{component.get('name', 'unnamed')} ({component['type']})")
                elif isinstance(component, str):
                    resources.append(component)

    # If no components, try to parse from description or diagram
    if not resources:
        # Common Azure resource type keywords
        azure_resources = [
            "App Service", "Function App", "Storage Account", "Cosmos DB",
            "SQL Database", "Key Vault", "Application Insights", "Virtual Network",
            "API Management", "Service Bus", "Event Hubs", "Container Instances",
            "Kubernetes Service", "Redis Cache", "Front Door", "CDN",
        ]

        description = architecture.get("description", "")
        diagram = architecture.get("diagram", "")
        combined_text = f"{description} {diagram} {context}".lower()

        for resource_type in azure_resources:
            if resource_type.lower() in combined_text:
                resources.append(resource_type)

    return resources if resources else ["Extract from architecture description"]


def _detect_iac_format(user_message: str) -> str:
    """Detect IaC format (Bicep or Terraform) from user message."""
    if "terraform" in user_message:
        return "terraform"
    elif "bicep" in user_message:
        return "bicep"
    else:
        # Default to Bicep (Azure-native)
        return "bicep"


# ==============================================================================
# Phase 3: SaaS Advisor Routing
# ==============================================================================


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
    requirements_text = _format_requirements(requirements)

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


# ==============================================================================
# Phase 3: Cost Estimator Routing
# ==============================================================================


def should_route_to_cost_estimator(state: GraphState) -> bool:
    """
    Determine if request should go to Cost Estimator sub-agent.

    Route to Cost Estimator ONLY when:
    - User explicitly mentions "cost", "price", "pricing", "how much", "TCO", "budget"
    - User asks for cost estimate or breakdown
    - Architecture is finalized (candidateArchitectures exists)

    DO NOT route for:
    - General architecture questions (no cost aspect)
    - Budget as a constraint (not requesting estimate)

    This is a LOW priority routing check (after IaC, Architecture, and SaaS).

    Args:
        state: Current graph state

    Returns:
        True if should route to Cost Estimator
    """
    user_message = (state.get("user_message") or "").lower()

    # Explicit cost keywords (strict matching)
    cost_keywords = [
        "cost", "price", "pricing", "how much",
        "tco", "total cost of ownership",
        "budget estimate", "cost estimate", "estimate cost",
        "monthly cost", "annual cost", "pricing breakdown",
        "cost analysis", "cost breakdown", "cost calculation",
        "cost comparison", "cost optimization",
    ]

    explicit_cost = any(keyword in user_message for keyword in cost_keywords)
    next_stage = state.get("next_stage")

    if explicit_cost:
        # Prefer existing architecture when available.
        project_state = state.get("current_project_state") or {}
        has_architecture = bool(project_state.get("candidateArchitectures"))

        if has_architecture:
            logger.info("💰 Routing to Cost Estimator: explicit cost request + architecture exists")
            return True

        # Service-based pricing requests can be estimated without a finalized
        # candidate architecture by asking assumptions/quantities first.
        if _has_service_pricing_signals(user_message):
            logger.info("💰 Routing to Cost Estimator: explicit cost request + service signals")
            return True

        # Route anyway for clarification-first pricing instead of falling back
        # to generic agent loops.
        logger.info(
            "💰 Routing to Cost Estimator: explicit cost request without finalized architecture"
        )
        return True

    # Check project stage
    if next_stage == ProjectStage.PRICING.value:
        logger.info("💰 Routing to Cost Estimator: project stage is 'pricing'")
        return True

    return False


def _has_service_pricing_signals(user_message: str) -> bool:
    """Detect service hints in user text for pricing-first workflows."""
    service_tokens = [
        "swa",
        "static web app",
        "static web apps",
        "azure function",
        "function app",
        "table storage",
        "storage account",
        "blob storage",
        "sql database",
        "cosmos db",
        "app service",
        "aks",
        "api management",
        "service bus",
        "event hub",
        "front door",
        "application gateway",
        "redis",
        "key vault",
    ]
    return any(token in user_message for token in service_tokens)


def prepare_cost_estimator_handoff(state: GraphState) -> dict[str, Any]:
    """
    Prepare handoff context for Cost Estimator sub-agent.

    Extracts architecture, resource list, and constraints to pass
    to the specialized cost estimation agent.

    Args:
        state: Current graph state

    Returns:
        State update with agent_handoff_context for Cost Estimator
    """
    project_state = state.get("current_project_state") or {}
    context_summary = state.get("context_summary") or ""

    # Extract architecture (use first candidate if multiple)
    candidate_architectures = project_state.get("candidateArchitectures") or []
    architecture = candidate_architectures[0] if candidate_architectures else {}

    # Extract resource list from architecture
    resource_list = _extract_resource_list(architecture, context_summary)

    # Detect region from user message or requirements
    user_message = state.get("user_message", "").lower()
    requirements = project_state.get("requirements") or {}
    region = _detect_region(user_message, requirements)

    # Detect environment (production, dev, test)
    environment = _detect_environment(user_message, context_summary)

    # Extract constraints
    req_params = requirements if isinstance(requirements, dict) else {}
    constraints = {
        "budget": req_params.get("budget"),
        "reserved_instances": "reserved instance" in user_message or "ri" in user_message,
        "azure_hybrid_benefit": "ahb" in user_message or "hybrid benefit" in user_message,
        "spot_instances": "spot" in user_message,
        "compliance": req_params.get("compliance", []),
    }
    # Remove None/False values
    constraints = {k: v for k, v in constraints.items() if v}

    handoff_context = {
        "project_context": context_summary,
        "architecture": architecture,
        "resource_list": resource_list,
        "region": region,
        "environment": environment,
        "constraints": constraints,
        "user_request": state.get("user_message", ""),
        "routing_reason": "Cost estimation requested for finalized architecture",
    }

    logger.info(
        f"Prepared Cost Estimator handoff context: "
        f"region={region}, environment={environment}, {len(resource_list)} resources"
    )

    return {
        "agent_handoff_context": handoff_context,
        "current_agent": "cost_estimator",
    }


def _detect_region(user_message: str, requirements: dict[str, Any]) -> str:
    """
    Detect Azure region from user message or requirements.

    Args:
        user_message: User's message
        requirements: Project requirements

    Returns:
        Azure region (defaults to eastus)
    """
    # Common Azure regions
    regions = [
        "eastus", "eastus2", "westus", "westus2", "westus3",
        "centralus", "northcentralus", "southcentralus",
        "westcentralus", "canadacentral", "canadaeast",
        "brazilsouth", "northeurope", "westeurope",
        "uksouth", "ukwest", "francecentral", "germanywestcentral",
        "switzerlandnorth", "norwayeast", "swedencentral",
        "eastasia", "southeastasia", "japaneast", "japanwest",
        "australiaeast", "australiasoutheast", "centralindia",
        "southindia", "westindia",
    ]

    # Check user message
    for region in regions:
        if region in user_message:
            return region

    # Check requirements
    req_params = requirements if isinstance(requirements, dict) else {}
    allowed_regions = req_params.get("allowedRegions", [])
    if allowed_regions:
        return allowed_regions[0]

    # Default to East US
    return "eastus"


def _detect_environment(user_message: str, context_summary: str) -> str:
    """
    Detect environment type (production, dev, test).

    Args:
        user_message: User's message
        context_summary: Context summary

    Returns:
        Environment type (defaults to production)
    """
    combined_text = f"{user_message} {context_summary}".lower()

    if any(keyword in combined_text for keyword in ["dev", "development", "sandbox"]):
        return "development"
    elif any(keyword in combined_text for keyword in ["test", "testing", "qa", "staging"]):
        return "test"
    elif any(keyword in combined_text for keyword in ["prod", "production"]):
        return "production"

    # Default to production for cost estimates
    return "production"

