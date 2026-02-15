"""
Agent execution node for LangGraph workflow.

Stage-aware execution using the LangGraph-native tool loop.
Falls back to the legacy orchestrator if native execution fails.
"""

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from ...runner import get_agent_runner
from ..state import GraphState
from .agent_native import run_stage_aware_agent

logger = logging.getLogger(__name__)

_PILLAR_ALIASES: dict[str, tuple[str, ...]] = {
    "Reliability": ("reliability", "reliabilty", "reliablity", "resilience", "resiliency"),
    "Security": ("security",),
    "Cost Optimization": ("cost optimization", "cost", "finops"),
    "Operational Excellence": ("operational excellence", "operations"),
    "Performance Efficiency": ("performance efficiency", "performance"),
}

_SCOPE_REFUSAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"i cannot assist with this topic", re.IGNORECASE),
    re.compile(r"scope is restricted", re.IGNORECASE),
    re.compile(r"out[-\s]?of[-\s]?scope", re.IGNORECASE),
)

# ---------------------------------------------------------------------------
# Scope-detection vocabulary
# ---------------------------------------------------------------------------
# All patterns use word-boundary matching (\b) compiled once at import time
# to avoid substring false-positives (e.g. "cost" inside "Acosta").
# ---------------------------------------------------------------------------

# Domain keywords — a hit on any of these is a strong in-scope signal.
_IN_SCOPE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
    for kw in (
        # Core domain
        "azure",
        "architecture",
        "architect",
        "project",
        "checklist",
        "waf",
        "well-architected",
        "well architected",
        # WAF pillars
        "reliability",
        "security",
        "cost optimization",
        "cost",
        "operational excellence",
        "performance efficiency",
        # Artifacts / concepts
        "adr",
        "decision record",
        "diagram",
        "mermaid",
        "c4 model",
        "iac",
        "terraform",
        "bicep",
        "arm template",
        "nfr",
        "non-functional",
        "validation",
        "finding",
        "traceability",
        "candidate architecture",
        "mind map",
        "requirements",
        "requirement",
        "assumptions",
        "assumption",
        "open questions",
        "clarification",
        "mcp",
        # Azure services & infra concepts
        "vm",
        "virtual machine",
        "container",
        "kubernetes",
        "aks",
        "app service",
        "function app",
        "storage account",
        "cosmos",
        "sql database",
        "sql server",
        "blob",
        "redis",
        "service bus",
        "event hub",
        "event grid",
        "api management",
        "apim",
        "front door",
        "application gateway",
        "load balancer",
        "vpn",
        "vnet",
        "subnet",
        "nsg",
        "firewall",
        "bastion",
        "key vault",
        "managed identity",
        "rbac",
        "entra",
        "active directory",
        "monitor",
        "log analytics",
        "app insights",
        "application insights",
        # Architecture / engineering terms
        "microservice",
        "monolith",
        "saas",
        "paas",
        "iaas",
        "serverless",
        "multi-tenant",
        "single-tenant",
        "deployment",
        "deploy",
        "ci/cd",
        "pipeline",
        "migration",
        "migrate",
        "scalability",
        "scale",
        "scaling",
        "latency",
        "throughput",
        "availability",
        "disaster recovery",
        "failover",
        "backup",
        "sla",
        "rto",
        "rpo",
        "region",
        "zone",
        "geo-redundant",
        "compliance",
        "hipaa",
        "gdpr",
        "soc 2",
        "pci dss",
        "iso 27001",
        "encryption",
        "tls",
        "ssl",
        "oauth",
        "authentication",
        "authorization",
        "endpoint",
        "api",
        "rest",
        "graphql",
        "grpc",
        "web app",
        "database",
        "caching",
        "cdn",
        "dns",
        "domain",
        "certificate",
        "tco",
        "budget",
        "pricing",
        "estimate",
        "infrastructure",
        "devops",
        "observability",
        "monitoring",
        "alerting",
        "logging",
        "telemetry",
        "data flow",
        "workflow",
        "integration",
        "queue",
        "pub/sub",
        "networking",
        "topology",
        "tier",
    )
)

# Action verbs — imply the user wants to *do* something to the project.
_ACTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"\b{re.escape(verb)}\b", re.IGNORECASE)
    for verb in (
        "create",
        "update",
        "delete",
        "remove",
        "add",
        "set",
        "mark",
        "uncheck",
        "check",
        "generate",
        "analyze",
        "analyse",
        "validate",
        "review",
        "propose",
        "suggest",
        "compare",
        "evaluate",
        "assess",
        "refactor",
        "redesign",
        "implement",
        "plan",
        "define",
        "document",
        "export",
        "summarize",
        "list",
        "show",
        "explain",
        "describe",
        "recommend",
        "improve",
        "optimize",
        "configure",
        "provision",
        "audit",
    )
)

# Off-topic phrases — must be *phrases at word boundaries* to avoid false
# positives (e.g. "travel" matching "traversal").  The guardrail only blocks
# retry when *multiple* off-topic signals are present AND zero in-scope
# signals exist.
_OFF_TOPIC_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
    for phrase in (
        "tell me a joke",
        "joke",
        "weather forecast",
        "weather today",
        "movie recommendation",
        "movie review",
        "sports score",
        "sports news",
        "political opinion",
        "politics",
        "dating advice",
        "love life",
        "recipe",
        "cook",
        "horoscope",
        "astrology",
        "song lyrics",
        "play a game",
        "trivia",
        "riddle",
        "poem",
        "story",
        "fiction",
    )
)

# ---------------------------------------------------------------------------
# Pre-filter: detect requests that are clearly outside the assistant's role
# ---------------------------------------------------------------------------
# These patterns detect generic coding/scripting requests, homework, or
# unrelated topics that have NOTHING to do with the Azure architecture
# project the user is working on.  The pre-filter fires only when:
#   1. At least one _GENERIC_REQUEST_PATTERNS matches, AND
#   2. Zero _IN_SCOPE_PATTERNS match (no Azure/architecture/project signal).
# This avoids blocking e.g. "write a Python script that deploys to Azure".
# ---------------------------------------------------------------------------

_GENERIC_REQUEST_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        # Generic coding tasks
        r"\b(?:write|create|build|make|code|implement|develop)\b.{0,30}\b(?:python|javascript|typescript|java|c\+\+|c#|ruby|go|rust|php|perl|bash|shell|powershell)\s+(?:script|program|code|function|class|app|application|bot|tool|utility|game)\b",
        r"\b(?:write|create|build|make|code|implement)\b.{0,20}\b(?:script|program|code|function|class)\b.{0,30}\b(?:that|which|to)\b.{0,40}\b(?:sort|parse|convert|calculate|count|sum|multiply|divide|reverse|filter|merge|split|extract|download|scrape|crawl|fetch|send|email|sms|tweet)\b",
        r"\b(?:write|create|build|make)\b.{0,20}\b(?:a|an|the|me a|me an)\b\s+\b(?:script|program|bot|game|calculator|converter|scraper|crawler|chatbot|todo|to-do|cli|gui|todo app|to-do app)\b",
        # Generic app/tool building with language specified
        r"\b(?:write|create|build|make|develop)\b.{0,30}\b(?:app|application|tool|utility|website|web app|desktop app|mobile app)\b.{0,20}\b(?:in|using|with)\b\s+\b(?:python|javascript|typescript|java|c\+\+|c#|ruby|go|rust|react|vue|angular|svelte|next\.?js|flask|django|express|node)\b",
        # Algorithm / data-structure homework
        r"\b(?:implement|write|code)\b.{0,20}\b(?:bubble sort|quick sort|merge sort|insertion sort|binary search|linked list|binary tree|hash table|heap|stack|queue|graph traversal|bfs|dfs|dijkstra|fibonacci|factorial|palindrome|anagram|permutation)\b",
        # Generic how-to coding questions with no project context
        r"\bhow (?:do i|to|can i)\b.{0,20}\b(?:sort a list|reverse a string|read a file|write a file|open a file|parse json|parse xml|parse csv|make a request|http request|loop through|iterate over)\b.{0,20}\bin (?:python|javascript|java|c\+\+|c#|ruby|go|rust)\b",
        # Clearly personal / entertainment
        r"\b(?:write|tell|give|sing|compose)\b.{0,15}\b(?:me|us)\b.{0,15}\b(?:a joke|a poem|a song|a story|a limerick|a haiku|a riddle)\b",
        r"\bwhat(?:'s| is)\b.{0,15}\b(?:the weather|my horoscope|the score|the news)\b",
        r"\b(?:play|let's play)\b.{0,10}\b(?:a game|trivia|guess|rock paper|tic tac)\b",
        # Translation / language tasks
        r"\btranslate\b.{0,20}\b(?:to|into|from)\b.{0,20}\b(?:french|spanish|german|italian|portuguese|chinese|japanese|korean|arabic|hindi|russian)\b",
        # Math homework
        r"\b(?:solve|calculate|compute|evaluate|simplify|factor|derive|integrate)\b.{0,20}\b(?:equation|integral|derivative|matrix|polynomial|expression|limit)\b",
    )
)

_OUT_OF_SCOPE_REDIRECT = (
    "I'm the Azure Architect Assistant — I help with Azure architecture design, "
    "WAF assessments, requirements analysis, ADRs, IaC generation, and cost estimation "
    "for your project.\n\n"
    "Your request doesn't seem related to the project's architecture work. "
    "Could you rephrase it in the context of your project, or ask me something about "
    "your Azure architecture instead?"
)


def _is_out_of_scope_request(user_message: str) -> bool:
    """Return True if the request is clearly unrelated to the project.

    The check is deliberately conservative (high precision): it only fires
    when a generic-request pattern matches AND no domain keyword is present.
    This means it will never block a legitimate project request that happens
    to mention a programming language (e.g. "write a Bicep script to deploy
    my architecture").
    """
    # If ANY domain keyword is present, the request is in-scope — skip.
    if any(pat.search(user_message) for pat in _IN_SCOPE_PATTERNS):
        return False

    # Check if a generic request pattern matches.
    if any(pat.search(user_message) for pat in _GENERIC_REQUEST_PATTERNS):
        return True

    # Pure off-topic (jokes, weather, etc.) with no domain signal.
    off_topic_hits = sum(1 for pat in _OFF_TOPIC_PATTERNS if pat.search(user_message))
    if off_topic_hits >= 1:
        return True

    return False


async def run_agent_node(state: GraphState) -> dict[str, Any]:
    """
    Execute agent with project context and stage directives.

    Args:
        state: Current graph state

    Returns:
        State update with agent output and intermediate steps
    """
    user_message = state["user_message"]

    # ── Pre-filter: block clearly out-of-scope requests before hitting LLM ──
    if _is_out_of_scope_request(user_message):
        logger.info("Pre-filter blocked out-of-scope request: %s", user_message[:100])
        return {
            "agent_output": _OUT_OF_SCOPE_REDIRECT,
            "intermediate_steps": [],
            "success": True,
            "error": None,
        }

    single_item_update = _build_direct_waf_single_item_update_response(state)
    if single_item_update is not None:
        logger.info("Applying direct WAF single-item update shortcut for message: %s", user_message[:80])
        return single_item_update

    direct_update = _build_direct_waf_bulk_update_response(state)
    if direct_update is not None:
        logger.info("Applying direct WAF bulk update shortcut for message: %s", user_message[:80])
        return direct_update

    try:
        # Get the agent runner for shared OpenAI + MCP clients
        runner = await get_agent_runner()
        logger.info(f"Executing stage-aware agent for message: {user_message[:100]}...")
        result = await run_stage_aware_agent(
            state,
            mcp_client=getattr(runner, "mcp_client", None),
            openai_settings=getattr(runner, "openai_settings", None),
        )
        scope_recovered = await _recover_from_over_refusal(
            result=result,
            state=state,
            runner=runner,
        )
        if scope_recovered is not None:
            return scope_recovered

        # The native agent already returns the expected fields
        return result

    except RuntimeError as e:
        logger.error(f"Agent not initialized: {e}")
        return {
            "agent_output": "",
            "intermediate_steps": [],
            "success": False,
            "error": f"Agent system not initialized: {e!s}",
        }
    except Exception as e:
        logger.error(f"Native agent execution failed: {e}", exc_info=True)
        return {
            "agent_output": "",
            "intermediate_steps": [],
            "success": False,
            "error": f"LangGraph native agent execution failed: {e!s}",
        }


async def _recover_from_over_refusal(
    *,
    result: dict[str, Any],
    state: GraphState,
    runner: Any,
) -> dict[str, Any] | None:
    """Retry once when a likely in-scope request is incorrectly refused."""
    user_message = str(state.get("user_message", ""))
    agent_output = str(result.get("agent_output", ""))
    if not _is_scope_refusal(agent_output):
        return None
    if not _is_probably_in_scope(user_message):
        return None

    logger.warning(
        "Detected likely over-refusal for in-scope request; retrying with stronger directives."
    )
    retry_state = dict(state)
    existing_directives = str(retry_state.get("stage_directives", "") or "")
    retry_state["stage_directives"] = (
        existing_directives
        + "\n\nScope override: This user request is in-scope for project/architecture work. "
        "Do NOT refuse. Either perform the requested project update, or ask a focused "
        "clarification question needed to execute it."
    )
    retry_result = await run_stage_aware_agent(
        retry_state,
        mcp_client=getattr(runner, "mcp_client", None),
        openai_settings=getattr(runner, "openai_settings", None),
    )
    retry_output = str(retry_result.get("agent_output", ""))
    if retry_output.strip() and not _is_scope_refusal(retry_output):
        return retry_result

    return {
        "agent_output": (
            "This request is in scope for the project assistant. "
            "I can execute it once you confirm the exact target artifact/item if ambiguous."
        ),
        "intermediate_steps": retry_result.get("intermediate_steps", []),
        "success": True,
        "error": None,
    }


def _is_scope_refusal(text: str) -> bool:
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    return any(pattern.search(lowered) for pattern in _SCOPE_REFUSAL_PATTERNS)


def _is_probably_in_scope(user_message: str) -> bool:
    """Determine whether *user_message* is likely an in-scope project request.

    Uses a weighted approach to avoid both false negatives (blocking legitimate
    requests) and false positives (retrying genuinely off-topic messages):

    1. Any domain keyword match → immediately in-scope.
    2. An action verb present AND no *dominant* off-topic signal → in-scope.
    3. A project state exists (non-empty) → strong bias toward in-scope
       (the user is chatting inside an active project).
    4. Off-topic signals must be *strong* (multiple hits, zero domain hits)
       to block the retry, preventing words like "relationship" or "travel"
       from killing legitimate requests.
    """
    # 1. Direct domain-keyword match (strongest signal)
    if any(pat.search(user_message) for pat in _IN_SCOPE_PATTERNS):
        return True

    # 2. Action verb + no dominant off-topic
    has_action = any(pat.search(user_message) for pat in _ACTION_PATTERNS)
    off_topic_hits = sum(1 for pat in _OFF_TOPIC_PATTERNS if pat.search(user_message))

    if has_action and off_topic_hits == 0:
        return True

    # 3. Even with an action verb, if off-topic signal is weak (1 hit only)
    #    and the message is reasonably long, still allow it — the agent will
    #    decide context from the conversation.
    if has_action and off_topic_hits == 1 and len(user_message.split()) >= 8:
        return True

    return False


def _build_direct_waf_bulk_update_response(state: GraphState) -> dict[str, Any] | None:
    """Build deterministic checklist updates for explicit bulk-completion commands."""
    user_message = str(state.get("user_message", ""))

    target_pillar = _extract_target_pillar(user_message)
    if target_pillar is None:
        return None
    if not _is_bulk_completion_request(user_message):
        return None

    items = _extract_pillar_items(state.get("current_project_state") or {}, target_pillar)
    if not items:
        return None

    timestamp = datetime.now(timezone.utc).isoformat()
    bulk_evidence = (
        f"Manual bulk override requested by user: marked all {target_pillar} checks as covered. "
        "Evidence not independently verified in this turn."
    )
    update_items = [
        {
            "id": item["id"],
            "pillar": target_pillar,
            "topic": item["topic"],
            "evaluations": [
                {
                    "id": str(uuid.uuid4()),
                    "status": "covered",
                    "evidence": bulk_evidence,
                    "relatedFindingIds": [],
                    "sourceCitations": [],
                    "createdAt": timestamp,
                }
            ],
        }
        for item in items
    ]
    state_update = {"wafChecklist": {"items": update_items}}
    response_text = (
        f"Updated {len(update_items)} {target_pillar} WAF checklist items to covered.\n\n"
        "Risk warning: this is a manual bulk override without per-item validation evidence. "
        "Treat it as provisional and verify each control before sign-off.\n\n"
        "AAA_STATE_UPDATE\n"
        "```json\n"
        f"{json.dumps(state_update, ensure_ascii=False, indent=2)}\n"
        "```"
    )
    return {
        "agent_output": response_text,
        "intermediate_steps": [],
        "success": True,
        "error": None,
    }


def _build_direct_waf_single_item_update_response(state: GraphState) -> dict[str, Any] | None:
    """Build deterministic checklist update for explicit single-item status commands."""
    user_message = str(state.get("user_message", ""))
    if not _is_single_item_update_request(user_message):
        return None

    target_status = _extract_target_status(user_message)
    if target_status is None:
        return None

    target_pillar = _extract_target_pillar(user_message)
    items = _extract_pillar_items(state.get("current_project_state") or {}, target_pillar)
    if not items:
        return None

    matched_item = _match_single_item_from_message(user_message, items)
    if matched_item is None:
        return None

    timestamp = datetime.now(timezone.utc).isoformat()
    update_item = {
        "id": matched_item["id"],
        "pillar": matched_item["pillar"],
        "topic": matched_item["topic"],
        "evaluations": [
            {
                "id": str(uuid.uuid4()),
                "status": target_status,
                "evidence": (
                    f"Manual checklist update requested by user for topic '{matched_item['topic']}'. "
                    "Evidence not independently verified in this turn."
                ),
                "relatedFindingIds": [],
                "sourceCitations": [],
                "createdAt": timestamp,
            }
        ],
    }
    state_update = {"wafChecklist": {"items": [update_item]}}
    status_label = _status_to_label(target_status)
    response_text = (
        f"Updated '{matched_item['topic']}' ({matched_item['pillar']}) to {status_label}.\n\n"
        "Risk warning: this is a manual status override without per-item validation evidence. "
        "Treat it as provisional until evidence is captured.\n\n"
        "AAA_STATE_UPDATE\n"
        "```json\n"
        f"{json.dumps(state_update, ensure_ascii=False, indent=2)}\n"
        "```"
    )
    return {
        "agent_output": response_text,
        "intermediate_steps": [],
        "success": True,
        "error": None,
    }


def _extract_target_pillar(user_message: str) -> str | None:
    lowered = user_message.lower()
    for pillar, aliases in _PILLAR_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            return pillar
    return None


def _is_bulk_completion_request(user_message: str) -> bool:
    lowered = user_message.lower()
    completion_terms = ("done", "complete", "completed", "covered", "green")
    scope_terms = ("all", "entire", "every")
    action_terms = ("update", "mark", "set")

    has_completion = any(term in lowered for term in completion_terms)
    has_scope = any(term in lowered for term in scope_terms)
    if not has_completion or not has_scope:
        return False

    has_checklist_ref = "checklist" in lowered or "waf" in lowered
    has_action = any(term in lowered for term in action_terms)
    return has_checklist_ref or has_action


def _is_single_item_update_request(user_message: str) -> bool:
    lowered = user_message.lower()
    has_checklist_ref = "checklist" in lowered or "waf" in lowered
    if not has_checklist_ref:
        return False

    # Avoid overlap with explicit bulk updates.
    if any(term in lowered for term in (" all ", " every ", " entire ")):
        return False

    action_terms = (
        "uncheck",
        "check",
        "mark",
        "set",
        "update",
        "not covered",
        "covered",
        "partial",
        "in progress",
    )
    return any(term in lowered for term in action_terms)


def _extract_target_status(user_message: str) -> str | None:
    lowered = user_message.lower()

    not_covered_terms = ("uncheck", "not covered", "not-covered", "remove check", "undo")
    partial_terms = ("partial", "in progress", "in-progress")
    covered_terms = ("check", "covered", "done", "complete", "completed", "green")

    if any(term in lowered for term in not_covered_terms):
        return "notCovered"
    if any(term in lowered for term in partial_terms):
        return "partial"
    if any(term in lowered for term in covered_terms):
        return "covered"
    return None


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def _topic_tokens(topic: str) -> list[str]:
    stopwords = {
        "the",
        "and",
        "for",
        "your",
        "with",
        "that",
        "this",
        "from",
        "into",
        "workload",
        "design",
        "checklist",
    }
    tokens = [token for token in _normalize_text(topic).split(" ") if len(token) > 2]
    return [token for token in tokens if token not in stopwords]


def _match_single_item_from_message(
    user_message: str,
    items: list[dict[str, str]],
) -> dict[str, str] | None:
    normalized_message = _normalize_text(user_message)
    best_match: dict[str, str] | None = None
    best_score = 0.0

    for item in items:
        topic = item["topic"]
        normalized_topic = _normalize_text(topic)
        if normalized_topic and normalized_topic in normalized_message:
            return item

        tokens = _topic_tokens(topic)
        if not tokens:
            continue

        overlap = sum(1 for token in tokens if token in normalized_message)
        score = overlap / len(tokens)
        if score > best_score:
            best_score = score
            best_match = item

    # Require strong match to avoid accidental updates.
    return best_match if best_score >= 0.6 else None


def _status_to_label(status: str) -> str:
    if status == "notCovered":
        return "not covered"
    if status == "partial":
        return "partial"
    return "covered"


def _extract_pillar_items(
    current_project_state: dict[str, Any], pillar: str | None
) -> list[dict[str, str]]:
    waf = current_project_state.get("wafChecklist")
    if not isinstance(waf, dict):
        return []

    raw_items = waf.get("items")
    items_iterable = raw_items.values() if isinstance(raw_items, dict) else raw_items
    if not isinstance(items_iterable, (list, tuple)) and not hasattr(items_iterable, "__iter__"):
        return []

    selected: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for item in items_iterable:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "")).strip()
        topic = str(item.get("topic") or item.get("title") or item_id).strip()
        item_pillar = str(item.get("pillar", "")).strip()
        if not item_id or not topic:
            continue
        if pillar is not None and item_pillar.lower() != pillar.lower():
            continue
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)
        selected.append({"id": item_id, "topic": topic, "pillar": item_pillar or "General"})
    return selected

