"""Read-side assembly helpers for checklist payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.agents_system.checklists.default_templates import (
    WAF_PILLAR_TEMPLATES,
    resolve_bootstrap_template_slugs,
)
from app.agents_system.checklists.template_resolver import ChecklistTemplateResolver
from app.models.checklist import Checklist, ChecklistItemEvaluation, EvaluationStatus

_DEFAULT_PILLARS = [template.pillar for template in WAF_PILLAR_TEMPLATES]


class ChecklistReadAssembler:
    """Build checklist payloads from normalized rows."""

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
            reconstructed_empty[slug] = {
                "slug": slug,
                "version": template_info.version or "1",
                "pillars": self._resolve_pillars([], self.resolver.extract_known_pillars(template_info)),
                "items": [],
            }
        return reconstructed_empty

    def reconstruct_from_checklists(self, checklists: list[Checklist]) -> dict[str, Any]:
        reconstructed: dict[str, Any] = {}
        for checklist in checklists:
            template_slug = checklist.template_slug or self.resolver.default_template_slug()
            template = self.resolver.registry.get_template(template_slug)
            known_pillars = self.resolver.extract_known_pillars(template) if template else None
            items = [self._build_item_payload(item) for item in checklist.items]
            reconstructed[template_slug] = {
                "slug": template_slug,
                "version": checklist.version or "1",
                "pillars": self._resolve_pillars(items, known_pillars),
                "items": items,
                "title": checklist.title,
            }
        return reconstructed

    @staticmethod
    def _resolve_pillars(
        items: list[dict[str, Any]],
        known_pillars: list[str] | None,
    ) -> list[str]:
        if known_pillars:
            cleaned = sorted({str(p).strip() for p in known_pillars if str(p).strip()})
            if cleaned:
                return cleaned

        derived = sorted(
            {
                str(item.get("pillar", "")).strip()
                for item in items
                if isinstance(item, dict) and str(item.get("pillar", "")).strip()
            }
        )
        return derived if derived else _DEFAULT_PILLARS

    def _build_item_payload(self, item: Any) -> dict[str, Any]:
        latest_eval = self._latest_evaluation(getattr(item, "evaluations", []) or [])
        evaluations: list[dict[str, Any]] = []
        if latest_eval is not None:
            evaluations.append(
                {
                    "id": f"eval_{latest_eval.id}",
                    "status": self._status_value(latest_eval.status),
                    "evidence": self._evidence_text(latest_eval.evidence),
                    "createdAt": latest_eval.created_at.isoformat() if latest_eval.created_at else None,
                    "sourceCitations": [],
                    "relatedFindingIds": [],
                }
            )

        item_id = str(getattr(item, "template_item_id", "") or getattr(item, "id", ""))
        return {
            "id": item_id,
            "pillar": getattr(item, "pillar", None),
            "topic": getattr(item, "title", None),
            "description": getattr(item, "description", None),
            "severity": self._enum_or_raw(getattr(item, "severity", None)),
            "evaluations": evaluations,
        }

    @staticmethod
    def _latest_evaluation(evaluations: list[Any]) -> ChecklistItemEvaluation | None:
        typed = [evaluation for evaluation in evaluations if isinstance(evaluation, ChecklistItemEvaluation)]
        if not typed:
            return None
        typed.sort(
            key=lambda evaluation: evaluation.created_at
            if isinstance(evaluation.created_at, datetime)
            else datetime.min,
            reverse=True,
        )
        return typed[0]

    @staticmethod
    def _status_value(status: EvaluationStatus | str) -> str:
        value = status.value if isinstance(status, EvaluationStatus) else str(status)
        normalized = value.strip().lower()
        if normalized == EvaluationStatus.FALSE_POSITIVE.value:
            return EvaluationStatus.FIXED.value
        if normalized in {
            EvaluationStatus.FIXED.value,
            EvaluationStatus.IN_PROGRESS.value,
            EvaluationStatus.OPEN.value,
        }:
            return normalized
        return EvaluationStatus.OPEN.value

    @staticmethod
    def _evidence_text(evidence: Any) -> str:
        if isinstance(evidence, dict):
            return str(evidence.get("description") or evidence.get("evidence") or "")
        if isinstance(evidence, str):
            return evidence
        return ""

    @staticmethod
    def _enum_or_raw(value: Any) -> Any:
        return value.value if hasattr(value, "value") else value
