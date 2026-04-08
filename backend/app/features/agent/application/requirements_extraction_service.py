"""Helpers for Phase 4 requirements extraction bundling."""

from __future__ import annotations

from collections import OrderedDict

from app.features.agent.contracts import (
    ExtractedRequirementContract,
    RequirementAmbiguityContract,
    RequirementSourceContract,
    RequirementsExtractionResultContract,
)


class RequirementsExtractionService:
    """Deduplicate and bundle structured requirements extraction results."""

    def merge_requirements(
        self,
        requirements: list[ExtractedRequirementContract],
    ) -> list[ExtractedRequirementContract]:
        merged_by_key: OrderedDict[tuple[str, str], ExtractedRequirementContract] = OrderedDict()

        for requirement in requirements:
            key = (self._normalize(requirement.text), requirement.category)
            if key not in merged_by_key:
                merged_by_key[key] = requirement.model_copy(deep=True)
                continue

            existing = merged_by_key[key]
            existing.sources = self._merge_sources(existing.sources, requirement.sources)
            existing.ambiguity = self._merge_ambiguity(existing.ambiguity, requirement.ambiguity)

        return list(merged_by_key.values())

    def build_result(
        self,
        *,
        requirements: list[ExtractedRequirementContract],
        assumptions: list[str],
        chunks_processed: int,
    ) -> RequirementsExtractionResultContract:
        merged_requirements = self.merge_requirements(requirements)
        normalized_assumptions = self._normalize_assumptions(assumptions)
        return RequirementsExtractionResultContract(
            requirements=merged_requirements,
            assumptions=normalized_assumptions,
            ambiguities_detected=sum(
                1 for requirement in merged_requirements if requirement.ambiguity.is_ambiguous
            ),
            chunks_processed=chunks_processed,
        )

    def _merge_sources(
        self,
        existing: list[RequirementSourceContract],
        incoming: list[RequirementSourceContract],
    ) -> list[RequirementSourceContract]:
        merged: OrderedDict[tuple[str, str, str | None], RequirementSourceContract] = OrderedDict()
        for source in [*existing, *incoming]:
            key = (source.document_id, source.excerpt, source.location)
            merged.setdefault(key, source)
        return list(merged.values())

    def _merge_ambiguity(
        self,
        existing: RequirementAmbiguityContract,
        incoming: RequirementAmbiguityContract,
    ) -> RequirementAmbiguityContract:
        notes = [note for note in [existing.notes.strip(), incoming.notes.strip()] if note]
        merged_notes = " | ".join(dict.fromkeys(notes))
        return RequirementAmbiguityContract(
            is_ambiguous=existing.is_ambiguous or incoming.is_ambiguous,
            notes=merged_notes,
        )

    def _normalize_assumptions(self, assumptions: list[str]) -> list[str]:
        normalized: OrderedDict[str, str] = OrderedDict()
        for assumption in assumptions:
            cleaned = assumption.strip()
            if cleaned:
                normalized.setdefault(cleaned.lower(), cleaned)
        return list(normalized.values())

    def _normalize(self, text: str) -> str:
        return " ".join(text.lower().split())
