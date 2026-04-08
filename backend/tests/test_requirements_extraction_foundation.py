from __future__ import annotations

import pytest

from app.features.agent.application.requirements_extraction_service import (
    RequirementsExtractionService,
)
from app.features.agent.contracts.extract_requirements import (
    ExtractedRequirementContract,
    RequirementAmbiguityContract,
    RequirementSourceContract,
    RequirementsExtractionResultContract,
)


def _source(document_id: str, excerpt: str, location: str) -> RequirementSourceContract:
    return RequirementSourceContract(
        document_id=document_id,
        excerpt=excerpt,
        location=location,
    )


def _requirement(
    *,
    text: str,
    category: str = "functional",
    ambiguous: bool = False,
    notes: str = "",
    sources: list[RequirementSourceContract] | None = None,
) -> ExtractedRequirementContract:
    return ExtractedRequirementContract(
        text=text,
        category=category,
        ambiguity=RequirementAmbiguityContract(
            is_ambiguous=ambiguous,
            notes=notes,
        ),
        sources=sources or [_source("doc-1", "excerpt", "p1")],
    )


def test_merge_requirements_deduplicates_exact_matches_and_preserves_sources() -> None:
    service = RequirementsExtractionService()

    merged = service.merge_requirements(
        [
            _requirement(
                text="Support SSO for internal users",
                sources=[_source("doc-1", "SSO is required", "p2")],
            ),
            _requirement(
                text="Support SSO for internal users",
                sources=[_source("doc-2", "Users authenticate with Entra ID", "p4")],
            ),
        ]
    )

    assert len(merged) == 1
    assert merged[0].text == "Support SSO for internal users"
    assert {source.document_id for source in merged[0].sources} == {"doc-1", "doc-2"}


def test_merge_requirements_propagates_ambiguity_notes() -> None:
    service = RequirementsExtractionService()

    merged = service.merge_requirements(
        [
            _requirement(
                text="System must be highly scalable",
                ambiguous=False,
                notes="",
                sources=[_source("doc-1", "highly scalable", "p5")],
            ),
            _requirement(
                text="System must be highly scalable",
                ambiguous=True,
                notes="Scalable is not quantified",
                sources=[_source("doc-2", "must be highly scalable", "p7")],
            ),
        ]
    )

    assert len(merged) == 1
    assert merged[0].ambiguity.is_ambiguous is True
    assert "not quantified" in merged[0].ambiguity.notes


def test_build_result_counts_ambiguities_and_keeps_assumptions() -> None:
    service = RequirementsExtractionService()

    result = service.build_result(
        requirements=[
            _requirement(text="Support audit logs", ambiguous=False),
            _requirement(
                text="Provide real-time analytics",
                category="nfr",
                ambiguous=True,
                notes="Real-time is undefined",
            ),
        ],
        assumptions=["Analytics latency target will be clarified"],
        chunks_processed=3,
    )

    assert isinstance(result, RequirementsExtractionResultContract)
    assert result.ambiguities_detected == 1
    assert result.assumptions == ["Analytics latency target will be clarified"]
    assert result.chunks_processed == 3


def test_extracted_requirement_requires_at_least_one_source() -> None:
    with pytest.raises(ValueError, match="at least one source"):
        ExtractedRequirementContract(
            text="Support audit logs",
            category="functional",
            ambiguity=RequirementAmbiguityContract(is_ambiguous=False, notes=""),
            sources=[],
        )
