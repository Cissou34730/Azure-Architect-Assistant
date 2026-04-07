"""Helpers for checklist payload merging and consistency checks."""

from __future__ import annotations

from typing import Any


def merge_reconstructed_waf_payloads(reconstructed: dict[str, Any]) -> dict[str, Any]:
    """Merge multi-template reconstructed checklist payload into one flat checklist shape."""
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
    """Extract item ids from list- or dict-based containers."""
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
    """Best-effort consistency check between original and reconstructed checklist payloads."""
    if not orig_waf:
        return True, []

    errors: list[str] = []
    if "items" in orig_waf:
        orig_ids = _extract_item_ids(orig_waf.get("items", {}))
        recon_merged = merge_reconstructed_waf_payloads(recon_waf)
        recon_ids = _extract_item_ids(recon_merged.get("items", {}))
        missing = sorted(orig_ids - recon_ids)
        if missing:
            errors.append(f"Missing items from reconstructed data: {missing[:5]}")
        return len(errors) == 0, errors

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
