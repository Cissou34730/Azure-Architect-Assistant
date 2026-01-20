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
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .aaa_state_models import MCPQueryPhase
from .source_logging import new_mcp_query, new_mcp_citation


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_AAA_MCP_LOG_RE = re.compile(r"AAA_MCP_LOG\s*```json\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_urls(text: str) -> List[str]:
    urls = [u.rstrip(")].,;") for u in _URL_RE.findall(text or "")]
    # Preserve order, de-dupe
    seen: set[str] = set()
    deduped: List[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    return deduped


def _extract_first_mcp_log_payload(text: str, *, expected_tool: str) -> Optional[Dict[str, Any]]:
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
    intermediate_steps: Iterable[Tuple[Any, Any]],
    user_message: str,
) -> Dict[str, Any]:
    """Derive ProjectState updates for MCP queries from LangChain intermediate steps."""

    phase = infer_phase_from_user_message(user_message)
    mcp_queries: List[Dict[str, Any]] = []

    for action, observation in intermediate_steps or []:
        tool_name = getattr(action, "tool", None)
        if tool_name not in {
            "microsoft_docs_search",
            "microsoft_docs_fetch",
            "microsoft_code_samples_search",
        }:
            continue

        tool_input = getattr(action, "tool_input", None)
        query_text = None
        if isinstance(tool_input, dict):
            query_text = tool_input.get("query") or tool_input.get("url")
        elif isinstance(tool_input, str):
            query_text = tool_input

        query_text = (query_text or "").strip() or f"{tool_name}"
        obs_text = str(observation) if observation is not None else ""

        payload = _extract_first_mcp_log_payload(obs_text, expected_tool=tool_name)
        if payload is not None:
            payload_query = payload.get("query") or payload.get("url")
            if isinstance(payload_query, str) and payload_query.strip():
                query_text = payload_query.strip()

            payload_urls = payload.get("urls")
            if isinstance(payload_urls, list):
                result_urls = [u for u in payload_urls if isinstance(u, str)]
            else:
                result_urls = []
        else:
            result_urls = _extract_urls(obs_text)

        q = new_mcp_query(
            query_text=query_text,
            phase=phase,
            result_urls=result_urls,
            selected_snippets=None,
            executed_at=_now_iso(),
        )
        mcp_queries.append(q.model_dump())

    return {"mcpQueries": mcp_queries} if mcp_queries else {}


def build_iteration_event_update(
    *,
    kind: str,
    text: str,
    mcp_query_ids: List[str],
    architect_response_message_id: Optional[str] = None,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
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


def derive_uncovered_topic_questions(state: Dict[str, Any]) -> List[str]:
    """Heuristic uncovered topic prompts until full mind map coverage exists (US6).

    We map a subset of the 13 top-level topics to existing persisted artifacts.
    If an artifact group is empty/missing, we consider that topic likely uncovered.
    """

    def _has_items(key: str) -> bool:
        v = state.get(key)
        return bool(v) if isinstance(v, (list, dict)) else False

    nfrs = state.get("nfrs") if isinstance(state.get("nfrs"), dict) else {}

    candidates_ok = _has_items("candidateArchitectures")
    requirements_ok = _has_items("requirements")
    waf_ok = isinstance(state.get("wafChecklist"), dict) and bool(state.get("wafChecklist"))
    diagrams_ok = _has_items("diagrams")
    iac_ok = _has_items("iacArtifacts")
    cost_ok = _has_items("costEstimates")

    questions: List[str] = []

    if not requirements_ok:
        questions.append(
            "Topic 2 (Requirements & Quality Attributes): do we have complete NFRs (availability, RPO/RTO, latency, budget) and success criteria?"
        )
    else:
        if not nfrs or not any(nfrs.get(k) for k in ["availability", "security", "performance", "costConstraints"]):
            questions.append(
                "Topic 2 (Requirements & Quality Attributes): which NFRs are most critical (availability, security/compliance, performance/latency, cost)?"
            )

    if not candidates_ok:
        questions.append(
            "Topic 4 (Architecture Styles): should we prefer monolith vs microservices vs event-driven vs serverless for this workload?"
        )

    if not diagrams_ok:
        questions.append(
            "Topic 1 (Foundations/C4): do you want a C4 Container diagram next (or just keep System Context for now)?"
        )

    if not waf_ok:
        questions.append(
            "Topic WAF (cross-cutting): are there any must-pass WAF pillar requirements (security, reliability, cost, operational excellence, performance)?"
        )

    if not iac_ok:
        questions.append(
            "Topic 7 (Cloud & Infrastructure): should we target Terraform, Bicep, or both for IaC?"
        )

    if not cost_ok:
        questions.append(
            "Topic Cost: do you have a monthly budget target and the expected scale (users/requests/data volume) for cost estimation?"
        )

    return questions[:3]
