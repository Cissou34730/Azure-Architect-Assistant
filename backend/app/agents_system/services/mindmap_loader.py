"""Mind map loading and validation.

This module loads `/docs/arch_mindmap.json` once at startup and provides
access to the parsed structure for downstream AAA features.

Phase 2 scope (T005): validate presence of the 13 invariant top-level topics.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from datetime import datetime, timezone


REQUIRED_TOP_LEVEL_TOPIC_KEYS: Tuple[str, ...] = (
    "1_foundations",
    "2_requirements_and_quality_attributes",
    "3_domain_and_design",
    "4_architecture_styles",
    "5_data_and_storage",
    "6_integration_and_distributed_systems",
    "7_cloud_and_infrastructure",
    "8_security_and_compliance",
    "9_delivery_and_lifecycle",
    "10_observability_and_reliability",
    "11_organization_and_process",
    "12_practice_ideas",
    "13_learning_and_practice",
)


class MindMapValidationError(ValueError):
    """Raised when the mind map file is missing or invalid."""


@dataclass(frozen=True)
class MindMapLoadResult:
    mindmap: Dict[str, Any]
    top_level_topics: Dict[str, Any]
    missing_top_level_keys: List[str]


_cached_mindmap: Optional[Dict[str, Any]] = None
_cached_top_level_topics: Optional[Dict[str, Any]] = None
_cached_path: Optional[Path] = None


def load_mindmap(mindmap_path: Path) -> MindMapLoadResult:
    """Load and validate the architecture mind map from disk."""
    if not mindmap_path.exists():
        raise MindMapValidationError(f"Mind map file not found: {mindmap_path}")

    with open(mindmap_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise MindMapValidationError("Mind map JSON root must be an object")

    root = data.get("software_architecture_mindmap")
    if not isinstance(root, dict):
        raise MindMapValidationError(
            "Mind map must contain 'software_architecture_mindmap' object"
        )

    missing = [key for key in REQUIRED_TOP_LEVEL_TOPIC_KEYS if key not in root]

    return MindMapLoadResult(
        mindmap=data, top_level_topics=root, missing_top_level_keys=missing
    )


def initialize_mindmap(mindmap_path: Path) -> None:
    """Load and cache the mind map.

    This is intended to be called once during application startup.
    """
    global _cached_mindmap, _cached_top_level_topics, _cached_path

    result = load_mindmap(mindmap_path)

    if result.missing_top_level_keys:
        raise MindMapValidationError(
            "Mind map is missing required top-level topic keys: "
            + ", ".join(result.missing_top_level_keys)
        )

    _cached_mindmap = result.mindmap
    _cached_top_level_topics = result.top_level_topics
    _cached_path = mindmap_path


def is_mindmap_initialized() -> bool:
    return _cached_mindmap is not None and _cached_top_level_topics is not None


def get_mindmap() -> Dict[str, Any]:
    """Return the cached mind map JSON."""
    if _cached_mindmap is None:
        raise RuntimeError("Mind map not initialized")
    return _cached_mindmap


def get_top_level_topics() -> Dict[str, Any]:
    """Return the cached top-level topics dict."""
    if _cached_top_level_topics is None:
        raise RuntimeError("Mind map not initialized")
    return _cached_top_level_topics


def get_mindmap_path() -> Optional[Path]:
    return _cached_path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_top_level_coverage(state: Dict[str, Any]) -> Dict[str, Any]:
    """Compute coarse coverage for the 13 top-level topics.

    Coverage is heuristic and based on presence of artifact groups. This is meant
    to drive navigation and prompt uncovered areas, not to be a strict compliance check.
    """

    topics = {}
    try:
        top_level = get_top_level_topics()
        topic_keys = list(top_level.keys())
    except Exception:
        topic_keys = list(REQUIRED_TOP_LEVEL_TOPIC_KEYS)

    def _has_list(key: str) -> bool:
        v = state.get(key)
        return bool(v) if isinstance(v, list) else False

    def _has_dict(key: str) -> bool:
        v = state.get(key)
        return bool(v) if isinstance(v, dict) else False

    has_requirements = _has_list("requirements")
    has_candidates = _has_list("candidateArchitectures")
    has_diagrams = _has_list("diagrams")
    has_adrs = _has_list("adrs")
    has_findings = _has_list("findings")
    has_iac = _has_list("iacArtifacts")
    has_cost = _has_list("costEstimates")
    has_trace = _has_list("traceabilityLinks")

    waf = state.get("wafChecklist")
    has_waf = isinstance(waf, dict) and bool(waf)
    has_waf_items = isinstance(waf, dict) and isinstance(waf.get("items"), list) and bool(waf.get("items"))

    # Minimal mapping from artifacts to the 13 top-level topics.
    signals: Dict[str, List[bool]] = {
        "1_foundations": [has_diagrams, has_trace],
        "2_requirements_and_quality_attributes": [has_requirements, has_waf],
        "3_domain_and_design": [has_requirements],
        "4_architecture_styles": [has_candidates, has_diagrams],
        "5_data_and_storage": [has_candidates, has_adrs],
        "6_integration_and_distributed_systems": [has_candidates, has_adrs],
        "7_cloud_and_infrastructure": [has_iac, has_diagrams],
        "8_security_and_compliance": [has_waf_items, has_findings],
        "9_delivery_and_lifecycle": [has_iac],
        "10_observability_and_reliability": [has_waf_items, has_findings],
        "11_organization_and_process": [has_adrs],
        "12_practice_ideas": [has_adrs, has_trace],
        "13_learning_and_practice": [has_trace],
    }

    for key in topic_keys:
        checks = signals.get(key, [])
        if not checks:
            status = "not-addressed"
        else:
            true_count = sum(1 for c in checks if c)
            if true_count == 0:
                status = "not-addressed"
            elif true_count == len(checks):
                status = "addressed"
            else:
                status = "partial"
        topics[key] = {"status": status}

    return {
        "version": "1",
        "computedAt": _now_iso(),
        "topics": topics,
    }


def update_mindmap_coverage(state: Dict[str, Any]) -> Dict[str, Any]:
    """Return a shallow-copied state dict with updated mind map coverage."""
    updated = dict(state)
    updated["mindMapCoverage"] = compute_top_level_coverage(updated)
    return updated
