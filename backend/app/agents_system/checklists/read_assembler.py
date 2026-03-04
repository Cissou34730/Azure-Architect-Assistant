"""Read-side assembly helpers for legacy checklist payloads."""

from __future__ import annotations

from typing import Any

from app.agents_system.checklists.default_templates import resolve_bootstrap_template_slugs
from app.agents_system.checklists.normalize_helpers import reconstruct_legacy_waf_json
from app.agents_system.checklists.template_resolver import ChecklistTemplateResolver
from app.models.checklist import Checklist


class ChecklistReadAssembler:
    """Build legacy-shaped WAF payloads from normalized rows."""

    def __init__(self, resolver: ChecklistTemplateResolver) -> None:
        self.resolver = resolver

    def build_empty_reconstructed_state(self) -> dict[str, Any]:
        templates = self.resolver.registry.list_templates()
        selected_slugs = resolve_bootstrap_template_slugs(
            getattr(template, "slug", "") for template in templates
        )
        if not selected_slugs and templates:
            selected_slugs = [getattr(templates[0], "slug", "")]

        reconstructed_empty: dict[str, Any] = {}
        for slug in selected_slugs:
            if not slug:
                continue
            template_info = self.resolver.registry.get_template(slug)
            if template_info is None:
                continue
            reconstructed_empty[slug] = reconstruct_legacy_waf_json(
                template_slug=slug,
                version=template_info.version or "1",
                items_with_evals=[],
                known_pillars=self.resolver.extract_known_pillars(template_info),
            )
        return reconstructed_empty

    def reconstruct_from_checklists(self, checklists: list[Checklist]) -> dict[str, Any]:
        reconstructed: dict[str, Any] = {}
        for checklist in checklists:
            template_slug = checklist.template_slug or self.resolver.default_template_slug()
            template = self.resolver.registry.get_template(template_slug)
            known_pillars = self.resolver.extract_known_pillars(template) if template else None
            reconstructed[template_slug] = reconstruct_legacy_waf_json(
                template_slug=template_slug,
                version=checklist.version,
                items_with_evals=list(checklist.items),
                known_pillars=known_pillars,
            )
            reconstructed[template_slug]["title"] = checklist.title
        return reconstructed
