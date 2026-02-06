"""
Helper functions for normalizing WAF data and maintaining legacy compatibility.

Bridges the gap between ProjectState.state (JSONB) and the normalized SQL tables.
"""

import logging
from typing import Any

from app.models.checklist import ChecklistItemEvaluation

logger = logging.getLogger(__name__)

# Map legacy status to normalized status
LEGACY_STATUS_MAP = {
    "covered": "fixed",
    "partial": "in_progress",
    "notCovered": "open",
    "completed": "fixed",
    "fixed": "fixed",
}

# Map normalized status back to legacy status
NORMALIZED_STATUS_MAP = {
    "fixed": "covered",
    "in_progress": "partial",
    "open": "notCovered",
    "not_applicable": "covered",
}

def map_legacy_status(legacy_status: str) -> str:
    """Map legacy WAF coverage status to normalized evaluation status."""
    return LEGACY_STATUS_MAP.get(legacy_status, "not_started")

def map_normalized_status(normalized_status: str) -> str:
    """Map normalized evaluation status back to legacy WAF coverage status."""
    return NORMALIZED_STATUS_MAP.get(normalized_status, "notCovered")

def extract_waf_evaluations(project_state: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract WAF evaluations from legacy project state JSON.
    
    Returns a list of flattened evaluation dicts ready for database insertion.
    """
    waf_data = project_state.get("wafChecklist", {})
    if not waf_data:
        return []

    evaluations = []
    items = waf_data.get("items", [])
    for item in items:
        item_id = item.get("id")
        if not item_id:
            continue

        # Legacy often has a list of evaluations, we take the latest one
        item_evals = item.get("evaluations", [])
        if not item_evals:
            continue

        # Get the most recent evaluation (usually the last one in the list)
        legacy_eval = item_evals[-1]

        evaluations.append({
            "item_id": item_id,
            "status": map_legacy_status(legacy_eval.get("status", "notCovered")),
            "evidence": {"description": legacy_eval.get("evidence", ""), "legacy_id": legacy_eval.get("id")},
            "evaluator": "legacy-migration",
            "source_type": "legacy-migration",
            "created_at": legacy_eval.get("created_at")
        })

    return evaluations

def reconstruct_legacy_waf_json(
    template_slug: str,
    version: str,
    items_with_evals: list[Any],  # Expecting ChecklistItem joined with latest ChecklistItemEvaluation
    known_pillars: list[str] | None = None
) -> dict[str, Any]:
    """
    Reconstruct the legacy ProjectState.state['wafChecklist'] JSON structure
    from normalized database records.
    """
    if known_pillars:
        pillars = sorted(list(set(known_pillars)))
    else:
        pillars = sorted(list(set(getattr(item, "pillar", "General") for item in items_with_evals)))

    if not pillars:
        # Fallback to standard WAF pillars if none found, to ensure UI doesn't break
        pillars = ["Cost Optimization", "Operational Excellence", "Performance Efficiency", "Reliability", "Security"]

    legacy_items = []
    for item in items_with_evals:
        # Get the latest evaluation if any
        eval_obj: ChecklistItemEvaluation | None = None
        if hasattr(item, "evaluations") and item.evaluations:
            # Assuming they are ordered or we just take the first if it's been filtered
            eval_obj = item.evaluations[0] if isinstance(item.evaluations, list) else item.evaluations

        legacy_evals = []
        if eval_obj:
            evidence_text = ""
            if isinstance(eval_obj.evidence, dict):
                evidence_text = eval_obj.evidence.get("description") or eval_obj.evidence.get("evidence") or ""
            elif isinstance(eval_obj.evidence, str):
                evidence_text = eval_obj.evidence

            legacy_evals.append({
                "id": f"eval_{eval_obj.id if hasattr(eval_obj, 'id') else 'new'}",
                "status": map_normalized_status(eval_obj.status),
                "evidence": evidence_text,
                "created_at": eval_obj.created_at.isoformat() if hasattr(eval_obj, 'created_at') and eval_obj.created_at else None,
                "sourceCitations": [], # Not currently fully mapped
                "relatedFindingIds": []
            })

        legacy_items.append({
            "id": str(item.id),
            "pillar": item.pillar,
            "topic": item.title,
            "evaluations": legacy_evals
        })

    return {
        "version": version,
        "pillars": pillars,
        "items": legacy_items
    }


def validate_normalized_consistency(
    orig_waf: dict, recon_waf: dict
) -> tuple[bool, list[str]]:
    """
    Validate that reconstructed WAF data matches the important parts of original legacy data.
    """
    errors = []
    
    if not orig_waf:
        return True, []

    for slug, orig_checklist in orig_waf.items():
        if slug not in recon_waf:
            errors.append(f"Checklist '{slug}' missing from reconstructed data")
            continue

        recon_checklist = recon_waf[slug]
        orig_items = orig_checklist.get("items", {})
        recon_items = recon_checklist.get("items", {})

        # Compare item IDs
        orig_ids = set()
        if isinstance(orig_items, dict):
            orig_ids = set(orig_items.keys())
        elif isinstance(orig_items, list):
            orig_ids = set(i.get("id") or i.get("slug") for i in orig_items if i)

        recon_ids = set(recon_items.keys()) if isinstance(recon_items, dict) else set()
        
        missing = orig_ids - recon_ids
        if missing:
            errors.append(f"Checklist '{slug}' missing items: {list(missing)[:5]}")

    return len(errors) == 0, errors
