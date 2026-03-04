"""Parsing helpers for legacy checklist payload shapes."""

from __future__ import annotations

import json
from typing import Any


class ChecklistStateParser:
    """Parse and normalize legacy checklist payload shapes."""

    @staticmethod
    def parse_project_state(project_state: dict[str, Any] | str) -> dict[str, Any] | None:
        if isinstance(project_state, str):
            try:
                return json.loads(project_state)
            except json.JSONDecodeError:
                return None
        return project_state

    def extract_checklists_from_waf_data(self, waf_data: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
        if "items" in waf_data:
            template_slug = self.resolve_template_slug(waf_data)
            return [(template_slug, waf_data)] if template_slug else []

        checklists: list[tuple[str, dict[str, Any]]] = []
        for key, value in waf_data.items():
            if key in {"templates", "metadata"}:
                continue
            if isinstance(value, dict) and "items" in value:
                checklists.append((key, value))
        return checklists

    @staticmethod
    def resolve_template_slug(payload: dict[str, Any]) -> str | None:
        explicit = payload.get("template")
        if isinstance(explicit, str) and explicit.strip():
            return explicit.strip()

        templates = payload.get("templates")
        if isinstance(templates, list):
            for template in templates:
                if not isinstance(template, dict):
                    continue
                slug = template.get("slug")
                if isinstance(slug, str) and slug.strip():
                    return slug.strip()
        return None

    @staticmethod
    def normalize_items_container(legacy_items: Any) -> list[dict[str, Any]]:
        if isinstance(legacy_items, list):
            return [item for item in legacy_items if isinstance(item, dict)]
        if isinstance(legacy_items, dict):
            items: list[dict[str, Any]] = []
            for key, value in legacy_items.items():
                if not isinstance(value, dict):
                    continue
                merged = dict(value)
                merged.setdefault("id", key)
                items.append(merged)
            return items
        return []
