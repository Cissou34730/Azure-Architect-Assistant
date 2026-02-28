"""Shared helpers used by multiple routing modules."""

from typing import Any

_DICT_FIELDS = [
    ("workloadType", "Workload Type"),
    ("expectedUsers", "Expected Users"),
    ("dataVolume", "Data Volume"),
    ("sla", "SLA Target"),
    ("rto", "RTO"),
    ("rpo", "RPO"),
]


def _format_requirement_item(req: Any) -> str:
    if isinstance(req, dict):
        title = req.get("title") or req.get("text") or "Requirement"
        desc = req.get("description") or ""
        return f"- {title}: {desc}" if desc else f"- {title}"
    return f"- {req!s}"


def format_requirements(requirements: Any) -> str:
    """Format requirements dictionary or list for handoff."""
    if not requirements:
        return "No explicit requirements provided."

    if isinstance(requirements, list):
        items = [_format_requirement_item(req) for req in requirements]
        return "\n".join(items) if items else "No explicit requirements provided."

    formatted = [
        f"- {label}: {requirements[key]}"
        for key, label in _DICT_FIELDS
        if key in requirements
    ]
    return "\n".join(formatted) if formatted else str(requirements)
