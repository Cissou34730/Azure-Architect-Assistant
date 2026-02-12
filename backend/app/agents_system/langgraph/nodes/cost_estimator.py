"""
Cost Estimator Node - Specialized agent for Azure cost estimation.

This module provides a specialized sub-agent for calculating Azure cost estimates
using the Azure Retail Prices API and providing optimization recommendations.
"""

import logging
import re
from typing import Any

from app.agents_system.services.state_update_parser import extract_state_updates
from app.agents_system.tools.aaa_cost_tool import AAAGenerateCostTool

from ..state import GraphState

logger = logging.getLogger(__name__)


async def cost_estimator_node(state: GraphState) -> dict[str, Any]:
    """
    Specialized node for Azure cost estimation.

    This node is invoked when:
    - User requests "cost", "price", "pricing", "how much"
    - User asks for "TCO", "total cost of ownership", "budget"
    - Finalized architecture exists in project state

    The Cost Estimator specializes in:
    - Azure Retail Prices API integration
    - Cost calculation (hourly → monthly → annual → 3-year TCO)
    - Service and SKU identification
    - Regional pricing differences
    - Reserved Instance and cost optimization recommendations
    - Pricing breakdown by service

    Args:
        state: Current graph state with project context and architecture

    Returns:
        Updated state with cost estimate
    """
    logger.info("💰 Cost Estimator Agent activated")

    try:
        # Prepare handoff context for cost estimator
        handoff_context = state.get("agent_handoff_context", {})
        project_context = handoff_context.get("project_context", "")
        architecture = handoff_context.get("architecture", "")
        resource_list = handoff_context.get("resource_list", [])
        region = handoff_context.get("region", "eastus")
        environment = handoff_context.get("environment", "production")

        # Get user's original request
        user_message = state.get("user_message", "")
        combined_text = _combined_pricing_text(
            user_message=user_message,
            resource_list=resource_list,
            architecture=architecture,
            project_context=project_context,
        )
        baseline_requested = _is_baseline_assumptions_requested(user_message)
        minimum_inputs_available = _minimum_pricing_inputs_available(user_message)
        has_supported_services = _has_supported_pricing_services(combined_text)

        if _needs_pricing_clarification(
            architecture=architecture,
            resource_list=resource_list,
            baseline_requested=baseline_requested,
            minimum_inputs_available=minimum_inputs_available,
            has_supported_services=has_supported_services,
        ):
            clarification = _build_cost_clarification_message(
                region=region,
                environment=environment,
            )
            logger.info("Cost Estimator returning clarification-first response")
            return {
                "agent_output": clarification,
                "intermediate_steps": state.get("intermediate_steps", []),
                "current_agent": "cost_estimator",
                "sub_agent_output": clarification,
                "cost_estimate": None,
                "success": True,
                "error": None,
            }

        should_run_deterministic = (
            has_supported_services
            or not _is_resource_list_missing(resource_list)
            or not _is_architecture_missing(architecture)
        )
        heuristic_lines = (
            _build_heuristic_pricing_lines(
                combined_text=combined_text,
                resource_list=resource_list,
                region=region,
                environment=environment,
            )
            if should_run_deterministic
            else []
        )
        validated_lines = _validate_pricing_lines_for_execution(heuristic_lines)
        if validated_lines:
            logger.info(
                "Cost Estimator using deterministic pricing tool path (lines=%d)",
                len(validated_lines),
            )
            deterministic_output = await _run_deterministic_cost_estimate(
                pricing_lines=validated_lines,
                region=region,
                environment=environment,
            )
            if deterministic_output is not None:
                if has_supported_services and not minimum_inputs_available and not baseline_requested:
                    return _append_refinement_questions(
                        deterministic_output=deterministic_output,
                        region=region,
                        environment=environment,
                    )
                return deterministic_output

        unsupported_message = _build_pricing_unavailable_message(
            user_message=user_message,
            region=region,
            environment=environment,
        )
        logger.info("Cost Estimator returning deterministic-unavailable clarification")
        return {
            "agent_output": unsupported_message,
            "intermediate_steps": state.get("intermediate_steps", []),
            "current_agent": "cost_estimator",
            "sub_agent_output": unsupported_message,
            "cost_estimate": None,
            "success": True,
            "error": None,
        }

    except Exception as exc:
        logger.error(f"❌ Cost Estimator failed: {exc}", exc_info=True)

        # Graceful fallback: Return error but don't break the workflow
        error_msg = (
            f"Cost Estimator encountered an error: {exc!s}\n\n"
            "Falling back to main agent for cost guidance. "
            "The main agent will provide best-effort cost estimates based on available data."
        )

        return {
            "agent_output": error_msg,
            "current_agent": "main",  # Fallback to main agent
            "sub_agent_output": None,
            "cost_estimate": None,
            "success": False,
            "error": str(exc),
        }


def _format_resource_list(resources: list[str]) -> str:
    """Format list of Azure resources for display."""
    if not resources:
        return "No resources identified. Please provide architecture details."

    formatted = []
    for idx, resource in enumerate(resources, 1):
        formatted.append(f"{idx}. {resource}")

    return "\n".join(formatted)


def _format_constraints(constraints: dict[str, Any]) -> str:
    """Format constraints dictionary for display."""
    if not constraints:
        return "No explicit constraints provided."

    formatted = []
    if "budget" in constraints:
        formatted.append(f"- Budget: {constraints['budget']}")
    if "timeline" in constraints:
        formatted.append(f"- Timeline: {constraints['timeline']}")
    if "compliance" in constraints:
        formatted.append(f"- Compliance: {', '.join(constraints['compliance'])}")
    if "regions" in constraints:
        formatted.append(f"- Allowed Regions: {', '.join(constraints['regions'])}")

    return "\n".join(formatted) if formatted else "No explicit constraints provided."


def _extract_cost_summary(cost_estimate: str) -> dict[str, Any]:
    """
    Extract cost summary from cost estimate text.

    Looks for monthly, annual, and TCO values in the estimate.

    Args:
        cost_estimate: Cost estimate text from agent

    Returns:
        Dictionary with monthly_cost, annual_cost, tco_3_year
    """
    summary: dict[str, Any] = {
        "monthly_cost": None,
        "annual_cost": None,
        "tco_3_year": None,
        "currency": "USD",
        "region": "eastus",
    }

    # Extract monthly cost
    monthly_patterns = [
        r"\*\*Monthly\*\*[:\s]*\$?([\d,]+\.?\d*)",
        r"Monthly Cost[:\s]*\$?([\d,]+\.?\d*)",
        r"Total Monthly[:\s]*\$?([\d,]+\.?\d*)",
    ]

    summary["monthly_cost"] = _extract_cost_value(cost_estimate, monthly_patterns)

    # Extract annual cost
    annual_patterns = [
        r"\*\*Annual\*\*[:\s]*\$?([\d,]+\.?\d*)",
        r"Annual Cost[:\s]*\$?([\d,]+\.?\d*)",
        r"Total Annual[:\s]*\$?([\d,]+\.?\d*)",
    ]

    summary["annual_cost"] = _extract_cost_value(cost_estimate, annual_patterns)

    # Extract 3-year TCO
    tco_patterns = [
        r"\*\*3-Year TCO\*\*[:\s]*\$?([\d,]+\.?\d*)",
        r"3-Year TCO[:\s]*\$?([\d,]+\.?\d*)",
        r"Total 3-Year[:\s]*\$?([\d,]+\.?\d*)",
    ]

    summary["tco_3_year"] = _extract_cost_value(cost_estimate, tco_patterns)

    # If annual not found but monthly exists, calculate
    if summary["annual_cost"] is None and summary["monthly_cost"]:
        summary["annual_cost"] = summary["monthly_cost"] * 12

    # If TCO not found but annual exists, calculate
    if summary["tco_3_year"] is None and summary["annual_cost"]:
        summary["tco_3_year"] = summary["annual_cost"] * 3

    return summary


def _extract_cost_value(cost_estimate: str, patterns: list[str]) -> float | None:
    """Extract a numeric cost value matching the provided patterns."""
    for pattern in patterns:
        match = re.search(pattern, cost_estimate, re.IGNORECASE)
        if not match:
            continue
        value = _parse_cost_value(match.group(1))
        if value is not None:
            return value
    return None


def _parse_cost_value(value: str) -> float | None:
    """Parse a numeric cost value from a string, returning None on failure."""
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


def _needs_pricing_clarification(
    *,
    architecture: Any,
    resource_list: list[str],
    baseline_requested: bool,
    minimum_inputs_available: bool,
    has_supported_services: bool,
) -> bool:
    """Return True when the cost estimator lacks enough sizing inputs."""
    architecture_missing = _is_architecture_missing(architecture)
    resources_missing = _is_resource_list_missing(resource_list)

    # If services are recognizable, produce a baseline estimate immediately and
    # then request sizing details for refinement.
    if has_supported_services:
        return False

    # If both architecture and service sizing are weak, clarify first.
    if (
        architecture_missing
        and resources_missing
        and not minimum_inputs_available
        and not baseline_requested
    ):
        return True

    # If there is no architecture and no sizing hints, avoid tool loops.
    if (
        architecture_missing
        and not minimum_inputs_available
        and not baseline_requested
    ):
        return True

    return False


def _is_architecture_missing(architecture: Any) -> bool:
    if not architecture:
        return True
    if isinstance(architecture, dict):
        meaningful_keys = ("description", "components", "diagram", "title", "summary")
        return not any(bool(architecture.get(key)) for key in meaningful_keys)
    return False


def _is_resource_list_missing(resource_list: list[str]) -> bool:
    if not resource_list:
        return True
    if len(resource_list) != 1:
        return False
    only_item = resource_list[0].strip().lower()
    return (
        "extract from architecture description" in only_item
        or "no resources identified" in only_item
    )


def _has_sizing_or_usage_hints(user_message: str) -> bool:
    text = (user_message or "").lower()
    patterns = [
        r"\b\d+\s*(instance|instances|apps|functions|gb|tb|rps|requests?/s|users?)\b",
        r"\b(sku|tier|plan|consumption|premium|standard|basic|s\d|p\d|ep\d)\b",
        r"\b(monthly|annual|per month|24/7|always on|on-demand)\b",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def _build_cost_clarification_message(
    *,
    region: str,
    environment: str,
) -> str:
    return (
        "I can estimate this, but I need a few pricing inputs first to avoid inaccurate numbers.\n\n"
        "Please confirm:\n"
        "1. Region (current default: " + region + ")\n"
        "2. Environment (current default: " + environment + ")\n"
        "3. Core Azure services in scope (if not already finalized)\n"
        "4. Expected compute usage (instances/hours or executions)\n"
        "5. Expected data/storage usage (GB and operations)\n\n"
        "If you prefer, reply with: `use baseline assumptions` and I will run a provisional estimate now."
    )


def _combined_pricing_text(
    *,
    user_message: str,
    resource_list: list[str],
    architecture: Any,
    project_context: str,
) -> str:
    resource_text = " ".join(resource_list) if resource_list else ""
    architecture_text = ""
    if isinstance(architecture, dict):
        architecture_text = " ".join(
            str(architecture.get(key, ""))
            for key in ("title", "summary", "description", "diagram")
        )
    elif architecture:
        architecture_text = str(architecture)
    return f"{user_message} {resource_text} {architecture_text} {project_context}".lower()


def _has_supported_pricing_services(combined_text: str) -> bool:
    service_markers = [
        "swa",
        "static web app",
        "static web apps",
        "azure function",
        "function app",
        "functions",
        "app service",
        "storage account",
        "blob storage",
        "sql database",
        "database for postgresql",
        "database for mysql",
        "key vault",
        "application insights",
        "api management",
        "service bus",
        "event hub",
        "event grid",
        "front door",
        "application gateway",
        "redis",
        "virtual machine",
        "aks",
        "table storage",
        "cosmos db",
        "azure cosmos db",
    ]
    return any(marker in combined_text for marker in service_markers)


def _is_baseline_assumptions_requested(user_message: str) -> bool:
    text = (user_message or "").lower()
    triggers = [
        "use baseline assumptions",
        "baseline assumptions",
        "use assumptions",
        "proceed with assumptions",
        "use default assumptions",
    ]
    return any(trigger in text for trigger in triggers)


def _minimum_pricing_inputs_available(user_message: str) -> bool:
    """Minimum viable input gate before executing pricing calls."""
    return _has_sizing_or_usage_hints(user_message)


def _build_heuristic_pricing_lines(
    *,
    combined_text: str,
    resource_list: list[str],
    region: str,
    environment: str,
) -> list[dict[str, Any]]:
    """Build baseline pricing lines from common service mentions."""
    lines: list[dict[str, Any]] = []
    instance_count = _extract_first_int(combined_text, r"(\d+)\s*(?:instance|instances)") or 1
    storage_gb = _extract_first_int(combined_text, r"(\d+)\s*gb") or 100
    monthly_exec = _extract_first_int(
        combined_text, r"(\d[\d,]*)\s*(?:executions|execution|requests)"
    ) or 1_000_000

    if "swa" in combined_text or "static web app" in combined_text:
        tier_hint = _extract_tier_hint(combined_text)
        lines.append(
            {
                "name": "Static Web Apps baseline",
                "serviceName": "Static Web Apps",
                "armRegionName": region,
                "productNameContains": tier_hint,
                "meterNameContains": tier_hint,
                "monthlyQuantity": float(max(instance_count, 1) * 730),
            }
        )

    if (
        "azure function" in combined_text
        or "function app" in combined_text
        or "functions" in combined_text
    ):
        if "premium" in combined_text:
            lines.append(
                {
                    "name": "Azure Functions Premium baseline",
                    "serviceName": "Functions",
                    "armRegionName": region,
                    "productNameContains": "Functions",
                    "meterNameContains": "Premium",
                    "monthlyQuantity": float(max(instance_count, 1) * 730),
                }
            )
        else:
            lines.append(
                {
                    "name": "Azure Functions executions baseline",
                    "serviceName": "Functions",
                    "armRegionName": region,
                    "productNameContains": "Functions",
                    "meterNameContains": "Execution",
                    "monthlyQuantity": float(max(monthly_exec, 1)),
                }
            )

    if "table storage" in combined_text:
        lines.append(
            {
                "name": "Table Storage capacity baseline",
                "serviceName": "Storage",
                "armRegionName": region,
                "productNameContains": "Table",
                "meterNameContains": "Data Stored",
                "monthlyQuantity": float(max(storage_gb, 1)),
            }
        )

    if "cosmos db" in combined_text or "azure cosmos db" in combined_text:
        lines.append(
            {
                "name": "Azure Cosmos DB autoscale baseline",
                "serviceName": "Azure Cosmos DB",
                "armRegionName": region,
                "productNameContains": "Azure Cosmos DB autoscale",
                "meterNameContains": "100 RUs",
                "monthlyQuantity": float(max(instance_count, 1) * 730),
            }
        )

    lines.extend(
        _build_resource_driven_pricing_lines(
            combined_text=combined_text,
            resource_list=resource_list,
            region=region,
            instance_count=instance_count,
            storage_gb=storage_gb,
            monthly_exec=monthly_exec,
        )
    )
    lines = _dedupe_pricing_lines(lines)

    # For development, use reduced baseline quantity for always-on compute.
    if environment.lower().startswith("dev"):
        for line in lines:
            if "monthlyQuantity" in line and "baseline" in str(line.get("name", "")).lower():
                line["monthlyQuantity"] = float(line["monthlyQuantity"]) * 0.4

    return lines


def _validate_pricing_lines_for_execution(
    pricing_lines: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Executor-side guardrail before calling pricing APIs."""
    valid: list[dict[str, Any]] = []
    required_keys = ("name", "serviceName", "armRegionName", "monthlyQuantity")
    for line in pricing_lines:
        if not isinstance(line, dict):
            continue
        if any(key not in line for key in required_keys):
            continue
        qty = line.get("monthlyQuantity")
        if not isinstance(qty, (int, float)) or qty <= 0:
            continue
        valid.append(line)
    return valid


def _extract_first_int(text: str, pattern: str) -> int | None:
    match = re.search(pattern, text)
    if not match:
        return None
    raw = match.group(1).replace(",", "")
    try:
        return int(raw)
    except ValueError:
        return None


def _extract_tier_hint(text: str) -> str | None:
    lowered = (text or "").lower()
    known_tiers = [
        "free",
        "standard",
        "premium",
        "basic",
        "consumption",
        "serverless",
    ]
    for tier in known_tiers:
        if tier in lowered:
            return tier.title()
    return None


def _build_resource_driven_pricing_lines(
    *,
    combined_text: str,
    resource_list: list[str],
    region: str,
    instance_count: int,
    storage_gb: int,
    monthly_exec: int,
) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    text = f"{combined_text} {' '.join(resource_list).lower() if resource_list else ''}"

    # Generic resource-to-pricing hints. No hardcoded SKU proxy replacement.
    mappings = [
        ("app service", "Azure App Service", "App Service baseline", "Standard", float(max(instance_count, 1) * 730)),
        ("storage account", "Storage", "Storage Account baseline", "Data Stored", float(max(storage_gb, 1))),
        ("blob storage", "Storage", "Blob Storage baseline", "Data Stored", float(max(storage_gb, 1))),
        ("sql database", "SQL Database", "SQL Database baseline", "General Purpose", float(max(instance_count, 1) * 730)),
        ("postgresql", "Azure Database for PostgreSQL", "PostgreSQL baseline", "General Purpose", float(max(instance_count, 1) * 730)),
        ("mysql", "Azure Database for MySQL", "MySQL baseline", "General Purpose", float(max(instance_count, 1) * 730)),
        ("key vault", "Key Vault", "Key Vault operations baseline", "Operations", float(max(monthly_exec, 100_000))),
        ("application insights", "Application Insights", "Application Insights baseline", "Data Ingestion", float(max(storage_gb, 10))),
        ("api management", "API Management", "API Management baseline", "Consumption", float(max(monthly_exec, 1_000_000))),
        ("service bus", "Service Bus", "Service Bus operations baseline", "Operations", float(max(monthly_exec, 1_000_000))),
        ("event hub", "Event Hubs", "Event Hubs throughput baseline", "Throughput", float(max(instance_count, 1) * 730)),
        ("event grid", "Event Grid", "Event Grid operations baseline", "Operations", float(max(monthly_exec, 1_000_000))),
        ("front door", "Azure Front Door", "Front Door baseline", "Requests", float(max(monthly_exec, 1_000_000))),
        ("application gateway", "Application Gateway", "Application Gateway baseline", "Gateway", float(max(instance_count, 1) * 730)),
        ("redis", "Azure Cache for Redis", "Redis baseline", "Cache", float(max(instance_count, 1) * 730)),
        ("virtual machine", "Virtual Machines", "Virtual Machines baseline", "Compute", float(max(instance_count, 1) * 730)),
        ("aks", "Virtual Machines", "AKS node compute baseline", "Compute", float(max(instance_count, 3) * 730)),
    ]

    for token, service_name, name, meter_name, monthly_quantity in mappings:
        if token not in text:
            continue
        lines.append(
            {
                "name": name,
                "serviceName": service_name,
                "armRegionName": region,
                "productNameContains": service_name,
                "meterNameContains": meter_name,
                "monthlyQuantity": monthly_quantity,
            }
        )

    # Generic fallback: keep discovery open even for services not in mappings.
    for resource in resource_list:
        resource_name = _normalize_resource_name(resource)
        if not resource_name:
            continue
        lines.append(
            {
                "name": f"{resource_name} baseline",
                "serviceName": resource_name,
                "armRegionName": region,
                "productNameContains": resource_name,
                "meterNameContains": None,
                "monthlyQuantity": float(max(instance_count, 1) * 730),
            }
        )

    return lines


def _dedupe_pricing_lines(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    deduped: list[dict[str, Any]] = []
    for line in lines:
        key = (
            line.get("name"),
            line.get("serviceName"),
            line.get("armRegionName"),
            line.get("productNameContains"),
            line.get("meterNameContains"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(line)
    return deduped


def _normalize_resource_name(resource: str) -> str:
    text = (resource or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    if "extract from architecture description" in lowered or "no resources identified" in lowered:
        return ""
    if "(" in text and ")" in text:
        start = text.find("(")
        end = text.find(")", start + 1)
        if end > start:
            candidate = text[start + 1:end].strip()
            if candidate:
                return candidate
    return text


async def _run_deterministic_cost_estimate(
    *,
    pricing_lines: list[dict[str, Any]],
    region: str,
    environment: str,
) -> dict[str, Any] | None:
    tool = AAAGenerateCostTool()
    tool_response = await tool._arun(payload={"pricingLines": pricing_lines})
    if not tool_response or tool_response.startswith("ERROR:"):
        logger.warning("Deterministic cost tool call failed: %s", tool_response[:200])
        return None

    updates = extract_state_updates(tool_response, user_message="", current_state={}) or {}
    cost_estimates = updates.get("costEstimates")
    estimate = cost_estimates[0] if isinstance(cost_estimates, list) and cost_estimates else {}
    total_monthly = estimate.get("totalMonthlyCost")
    currency = estimate.get("currencyCode", "USD")
    annual = float(total_monthly) * 12 if isinstance(total_monthly, (int, float)) else None
    line_items = estimate.get("lineItems", []) if isinstance(estimate, dict) else []
    gaps = estimate.get("pricingGaps", []) if isinstance(estimate, dict) else []

    if (not line_items) and isinstance(gaps, list) and gaps:
        logger.warning(
            "Deterministic pricing returned no matched line items (gaps=%d)",
            len(gaps),
        )
        return None

    summary_lines = [
        "## Baseline Cost Estimate (deterministic pricing API path)",
        f"- Region: `{region}`",
        f"- Environment: `{environment}`",
    ]
    if isinstance(total_monthly, (int, float)):
        summary_lines.append(f"- Estimated Monthly Total: `{currency} {total_monthly:,.2f}`")
    if isinstance(annual, float):
        summary_lines.append(f"- Estimated Annual Total: `{currency} {annual:,.2f}`")
    if isinstance(gaps, list) and gaps:
        summary_lines.append(
            f"- Pricing gaps: `{len(gaps)}` lines could not be matched exactly and were excluded."
        )
    summary_lines.append(
        "- Assumptions: baseline quantities were inferred from your message; provide exact SKUs/usage for a tighter estimate."
    )

    return {
        "agent_output": "\n".join(summary_lines) + "\n\n" + tool_response,
        "intermediate_steps": [],
        "current_agent": "cost_estimator",
        "sub_agent_output": "\n".join(summary_lines),
        "cost_estimate": estimate if isinstance(estimate, dict) else None,
        "success": True,
        "error": None,
    }


def _append_refinement_questions(
    *,
    deterministic_output: dict[str, Any],
    region: str,
    environment: str,
) -> dict[str, Any]:
    """Append clarification prompts after emitting a baseline estimate."""
    follow_up = (
        "\n\nTo refine this estimate, please confirm:\n"
        f"1. Region (current default: {region})\n"
        f"2. Environment (current default: {environment})\n"
        "3. Target tiers/plans for core services\n"
        "4. Compute usage profile (hours/instances or executions)\n"
        "5. Data/storage usage profile (GB and operations)"
    )
    output = str(deterministic_output.get("agent_output", "")) + follow_up
    deterministic_output["agent_output"] = output
    deterministic_output["sub_agent_output"] = str(
        deterministic_output.get("sub_agent_output", "")
    ) + follow_up
    return deterministic_output


def _build_pricing_unavailable_message(
    *,
    user_message: str,
    region: str,
    environment: str,
) -> str:
    requested = user_message.strip() or "your requested services"
    return (
        "I could not build a reliable pricing-line mapping from the current project context.\n\n"
        f"Request: {requested}\n"
        f"Region: {region}\n"
        f"Environment: {environment}\n\n"
        "Please provide one of these to proceed:\n"
        "1. A short list of core services in your solution (no SKU needed), or\n"
        "2. Approx usage assumptions (instances, GB, requests/executions), or\n"
        "3. A finalized architecture artifact so I can auto-derive services and discover matching SKUs.\n\n"
        "I will infer serviceName/SKU/meter automatically from available architecture context and pricing catalog."
    )
