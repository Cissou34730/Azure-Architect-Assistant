"""Helpers for per-iteration logging derived from agent tool calls.

User Story 7 scope:
- Record MCP queries for every iteration (including empty/failed lookups)
- Derive small sets of "uncovered topic" questions from current project state
- Create iteration event payloads suitable for merge-based state updates

These functions are pure and do not touch the database.
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from .aaa_state_models import MCPQueryPhase
from .source_logging import new_mcp_citation, new_mcp_query


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_AAA_MCP_LOG_RE = re.compile(r"AAA_MCP_LOG\s*```json\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_urls(text: str) -> list[str]:
    urls = [u.rstrip(")].,;") for u in _URL_RE.findall(text or "")]
    # Preserve order, de-dupe
    seen: set[str] = set()
    deduped: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    return deduped


def _extract_first_mcp_log_payload(text: str, *, expected_tool: str) -> dict[str, Any] | None:
    for match in _AAA_MCP_LOG_RE.findall(text or ""):
        try:
            payload = json.loads(match)
        except json.JSONDecodeError:
            continue

        if not isinstance(payload, dict):
            continue

        tool = payload.get("tool")
        if tool == expected_tool:
            return payload

    return None


def infer_phase_from_user_message(user_message: str) -> MCPQueryPhase:
    msg = (user_message or "").lower()
    if any(k in msg for k in ["terraform", "bicep", "iac", "infrastructure as code"]):
        return MCPQueryPhase.iac
    if any(k in msg for k in ["validate", "validation", "waf", "security benchmark", "asb"]):
        return MCPQueryPhase.validation
    return MCPQueryPhase.architecture


def derive_mcp_query_updates_from_steps(
    *,
    intermediate_steps: Iterable[tuple[Any, Any]],
    user_message: str,
) -> dict[str, Any]:
    """Derive ProjectState updates for MCP queries from LangChain intermediate steps."""
    phase = infer_phase_from_user_message(user_message)
    mcp_queries: list[dict[str, Any]] = []

    for action, observation in intermediate_steps or []:
        tool_name = getattr(action, "tool", None)
        if tool_name not in {
            "microsoft_docs_search",
            "microsoft_docs_fetch",
            "microsoft_code_samples_search",
        }:
            continue

        q_dict = _process_single_tool_step(action, observation, tool_name, phase)
        mcp_queries.append(q_dict)

    return {"mcpQueries": mcp_queries} if mcp_queries else {}


def _process_single_tool_step(
    action: Any, observation: Any, tool_name: str, phase: MCPQueryPhase
) -> dict[str, Any]:
    """Process a single tool call from intermediate steps into an MCP query update."""
    query_text = _extract_query_text(action, tool_name)
    obs_text = str(observation) if observation is not None else ""

    payload = _extract_first_mcp_log_payload(obs_text, expected_tool=tool_name)
    if payload:
        query_text = _refine_query_from_payload(payload, query_text)
        result_urls = _extract_urls_from_payload(payload)
    else:
        result_urls = _extract_urls(obs_text)

    q = new_mcp_query(
        query_text=query_text,
        phase=phase,
        result_urls=result_urls,
        selected_snippets=None,
        executed_at=_now_iso(),
    )
    return q.model_dump(by_alias=True)


def _extract_query_text(action: Any, tool_name: str) -> str:
    """Extract raw query text from tool action input."""
    tool_input = getattr(action, "tool_input", None)
    if isinstance(tool_input, dict):
        text = tool_input.get("query") or tool_input.get("url")
    elif isinstance(tool_input, str):
        text = tool_input
    else:
        text = None

    return (text or "").strip() or f"{tool_name}"


def _refine_query_from_payload(payload: dict[str, Any], current_query: str) -> str:
    """Refine query text using actual payload if available."""
    payload_query = payload.get("query") or payload.get("url")
    if isinstance(payload_query, str) and payload_query.strip():
        return payload_query.strip()
    return current_query


def _extract_urls_from_payload(payload: dict[str, Any]) -> list[str]:
    """Extract result URLs from tool output payload."""
    urls = payload.get("urls")
    if isinstance(urls, list):
        return [u for u in urls if isinstance(u, str)]
    return []


def build_iteration_event_update(
    *,
    kind: str,
    text: str,
    mcp_query_ids: list[str],
    architect_response_message_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    citations = []
    for qid in mcp_query_ids[:5]:
        citations.append(new_mcp_citation(mcp_query_id=qid).model_dump())

    event = {
        "id": str(uuid.uuid4()),
        "kind": kind,
        "text": text,
        "citations": citations,
        "architectResponseMessageId": architect_response_message_id,
        "createdAt": created_at or _now_iso(),
        "relatedArtifactIds": [],
    }
    return {"iterationEvents": [event]}


def derive_uncovered_topic_questions(state: dict[str, Any]) -> list[str]:
    """Heuristic uncovered topic prompts until full mind map coverage exists (US6)."""
    questions: list[str] = []

    _check_requirements_gaps(state, questions)
    _check_architecture_gaps(state, questions)
    _check_diagram_gaps(state, questions)
    _check_validation_gaps(state, questions)
    _check_iac_cost_gaps(state, questions)

    return questions[:3]


def _has_items(state: dict[str, Any], key: str) -> bool:
    """Helper to check if a state key has non-empty list or dict."""
    v = state.get(key)
    return bool(v) if isinstance(v, (list, dict)) else False


def _check_requirements_gaps(state: dict[str, Any], questions: list[str]) -> None:
    """Check for missing NFRs or requirements."""
    requirements_ok = _has_items(state, "requirements")
    nfrs = state.get("nfrs") if isinstance(state.get("nfrs"), dict) else {}

    if not requirements_ok:
        questions.append(
            "Topic 2 (Requirements & Quality Attributes): do we have complete NFRs (availability, RPO/RTO, latency, budget) and success criteria?"
        )
    elif not any(nfrs.get(k) for k in ["availability", "security", "performance", "costConstraints"]):
        questions.append(
            "Topic 2 (Requirements & Quality Attributes): which NFRs are most critical (availability, security/compliance, performance/latency, cost)?"
        )


def _check_architecture_gaps(state: dict[str, Any], questions: list[str]) -> None:
    """Check for missing architecture style candidates."""
    if not _has_items(state, "candidateArchitectures"):
        questions.append(
            "Topic 4 (Architecture Styles): should we prefer monolith vs microservices vs event-driven vs serverless for this workload?"
        )


def _check_diagram_gaps(state: dict[str, Any], questions: list[str]) -> None:
    """Check for missing diagrams."""
    if not _has_items(state, "diagrams"):
        questions.append(
            "Topic 1 (Foundations/C4): do you want a C4 Container diagram next (or just keep System Context for now)?"
        )


def _check_validation_gaps(state: dict[str, Any], questions: list[str]) -> None:
    """Check for missing WAF validation."""
    waf_ok = isinstance(state.get("wafChecklist"), dict) and bool(state.get("wafChecklist"))
    if not waf_ok:
        questions.append(
            "Topic WAF (cross-cutting): are there any must-pass WAF pillar requirements (security, reliability, cost, operational excellence, performance)?"
        )


def _check_iac_cost_gaps(state: dict[str, Any], questions: list[str]) -> None:
    """Check for missing IaC or cost estimation."""
    if not _has_items(state, "iacArtifacts"):
        questions.append(
            "Topic 7 (Cloud & Infrastructure): should we target Terraform, Bicep, or both for IaC?"
        )
    if not _has_items(state, "costEstimates"):
        questions.append(
            "Topic Cost: do you have a monthly budget target and the expected scale (users/requests/data volume) for cost estimation?"
        )

