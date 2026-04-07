"""Template resolution and metadata indexing helpers."""

from __future__ import annotations

import logging
from typing import Any

from app.features.checklists.domain.default_templates import resolve_bootstrap_template_slugs
from app.features.checklists.infrastructure.models import ChecklistTemplate
from app.features.checklists.infrastructure.registry import ChecklistRegistry

logger = logging.getLogger(__name__)


class ChecklistTemplateResolver:
    """Resolve templates and cache per-template item metadata indexes."""

    def __init__(self, registry: ChecklistRegistry) -> None:
        self.registry = registry
        self._item_metadata_cache: dict[str, dict[str, dict[str, Any]]] = {}

    def get_template(self, slug: str) -> ChecklistTemplate | None:
        return self.registry.get_template(slug)

    def resolve_template(self, template_slug: str, payload: dict[str, Any]) -> ChecklistTemplate | None:
        template = self.registry.get_template(template_slug)
        if template is not None:
            return template

        fallback_slug = self.default_template_slug()
        fallback = self.registry.get_template(fallback_slug)
        if fallback is None:
            logger.warning(
                "No checklist template found for '%s' and no fallback template available",
                template_slug,
            )
        return fallback

    def default_template_slug(self) -> str:
        available = [template.slug for template in self.registry.list_templates()]
        selected = resolve_bootstrap_template_slugs(available)
        if selected:
            return selected[0]
        return available[0] if available else "azure-waf-v1"

    def select_bootstrap_template_slugs(self, requested: list[str] | None) -> list[str]:
        available = [template.slug for template in self.registry.list_templates()]
        if requested:
            available_set = set(available)
            selected = [slug for slug in requested if slug in available_set]
            if selected:
                return selected
        return resolve_bootstrap_template_slugs(available)

    def collect_template_items(self, template: ChecklistTemplate) -> list[dict[str, Any]]:
        raw_items: list[dict[str, Any]] = []
        content = getattr(template, "content", None)
        if isinstance(content, dict):
            content_items = content.get("items")
            if isinstance(content_items, list):
                raw_items.extend(i for i in content_items if isinstance(i, dict))

        template_items = getattr(template, "items", None)
        if isinstance(template_items, list):
            raw_items.extend(i for i in template_items if isinstance(i, dict))

        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in raw_items:
            item_id = str(item.get("id") or item.get("slug") or "").strip()
            if not item_id or item_id in seen:
                continue
            seen.add(item_id)
            deduped.append(item)
        return deduped

    def metadata_for_item(self, template: ChecklistTemplate, template_item_id: str) -> dict[str, Any]:
        slug = str(getattr(template, "slug", "")).strip()
        if not slug:
            return {}
        if slug not in self._item_metadata_cache:
            self._item_metadata_cache[slug] = self._build_item_metadata_index(template)
        return self._item_metadata_cache[slug].get(template_item_id, {})

    def clear_metadata_cache(self, slug: str | None = None) -> None:
        """Invalidate the item metadata cache. Pass a slug to clear a specific template, or None to clear all."""
        if slug is not None:
            self._item_metadata_cache.pop(slug, None)
        else:
            self._item_metadata_cache.clear()

    def extract_known_pillars(self, template: ChecklistTemplate | None) -> list[str]:
        if template is None:
            return []
        content = getattr(template, "content", None)
        if not isinstance(content, dict):
            return []
        items = content.get("items")
        if not isinstance(items, list):
            return []
        return sorted({str(i.get("pillar")).strip() for i in items if isinstance(i, dict) and i.get("pillar")})

    def _build_item_metadata_index(self, template: ChecklistTemplate) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        for item in self.collect_template_items(template):
            item_id = str(item.get("id") or item.get("slug") or "").strip()
            if not item_id:
                continue
            index[item_id] = item
        return index

