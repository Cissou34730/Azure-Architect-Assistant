"""Utility functions for extracting project state updates from agent responses."""

from __future__ import annotations

import re
from typing import Dict, Any, Optional


def extract_state_updates(
    agent_response: str,
    user_message: str,
    current_state: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Infer partial `ProjectState` updates based on agent output and user input.

    This keeps the heuristic parsing logic out of the API router and allows reuse in
    other agent surfaces (e.g., batch processing, CLI tools) without duplicating code.
    The focus is on common non-functional requirement signals (availability, security,
    performance, cost). Returns ``None`` when no actionable updates are detected.
    """
    combined_text = f"{user_message} {agent_response}".lower()

    updates: Dict[str, Any] = {}

    availability_match = re.search(
        r"(\d{2,3}(?:\.\d+)?%)\s+(?:availability|uptime|sla)",
        combined_text,
        re.IGNORECASE,
    )
    if availability_match:
        updates.setdefault("nfrs", {})["availability"] = (
            f"{availability_match.group(1)} SLA requirement"
        )

    security_keywords = ["security", "authentication", "authorization", "encryption", "compliance"]
    if any(keyword in user_message.lower() for keyword in security_keywords):
        existing_security = current_state.get("nfrs", {}).get("security")
        if not existing_security:
            security_mentions = [
                line.strip() for line in agent_response.split("\n")
                if any(kw in line.lower() for kw in security_keywords)
            ]
            if security_mentions:
                updates.setdefault("nfrs", {})["security"] = "; ".join(security_mentions[:3])

    perf_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(ms|seconds?|milliseconds?)\s+(?:latency|response time)",
        combined_text,
        re.IGNORECASE,
    )
    if perf_match:
        updates.setdefault("nfrs", {})["performance"] = (
            f"{perf_match.group(1)} {perf_match.group(2)} target"
        )

    if "cost" in combined_text or "budget" in combined_text:
        cost_match = re.search(r"\$[\d,]+(?:\.\d{2})?", combined_text)
        if cost_match:
            updates.setdefault("nfrs", {})["costConstraints"] = f"Budget: {cost_match.group(0)}"

    return updates or None
