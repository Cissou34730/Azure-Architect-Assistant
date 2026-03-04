"""Helpers to bridge legacy ``wafChecklist`` JSON and normalized checklist tables."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.agents_system.checklists.default_templates import WAF_PILLAR_TEMPLATES
from app.models.checklist import ChecklistItemEvaluation, EvaluationStatus

logger = logging.getLogger(__name__)

_DEFAULT_PILLARS = [t.pillar for t in WAF_PILLAR_TEMPLATES]

# Legacy status -> normalized evaluation status (DB enum values)
LEGACY_STATUS_MAP = {
    "covered": "fixed",
    "partial": "in_progress",
    "notcovered": "open",
    "completed": "fixed",
    "fixed": "fixed",
    "open": "open",
    "in_progress": "in_progress",
    "false_positive": "false_positive",
}

# Normalized status -> legacy WAF coverage status
NORMALIZED_STATUS_MAP = {
    "fixed": "covered",
    "in_progress": "partial",
    "open": "notCovered",
    "false_positive": "covered",
}


def map_legacy_status(legacy_status: str) -> str:
    """Map legacy WAF coverage status to normalized checklist evaluation status."""
    normalized = legacy_status.strip().lower().replace("-", "_")
    return LEGACY_STATUS_MAP.get(normalized, "open")


def map_normalized_status(normalized_status: str | EvaluationStatus) -> str:
    """Map normalized checklist evaluation status back to legacy WAF coverage status."""
    value = normalized_status.value if isinstance(normalized_status, EvaluationStatus) else normalized_status
    normalized = str(value).strip().lower().replace("-", "_")
    return NORMALIZED_STATUS_MAP.get(normalized, "notCovered")


def _resolve_pillars(items_with_evals: list[Any], known_pillars: list[str] | None) -> list[str]:
    """Resolve the list of pillar names in priority order: known → derived from items → default."""
    if known_pillars:
        pillars = sorted({p for p in known_pillars if p})
        if pillars:
            return pillars
    derived = sorted(
        {str(getattr(item, "pillar", "")).strip() for item in items_with_evals if getattr(item, "pillar", "")}
    )
    return derived if derived else _DEFAULT_PILLARS


def _extract_evidence_text(eval_obj: ChecklistItemEvaluation) -> str:
    """Extract the plain-text evidence string from an evaluation object."""
    if isinstance(eval_obj.evidence, dict):
        return str(
            eval_obj.evidence.get("description")
            or eval_obj.evidence.get("evidence")
            or ""
        )
    if isinstance(eval_obj.evidence, str):
        return eval_obj.evidence
    return ""


def _build_legacy_item(item: Any) -> dict[str, Any]:
    """Build a single legacy WAF item dict with its most-recent evaluation."""
    raw_evals = getattr(item, "evaluations", []) or []
    eval_list = [e for e in raw_evals if isinstance(e, ChecklistItemEvaluation)]
    eval_list.sort(
        key=lambda e: e.created_at if isinstance(e.created_at, datetime) else datetime.min,
        reverse=True,
    )
    eval_obj = eval_list[0] if eval_list else None

    legacy_evals: list[dict[str, Any]] = []
    if eval_obj is not None:
        legacy_evals.append(
            {
                "id": f"eval_{eval_obj.id}",
                "status": map_normalized_status(eval_obj.status),
                "evidence": _extract_evidence_text(eval_obj),
                "created_at": eval_obj.created_at.isoformat() if eval_obj.created_at else None,
                "sourceCitations": [],
                "relatedFindingIds": [],
            }
        )

    legacy_item_id = str(getattr(item, "template_item_id", "") or getattr(item, "id", ""))
    return {
        "id": legacy_item_id,
        "pillar": getattr(item, "pillar", None),
        "topic": getattr(item, "title", None),
        "evaluations": legacy_evals,
    }


def reconstruct_legacy_waf_json(
    template_slug: str,
    version: str | None,
    items_with_evals: list[Any],
    known_pillars: list[str] | None = None,
) -> dict[str, Any]:
    """Reconstruct legacy ``wafChecklist`` JSON from normalized rows."""
    pillars = _resolve_pillars(items_with_evals, known_pillars)
    legacy_items = [_build_legacy_item(item) for item in items_with_evals]
    return {
        "slug": template_slug,
        "version": version or "1",
        "pillars": pillars,
        "items": legacy_items,
    }


def merge_reconstructed_waf_payloads(reconstructed: dict[str, Any]) -> dict[str, Any]:
    """Merge multi-template reconstructed WAF payload into legacy checklist shape."""
    all_items: list[dict[str, Any]] = []
    pillar_order: list[str] = []
    seen_pillars: set[str] = set()
    versions: set[str] = set()

    for payload in reconstructed.values():
        if not isinstance(payload, dict):
            continue

        version = payload.get("version")
        if isinstance(version, str) and version.strip():
            versions.add(version.strip())

        pillars = payload.get("pillars")
        if isinstance(pillars, list):
            for pillar in pillars:
                name = str(pillar).strip()
                if not name or name in seen_pillars:
                    continue
                seen_pillars.add(name)
                pillar_order.append(name)

        items = payload.get("items")
        if isinstance(items, list):
            all_items.extend(item for item in items if isinstance(item, dict))
        elif isinstance(items, dict):
            all_items.extend(item for item in items.values() if isinstance(item, dict))

    version = versions.pop() if len(versions) == 1 else "multi"
    return {"version": version, "pillars": pillar_order, "items": all_items}


def _extract_item_ids(items: Any) -> set[str]:
    """Extract a set of item ID strings from a dict-keyed or list-of-dict items container."""
    if isinstance(items, dict):
        return {str(k) for k in items}
    if isinstance(items, list):
        return {
            str(i.get("id") or i.get("slug"))
            for i in items
            if isinstance(i, dict) and (i.get("id") or i.get("slug"))
        }
    return set()


def validate_normalized_consistency(orig_waf: dict[str, Any], recon_waf: dict[str, Any]) -> tuple[bool, list[str]]:
    """Best-effort consistency check between original and reconstructed WAF JSON."""
    if not orig_waf:
        return True, []

    errors: list[str] = []
    for slug, orig_checklist in orig_waf.items():
        if slug not in recon_waf:
            errors.append(f"Checklist '{slug}' missing from reconstructed data")
            continue

        if not isinstance(orig_checklist, dict):
            continue
        recon_checklist = recon_waf.get(slug, {})

        orig_ids = _extract_item_ids(orig_checklist.get("items", {}))
        recon_ids = _extract_item_ids(recon_checklist.get("items", {}))

        missing = sorted(orig_ids - recon_ids)
        if missing:
            errors.append(f"Checklist '{slug}' missing items: {missing[:5]}")

    return len(errors) == 0, errors
