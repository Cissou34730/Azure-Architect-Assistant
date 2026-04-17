"""Deterministic WAF evaluator for current project architecture state."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any, Literal

WafEvaluationStatus = Literal["fixed", "in_progress", "open"]

_TEXT_SOURCE_KEYS: tuple[str, ...] = (
    "context",
    "nfrs",
    "applicationStructure",
    "requirements",
    "assumptions",
    "adrs",
    "candidateArchitectures",
    "diagrams",
    "referenceDocuments",
    "technicalConstraints",
    "mindMap",
)
_GENERIC_STOPWORDS = {
    "a",
    "all",
    "an",
    "and",
    "application",
    "architecture",
    "at",
    "by",
    "create",
    "data",
    "design",
    "different",
    "for",
    "from",
    "help",
    "implement",
    "in",
    "instance",
    "into",
    "its",
    "levels",
    "methods",
    "multiple",
    "network",
    "of",
    "on",
    "or",
    "service",
    "services",
    "systems",
    "that",
    "the",
    "their",
    "timely",
    "to",
    "use",
    "using",
    "workload",
    "your",
}
_MIN_TERM_LENGTH = 4
_FIXED_MATCH_THRESHOLD = 4


class WAFEvaluatorService:
    """Evaluate checklist items against the current project state without using an LLM."""

    def evaluate(self, state: Mapping[str, Any]) -> dict[str, Any]:
        project_state = self._coerce_project_state(state)
        checklist_items = self._extract_checklist_items(project_state)
        evidence_sources = self._extract_evidence_sources(project_state)

        evaluations = [
            self._evaluate_item(item=item, evidence_sources=evidence_sources)
            for item in checklist_items
        ]

        return {
            "items": evaluations,
            "summary": self._build_summary(evaluations, source_count=len(evidence_sources)),
        }

    def _coerce_project_state(self, state: Mapping[str, Any]) -> Mapping[str, Any]:
        nested_state = state.get("current_project_state")
        if isinstance(nested_state, Mapping):
            return nested_state
        return state

    def _extract_checklist_items(self, state: Mapping[str, Any]) -> list[dict[str, str]]:
        raw_waf = state.get("wafChecklist")
        if not isinstance(raw_waf, Mapping):
            return []

        raw_items = raw_waf.get("items")
        if isinstance(raw_items, Mapping):
            items_iterable: Iterable[Any] = [
                raw_items[key] for key in sorted(raw_items, key=lambda value: str(value))
            ]
        elif isinstance(raw_items, list | tuple):
            items_iterable = raw_items
        else:
            return []

        extracted: list[dict[str, str]] = []
        for item in items_iterable:
            if not isinstance(item, Mapping):
                continue

            item_id = str(item.get("id") or "").strip()
            topic = str(item.get("topic") or item.get("title") or "").strip()
            if not item_id or not topic:
                continue

            description = str(item.get("description") or "").strip()
            if not description:
                guidance = item.get("guidance")
                if isinstance(guidance, Mapping):
                    description = str(guidance.get("recommendation") or "").strip()

            extracted.append(
                {
                    "id": item_id,
                    "pillar": str(item.get("pillar") or "General").strip() or "General",
                    "topic": topic,
                    "description": description,
                }
            )

        return sorted(
            extracted,
            key=lambda item: (
                item["pillar"].casefold(),
                item["id"].casefold(),
                item["topic"].casefold(),
            ),
        )

    def _extract_evidence_sources(self, state: Mapping[str, Any]) -> list[dict[str, str]]:
        evidence: list[dict[str, str]] = []
        for key in _TEXT_SOURCE_KEYS:
            value = state.get(key)
            if value is None:
                continue
            evidence.extend(self._flatten_text(value=value, path=key))

        return sorted(
            (
                source
                for source in evidence
                if source["text"].strip()
            ),
            key=lambda source: source["path"],
        )

    def _flatten_text(self, *, value: Any, path: str) -> list[dict[str, str]]:
        if isinstance(value, str):
            return [{"path": path, "text": value.strip()}] if value.strip() else []
        if isinstance(value, Mapping):
            flattened: list[dict[str, str]] = []
            for key in sorted(value, key=lambda item: str(item)):
                child = value[key]
                child_path = f"{path}.{key}"
                flattened.extend(self._flatten_text(value=child, path=child_path))
            return flattened
        if isinstance(value, list | tuple):
            flattened = []
            for index, child in enumerate(value):
                flattened.extend(self._flatten_text(value=child, path=f"{path}[{index}]"))
            return flattened
        return []

    def _evaluate_item(
        self,
        *,
        item: Mapping[str, str],
        evidence_sources: list[dict[str, str]],
    ) -> dict[str, Any]:
        candidate_terms = self._candidate_terms(item)
        matched_sources: list[dict[str, Any]] = []
        term_hits: Counter[str] = Counter()

        for source in evidence_sources:
            matched_terms = self._match_terms_for_source(
                candidate_terms=candidate_terms,
                source_text=source["text"],
            )
            if not matched_terms:
                continue

            term_hits.update(matched_terms)
            matched_sources.append(
                {
                    "sourcePath": source["path"],
                    "matchedTerms": matched_terms,
                    "excerpt": source["text"][:240],
                }
            )

        matched_terms = sorted(term_hits)
        status = self._status_for_match_count(
            match_count=len(matched_terms),
            candidate_count=len(candidate_terms),
        )
        coverage_score = round(
            len(matched_terms) / len(candidate_terms) if candidate_terms else 0.0,
            3,
        )

        return {
            "itemId": item["id"],
            "pillar": item["pillar"],
            "topic": item["topic"],
            "status": status,
            "coverageScore": coverage_score,
            "matchedTerms": matched_terms,
            "matchedSourcePaths": [source["sourcePath"] for source in matched_sources],
            "evidence": matched_sources,
        }

    def _candidate_terms(self, item: Mapping[str, str]) -> list[tuple[str, str]]:
        text = " ".join(
            value.strip()
            for value in (item.get("topic"), item.get("description"))
            if isinstance(value, str) and value.strip()
        )
        terms: list[tuple[str, str]] = []
        seen: set[str] = set()
        for raw_term in re.findall(r"[a-z0-9']+", text.lower()):
            normalized = self._normalize_token(raw_term)
            if (
                len(normalized) < _MIN_TERM_LENGTH
                or normalized in _GENERIC_STOPWORDS
                or normalized in seen
            ):
                continue
            seen.add(normalized)
            terms.append((raw_term, normalized))
        return terms

    def _match_terms_for_source(
        self,
        *,
        candidate_terms: list[tuple[str, str]],
        source_text: str,
    ) -> list[str]:
        source_tokens = {
            self._normalize_token(token)
            for token in re.findall(r"[a-z0-9']+", source_text.lower())
        }
        return sorted(
            raw_term
            for raw_term, normalized in candidate_terms
            if normalized and normalized in source_tokens
        )

    def _normalize_token(self, token: str) -> str:
        normalized = token.strip().lower()
        if len(normalized) > 7 and normalized.endswith("ement"):
            normalized = normalized[:-5]
        elif (len(normalized) > 6 and normalized.endswith("ion")) or (len(normalized) > 6 and normalized.endswith("ing")):
            normalized = normalized[:-3]
        elif len(normalized) > 5 and normalized.endswith("ed"):
            normalized = normalized[:-2]
        if len(normalized) > 4 and normalized.endswith("ies"):
            normalized = normalized[:-3] + "y"
        if len(normalized) > 5 and normalized.endswith("s"):
            normalized = normalized[:-1]
        return normalized

    def _status_for_match_count(
        self,
        *,
        match_count: int,
        candidate_count: int,
    ) -> WafEvaluationStatus:
        if match_count >= self._required_match_count(candidate_count):
            return "fixed"
        if match_count > 0:
            return "in_progress"
        return "open"

    def _required_match_count(self, candidate_count: int) -> int:
        if candidate_count <= 0:
            return _FIXED_MATCH_THRESHOLD
        return min(_FIXED_MATCH_THRESHOLD, candidate_count)

    def _build_summary(
        self,
        evaluations: list[dict[str, Any]],
        *,
        source_count: int,
    ) -> dict[str, Any]:
        status_totals = {"fixed": 0, "in_progress": 0, "open": 0}
        pillars: dict[str, dict[str, int]] = {}

        for evaluation in evaluations:
            status = str(evaluation["status"])
            pillar = str(evaluation["pillar"])
            status_totals[status] += 1
            pillar_counts = pillars.setdefault(
                pillar,
                {"fixed": 0, "in_progress": 0, "open": 0},
            )
            pillar_counts[status] += 1

        return {
            "evaluatedItems": len(evaluations),
            "itemsByStatus": status_totals,
            "pillars": pillars,
            "sourceCount": source_count,
        }


__all__ = ["WAFEvaluatorService", "WafEvaluationStatus"]
