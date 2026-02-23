"""Tests for enriched project context summary.

Verifies that get_project_context_summary includes requirements,
technical constraints, data compliance, document excerpts,
and clarification questions in the agent context.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.agents_system.services.project_context import (
    _add_clarification_questions_section,
    _add_data_compliance_section,
    _add_document_excerpts_section,
    _add_requirements_section,
    _add_technical_constraints_section,
    get_project_context_summary,
)
from app.models.project import Base, Project, ProjectDocument, ProjectState


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session
    await engine.dispose()


def _state_with(overrides: dict[str, Any]) -> dict[str, Any]:
    """Build a minimal valid state dict with overrides."""
    base: dict[str, Any] = {
        "context": {"summary": "Test project"},
        "nfrs": {},
        "applicationStructure": {},
        "openQuestions": [],
    }
    base.update(overrides)
    return base


# ── Requirements section ──────────────────────────────────────────────

class TestAddRequirementsSection:
    def test_adds_requirements_when_present(self) -> None:
        parts: list[str] = []
        state = _state_with(
            {
                "requirements": [
                    {
                        "id": "r1",
                        "category": "business",
                        "text": "The system must support 1000 concurrent users",
                        "sources": [{"fileName": "rfp.pdf", "excerpt": "1000 users"}],
                    },
                    {
                        "id": "r2",
                        "category": "nfr",
                        "text": "99.9% availability SLA",
                        "ambiguity": {"isAmbiguous": True, "notes": "Which region?"},
                    },
                ]
            }
        )
        _add_requirements_section(parts, state)
        text = "\n".join(parts)
        assert "REQUIREMENTS:" in text
        assert "[business]" in text
        assert "1000 concurrent users" in text
        assert "[nfr]" in text
        assert "99.9% availability" in text
        assert "AMBIGUOUS" in text
        assert "Which region?" in text
        assert "Source: rfp.pdf" in text

    def test_no_section_when_empty(self) -> None:
        parts: list[str] = []
        _add_requirements_section(parts, _state_with({"requirements": []}))
        assert parts == []

    def test_no_section_when_missing(self) -> None:
        parts: list[str] = []
        _add_requirements_section(parts, _state_with({}))
        assert parts == []


# ── Technical constraints section ─────────────────────────────────────

class TestAddTechnicalConstraintsSection:
    def test_adds_constraints_and_assumptions(self) -> None:
        parts: list[str] = []
        state = _state_with(
            {
                "technicalConstraints": {
                    "constraints": ["Must use Azure only", "No on-prem"],
                    "assumptions": ["Team has Azure DevOps experience"],
                }
            }
        )
        _add_technical_constraints_section(parts, state)
        text = "\n".join(parts)
        assert "TECHNICAL CONSTRAINTS:" in text
        assert "Must use Azure only" in text
        assert "No on-prem" in text
        assert "Assumptions:" in text
        assert "Azure DevOps experience" in text

    def test_no_section_when_empty(self) -> None:
        parts: list[str] = []
        _add_technical_constraints_section(parts, _state_with({"technicalConstraints": {}}))
        assert parts == []


# ── Data compliance section ───────────────────────────────────────────

class TestAddDataComplianceSection:
    def test_adds_data_compliance(self) -> None:
        parts: list[str] = []
        state = _state_with(
            {
                "dataCompliance": {
                    "dataTypes": ["PII", "financial"],
                    "complianceRequirements": ["GDPR", "SOC 2"],
                    "dataResidency": "EU only",
                }
            }
        )
        _add_data_compliance_section(parts, state)
        text = "\n".join(parts)
        assert "DATA COMPLIANCE:" in text
        assert "PII" in text
        assert "GDPR" in text
        assert "EU only" in text

    def test_no_section_when_empty(self) -> None:
        parts: list[str] = []
        _add_data_compliance_section(parts, _state_with({"dataCompliance": {}}))
        assert parts == []


# ── Document excerpts section ─────────────────────────────────────────

class TestAddDocumentExcerptsSection:
    def test_adds_document_excerpts(self) -> None:
        parts: list[str] = []
        state = _state_with(
            {
                "referenceDocuments": [
                    {
                        "id": "d1",
                        "title": "requirements.pdf",
                        "category": "uploaded",
                        "parseStatus": "parsed",
                    },
                    {
                        "id": "d2",
                        "title": "architecture.docx",
                        "category": "uploaded",
                        "parseStatus": "parsed",
                    },
                ]
            }
        )
        documents_text = {
            "d1": "Full text of requirements document with details about...",
            "d2": "Architecture overview describing microservices...",
        }
        _add_document_excerpts_section(parts, state, documents_text)
        text = "\n".join(parts)
        assert "UPLOADED DOCUMENTS:" in text
        assert "requirements.pdf" in text
        assert "architecture.docx" in text

    def test_no_section_when_no_documents(self) -> None:
        parts: list[str] = []
        _add_document_excerpts_section(parts, _state_with({}), {})
        assert parts == []


# ── Clarification questions section ───────────────────────────────────

class TestAddClarificationQuestionsSection:
    def test_adds_clarification_questions(self) -> None:
        parts: list[str] = []
        state = _state_with(
            {
                "clarificationQuestions": [
                    {"question": "What is the expected budget?", "priority": 1},
                    {"question": "Which Azure regions?", "priority": 2},
                ]
            }
        )
        _add_clarification_questions_section(parts, state)
        text = "\n".join(parts)
        assert "CLARIFICATION QUESTIONS:" in text
        assert "expected budget" in text
        assert "Azure regions" in text

    def test_no_section_when_empty(self) -> None:
        parts: list[str] = []
        _add_clarification_questions_section(parts, _state_with({"clarificationQuestions": []}))
        assert parts == []


# ── Integration: get_project_context_summary ──────────────────────────

class TestGetProjectContextSummaryEnriched:
    @pytest.mark.asyncio
    async def test_includes_requirements_in_summary(self, db: AsyncSession) -> None:
        """The context summary should include extracted requirements."""
        project = Project(id="p1", name="Test Project")
        db.add(project)

        state_data = _state_with(
            {
                "requirements": [
                    {"id": "r1", "category": "functional", "text": "Support multi-tenancy"},
                ],
                "technicalConstraints": {
                    "constraints": ["Azure-only deployment"],
                    "assumptions": [],
                },
                "dataCompliance": {
                    "dataTypes": ["PII"],
                    "complianceRequirements": ["GDPR"],
                    "dataResidency": "EU",
                },
            }
        )
        db.add(
            ProjectState(
                project_id="p1",
                state=json.dumps(state_data),
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        await db.commit()

        with patch(
            "app.agents_system.services.project_context.is_mindmap_initialized",
            return_value=False,
        ):
            summary = await get_project_context_summary("p1", db)

        assert "REQUIREMENTS:" in summary
        assert "multi-tenancy" in summary
        assert "TECHNICAL CONSTRAINTS:" in summary
        assert "Azure-only" in summary
        assert "DATA COMPLIANCE:" in summary
        assert "GDPR" in summary

    @pytest.mark.asyncio
    async def test_includes_document_excerpts_in_summary(self, db: AsyncSession) -> None:
        """The context summary should include uploaded document excerpts."""
        project = Project(id="p2", name="Doc Project")
        db.add(project)

        doc = ProjectDocument(
            id="doc1",
            project_id="p2",
            file_name="spec.pdf",
            mime_type="application/pdf",
            raw_text="This is the full specification document content with important details.",
            parse_status="parsed",
            analysis_status="analyzed",
            uploaded_at="2026-01-01T00:00:00Z",
        )
        db.add(doc)

        state_data = _state_with(
            {
                "referenceDocuments": [
                    {
                        "id": "doc1",
                        "title": "spec.pdf",
                        "category": "uploaded",
                        "parseStatus": "parsed",
                        "accessedAt": "2026-01-01T00:00:00Z",
                    }
                ],
            }
        )
        db.add(
            ProjectState(
                project_id="p2",
                state=json.dumps(state_data),
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        await db.commit()

        with patch(
            "app.agents_system.services.project_context.is_mindmap_initialized",
            return_value=False,
        ):
            summary = await get_project_context_summary("p2", db)

        assert "UPLOADED DOCUMENTS:" in summary
        assert "spec.pdf" in summary
