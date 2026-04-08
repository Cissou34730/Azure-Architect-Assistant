"""Mind map loading and validation.

This module loads `/docs/arch_mindmap.json` once at startup and provides
access to the parsed structure for downstream AAA features.

Phase 2 scope (T005): validate presence of the 13 invariant top-level topics.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.shared.config.app_settings import get_app_settings

REQUIRED_TOP_LEVEL_TOPIC_KEYS: tuple[str, ...] = (
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

_TOPIC_EVIDENCE_KEYS: dict[str, tuple[str, ...]] = {
    "1_foundations": ("diagrams", "traceabilityLinks"),
    "2_requirements_and_quality_attributes": ("requirements", "wafChecklist"),
    "3_domain_and_design": ("requirements",),
    "4_architecture_styles": ("candidateArchitectures", "diagrams"),
    "5_data_and_storage": ("candidateArchitectures", "adrs"),
    "6_integration_and_distributed_systems": ("candidateArchitectures", "adrs"),
    "7_cloud_and_infrastructure": ("iacArtifacts", "diagrams"),
    "8_security_and_compliance": ("wafChecklist", "findings"),
    "9_delivery_and_lifecycle": ("iacArtifacts",),
    "10_observability_and_reliability": ("wafChecklist", "findings"),
    "11_organization_and_process": ("adrs",),
    "12_practice_ideas": ("adrs", "traceabilityLinks"),
    "13_learning_and_practice": ("traceabilityLinks",),
}

_ARTIFACT_EVIDENCE_REASONS: dict[str, str] = {
    "requirements": "Captured requirements provide direct architecture coverage evidence.",
    "candidateArchitectures": "Candidate architectures anchor design coverage for this topic.",
    "diagrams": "Recorded diagrams provide concrete design evidence for this topic.",
    "adrs": "ADRs capture reviewed decisions tied to this topic.",
    "iacArtifacts": "IaC artifacts demonstrate implementation coverage for this topic.",
    "traceabilityLinks": "Traceability links show cross-artifact evidence for this topic.",
    "wafChecklist": "WAF checklist evaluations provide governance and quality evidence for this topic.",
    "findings": "Validation findings provide review evidence for this topic.",
}


def _address_confidence_threshold() -> float:
    return get_app_settings().mindmap_confidence_threshold


class MindMapValidationError(ValueError):
    """Raised when the mind map file is missing or invalid."""


@dataclass(frozen=True)
class MindMapLoadResult:
    mindmap: dict[str, Any]
    top_level_topics: dict[str, Any]
    missing_top_level_keys: list[str]


class MindMapCache:
    """Singleton cache for loaded mind map data."""

    _mindmap: dict[str, Any] | None = None
    _topics: dict[str, Any] | None = None
    _path: Path | None = None

    @classmethod
    def set(cls, mindmap: dict[str, Any], topics: dict[str, Any], path: Path) -> None:
        cls._mindmap = mindmap
        cls._topics = topics
        cls._path = path

    @classmethod
    def get(cls) -> tuple[dict[str, Any] | None, dict[str, Any] | None, Path | None]:
        return cls._mindmap, cls._topics, cls._path

    @classmethod
    def is_initialized(cls) -> bool:
        return cls._mindmap is not None


def load_mindmap(mindmap_path: Path) -> MindMapLoadResult:
    """Load and validate the architecture mind map from disk."""
    data = _load_json_file(mindmap_path)

    pointer_status = data.get("status")
    moved_to = data.get("movedTo")
    if pointer_status == "pointer" and isinstance(moved_to, str):
        redirected_path = (mindmap_path.parent / moved_to).resolve()
        data = _load_json_file(redirected_path)

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


def _load_json_file(file_path: Path) -> dict[str, Any]:
    """Load and return a JSON object from disk."""
    if not file_path.exists():
        raise MindMapValidationError(f"Mind map file not found: {file_path}")

    with open(file_path, encoding="utf-8") as file_handle:
        loaded = json.load(file_handle)

    if not isinstance(loaded, dict):
        raise MindMapValidationError("Mind map JSON root must be an object")

    return loaded


def initialize_mindmap(mindmap_path: Path) -> None:
    """Load and cache the mind map."""
    result = load_mindmap(mindmap_path)

    if result.missing_top_level_keys:
        raise MindMapValidationError(
            "Mind map is missing required top-level topic keys: "
            + ", ".join(result.missing_top_level_keys)
        )

    MindMapCache.set(result.mindmap, result.top_level_topics, mindmap_path)


def is_mindmap_initialized() -> bool:
    return MindMapCache.is_initialized()


def get_mindmap() -> dict[str, Any]:
    """Return the cached mind map JSON."""
    mindmap, _, _ = MindMapCache.get()
    if mindmap is None:
        raise RuntimeError("Mind map not initialized")
    return mindmap


def get_top_level_topics() -> dict[str, Any]:
    """Return the cached top-level topics dict."""
    _, topics, _ = MindMapCache.get()
    if topics is None:
        raise RuntimeError("Mind map not initialized")
    return topics


def get_mindmap_path() -> Path | None:
    _, _, path = MindMapCache.get()
    return path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _waf_signal_strength(state: dict[str, Any]) -> float:
    """Compute checklist maturity signal in [0, 1]."""
    waf = state.get("wafChecklist")
    if not isinstance(waf, dict):
        return 0.0

    items_raw = waf.get("items")
    items = items_raw.values() if isinstance(items_raw, dict) else items_raw
    if not isinstance(items, list) or not items:
        return 0.0

    fixed = 0
    in_progress = 0
    total = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        total += 1
        evals = item.get("evaluations")
        latest = evals[-1] if isinstance(evals, list) and evals else None
        status = str((latest or {}).get("status", "open")).strip().lower()
        if status in {"fixed", "false_positive"}:
            fixed += 1
        elif status == "in_progress":
            in_progress += 1

    if total <= 0:
        return 0.0

    score = (fixed + 0.5 * in_progress) / total
    return round(max(0.0, min(score, 1.0)), 2)


def _findings_signal_strength(state: dict[str, Any]) -> float:
    """Estimate findings quality in [0, 1] using citation presence."""
    findings = state.get("findings")
    if not isinstance(findings, list) or not findings:
        return 0.0

    cited = 0
    total = 0
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        total += 1
        citations = finding.get("sourceCitations")
        if isinstance(citations, list) and citations:
            cited += 1

    if total <= 0:
        return 0.0
    if cited == 0:
        return 0.5
    return round(max(0.0, min(cited / total, 1.0)), 2)


def _gather_artifact_signals(state: dict[str, Any]) -> dict[str, list[float]]:
    """Gather weighted artifact signals for various top-level domains."""

    def _is_populated(key: str) -> bool:
        val = state.get(key)
        return bool(val) if isinstance(val, (list, dict)) else False

    h_req = 1.0 if _is_populated("requirements") else 0.0
    h_cand = 1.0 if _is_populated("candidateArchitectures") else 0.0
    h_diag = 1.0 if _is_populated("diagrams") else 0.0
    h_adr = 1.0 if _is_populated("adrs") else 0.0
    h_iac = 1.0 if _is_populated("iacArtifacts") else 0.0
    h_trace = 1.0 if _is_populated("traceabilityLinks") else 0.0
    h_waf = _waf_signal_strength(state)
    has_waf_items = 1.0 if h_waf > 0 else 0.0
    h_find = _findings_signal_strength(state)

    return {
        "1_foundations": [h_diag, h_trace],
        "2_requirements_and_quality_attributes": [h_req, h_waf],
        "3_domain_and_design": [h_req],
        "4_architecture_styles": [h_cand, h_diag],
        "5_data_and_storage": [h_cand, h_adr],
        "6_integration_and_distributed_systems": [h_cand, h_adr],
        "7_cloud_and_infrastructure": [h_iac, h_diag],
        "8_security_and_compliance": [has_waf_items, h_find],
        "9_delivery_and_lifecycle": [h_iac],
        "10_observability_and_reliability": [has_waf_items, h_find],
        "11_organization_and_process": [h_adr],
        "12_practice_ideas": [h_adr, h_trace],
        "13_learning_and_practice": [h_trace],
    }


def _topic_label(topic_key: str) -> str:
    topic_without_prefix = topic_key.split("_", 1)[-1]
    return topic_without_prefix.replace("_", " ").title()


def _sample_ids(items: list[Any], *, limit: int = 3) -> list[str]:
    sample_ids: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if item_id:
            sample_ids.append(str(item_id))
        if len(sample_ids) >= limit:
            break
    return sample_ids


def _waf_evidence(state: dict[str, Any]) -> dict[str, Any] | None:
    waf = state.get("wafChecklist")
    if not isinstance(waf, dict):
        return None

    items_raw = waf.get("items")
    items = list(items_raw.values()) if isinstance(items_raw, dict) else items_raw
    if not isinstance(items, list) or not items:
        return None

    status_counts = {"fixed": 0, "in_progress": 0, "open": 0}
    sample_ids: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("id") and len(sample_ids) < 3:
            sample_ids.append(str(item["id"]))
        evaluations = item.get("evaluations")
        latest = evaluations[-1] if isinstance(evaluations, list) and evaluations else None
        latest_status = str((latest or {}).get("status") or "open").strip().lower()
        if latest_status in {"fixed", "false_positive"}:
            status_counts["fixed"] += 1
        elif latest_status == "in_progress":
            status_counts["in_progress"] += 1
        else:
            status_counts["open"] += 1

    return {
        "artifactType": "wafChecklist",
        "artifactCount": len(items),
        "sampleIds": sample_ids,
        "statusSummary": status_counts,
        "reason": _ARTIFACT_EVIDENCE_REASONS["wafChecklist"],
    }


def _findings_evidence(state: dict[str, Any]) -> dict[str, Any] | None:
    findings = state.get("findings")
    if not isinstance(findings, list) or not findings:
        return None

    cited_findings = sum(
        1
        for finding in findings
        if isinstance(finding, dict)
        and isinstance(finding.get("sourceCitations"), list)
        and bool(finding.get("sourceCitations"))
    )
    return {
        "artifactType": "findings",
        "artifactCount": len(findings),
        "sampleIds": _sample_ids(findings),
        "citedArtifacts": cited_findings,
        "reason": _ARTIFACT_EVIDENCE_REASONS["findings"],
    }


def _list_artifact_evidence(state: dict[str, Any], artifact_key: str) -> dict[str, Any] | None:
    if artifact_key == "wafChecklist":
        return _waf_evidence(state)
    if artifact_key == "findings":
        return _findings_evidence(state)

    items = state.get(artifact_key)
    if not isinstance(items, list) or not items:
        return None

    return {
        "artifactType": artifact_key,
        "artifactCount": len(items),
        "sampleIds": _sample_ids(items),
        "reason": _ARTIFACT_EVIDENCE_REASONS[artifact_key],
    }


def build_top_level_coverage_scorecard(
    state: dict[str, Any],
    coverage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a 13-topic scorecard with evidence packaging for exports and reports."""
    coverage_payload = coverage if isinstance(coverage, dict) else None
    coverage_topics = coverage_payload.get("topics") if coverage_payload else None
    if not isinstance(coverage_topics, dict):
        coverage_payload = compute_top_level_coverage(state)
        coverage_topics = coverage_payload.get("topics") or {}

    topic_keys = list(REQUIRED_TOP_LEVEL_TOPIC_KEYS)
    summary = {"addressed": 0, "partial": 0, "notAddressed": 0}
    topics: dict[str, dict[str, Any]] = {}

    for topic_key in topic_keys:
        topic_coverage = coverage_topics.get(topic_key) if isinstance(coverage_topics, dict) else {}
        status = str((topic_coverage or {}).get("status") or "not-addressed")
        confidence = float((topic_coverage or {}).get("confidence") or 0.0)
        evidence = [
            packaged
            for artifact_key in _TOPIC_EVIDENCE_KEYS.get(topic_key, ())
            if (packaged := _list_artifact_evidence(state, artifact_key)) is not None
        ]

        if status == "addressed":
            summary["addressed"] += 1
        elif status == "partial":
            summary["partial"] += 1
        else:
            summary["notAddressed"] += 1

        topics[topic_key] = {
            "label": _topic_label(topic_key),
            "status": status,
            "confidence": round(confidence, 2),
            "evidence": evidence,
        }

    return {
        "version": "1",
        "generatedAt": _now_iso(),
        "summary": summary,
        "topics": topics,
    }


def _derive_topic_status(checks: list[float]) -> str:
    """Derive status string from weighted checks."""
    if not checks:
        return "not-addressed"

    score = sum(float(c) for c in checks) / len(checks)
    if score <= 0:
        return "not-addressed"
    if score >= _address_confidence_threshold():
        return "addressed"
    return "partial"


def _derive_topic_confidence(checks: list[float]) -> float:
    if not checks:
        return 0.0
    score = sum(float(c) for c in checks) / len(checks)
    return round(max(0.0, min(score, 1.0)), 2)


def compute_top_level_coverage(state: dict[str, Any]) -> dict[str, Any]:
    """Compute coarse coverage for the 13 top-level topics.

    Coverage is heuristic and based on presence of artifact groups. This is meant
    to drive navigation and prompt uncovered areas, not to be a strict compliance check.
    """

    topics = {}
    try:
        top_level = get_top_level_topics()
        topic_keys = list(top_level.keys())
    except (RuntimeError, ValueError):
        topic_keys = list(REQUIRED_TOP_LEVEL_TOPIC_KEYS)

    signals = _gather_artifact_signals(state)

    for key in topic_keys:
        checks = signals.get(key, [])
        topics[key] = {
            "status": _derive_topic_status(checks),
            "confidence": _derive_topic_confidence(checks),
        }

    return {
        "version": "1",
        "computedAt": _now_iso(),
        "topics": topics,
    }


def update_mindmap_coverage(state: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow-copied state dict with updated mind map coverage."""
    updated = dict(state)
    updated["mindMapCoverage"] = compute_top_level_coverage(updated)
    return updated

