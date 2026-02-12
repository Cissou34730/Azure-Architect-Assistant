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


def extract_waf_evaluations(project_state: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract latest legacy evaluation for each WAF item."""
    waf_data = project_state.get("wafChecklist", {})
    if not isinstance(waf_data, dict):
        return []

    items = waf_data.get("items", [])
    if not isinstance(items, list):
        return []

    evaluations: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if not item_id:
            continue

        item_evals = item.get("evaluations", [])
        if not isinstance(item_evals, list) or not item_evals:
            continue

        latest_eval = item_evals[-1]
        if not isinstance(latest_eval, dict):
            continue

        evaluations.append(
            {
                "item_id": item_id,
                "status": map_legacy_status(str(latest_eval.get("status", "notCovered"))),
                "evidence": {
                    "description": str(latest_eval.get("evidence", "")),
                    "legacy_id": latest_eval.get("id"),
                },
                "evaluator": "legacy-migration",
                "source_type": "legacy-migration",
                "created_at": latest_eval.get("created_at"),
            }
        )

    return evaluations


def reconstruct_legacy_waf_json(
    template_slug: str,
    version: str | None,
    items_with_evals: list[Any],
    known_pillars: list[str] | None = None,
) -> dict[str, Any]:
    """Reconstruct legacy ``wafChecklist`` JSON from normalized rows."""
    pillars = sorted({p for p in known_pillars or [] if p}) if known_pillars else []
    if not pillars:
        pillars = sorted(
            {str(getattr(item, "pillar", "")).strip() for item in items_with_evals if getattr(item, "pillar", "")}
        )
    if not pillars:
        pillars = _DEFAULT_PILLARS

    legacy_items: list[dict[str, Any]] = []
    for item in items_with_evals:
        raw_evals = getattr(item, "evaluations", []) or []
        eval_list = [e for e in raw_evals if isinstance(e, ChecklistItemEvaluation)]
        eval_list.sort(
            key=lambda e: e.created_at if isinstance(e.created_at, datetime) else datetime.min,
            reverse=True,
        )
        eval_obj = eval_list[0] if eval_list else None

        legacy_evals: list[dict[str, Any]] = []
        if eval_obj is not None:
            evidence_text = ""
            if isinstance(eval_obj.evidence, dict):
                evidence_text = str(
                    eval_obj.evidence.get("description")
                    or eval_obj.evidence.get("evidence")
                    or ""
                )
            elif isinstance(eval_obj.evidence, str):
                evidence_text = eval_obj.evidence

            legacy_evals.append(
                {
                    "id": f"eval_{eval_obj.id}",
                    "status": map_normalized_status(eval_obj.status),
                    "evidence": evidence_text,
                    "created_at": eval_obj.created_at.isoformat() if eval_obj.created_at else None,
                    "sourceCitations": [],
                    "relatedFindingIds": [],
                }
            )

        # Keep legacy item id stable for UI references.
        legacy_item_id = str(getattr(item, "template_item_id", "") or getattr(item, "id", ""))
        legacy_items.append(
            {
                "id": legacy_item_id,
                "pillar": getattr(item, "pillar", None),
                "topic": getattr(item, "title", None),
                "evaluations": legacy_evals,
            }
        )

    return {
        "slug": template_slug,
        "version": version or "1",
        "pillars": pillars,
        "items": legacy_items,
    }


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
        orig_items = orig_checklist.get("items", {})
        recon_items = recon_checklist.get("items", {})

        orig_ids: set[str] = set()
        if isinstance(orig_items, dict):
            orig_ids = {str(k) for k in orig_items}
        elif isinstance(orig_items, list):
            orig_ids = {
                str(i.get("id") or i.get("slug"))
                for i in orig_items
                if isinstance(i, dict) and (i.get("id") or i.get("slug"))
            }

        recon_ids: set[str] = set()
        if isinstance(recon_items, dict):
            recon_ids = {str(k) for k in recon_items}
        elif isinstance(recon_items, list):
            recon_ids = {
                str(i.get("id") or i.get("slug"))
                for i in recon_items
                if isinstance(i, dict) and (i.get("id") or i.get("slug"))
            }

        missing = sorted(orig_ids - recon_ids)
        if missing:
            errors.append(f"Checklist '{slug}' missing items: {missing[:5]}")

    return len(errors) == 0, errors
