"""Tests for the project document search tool.

Verifies that agents can query uploaded document content via a tool.
"""

from __future__ import annotations

import json
from typing import Any
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.agents_system.tools.project_document_tool import (
    ProjectDocumentSearchTool,
    search_project_documents,
)
from app.models.project import Base, Project, ProjectDocument


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession]:
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


@pytest.fixture
def sample_project_with_docs(db):
    """Setup helper returning an async function to seed the DB."""

    async def _setup() -> str:
        project = Project(id="proj1", name="Test Project")
        db.add(project)

        doc1 = ProjectDocument(
            id="doc1",
            project_id="proj1",
            file_name="requirements.pdf",
            mime_type="application/pdf",
            raw_text=(
                "The system must support 1000 concurrent users. "
                "Authentication must use Azure AD with MFA. "
                "Data must be stored in EU regions only. "
                "The application should support multi-tenancy."
            ),
            parse_status="parsed",
            analysis_status="analyzed",
            uploaded_at="2026-01-01T00:00:00Z",
        )
        doc2 = ProjectDocument(
            id="doc2",
            project_id="proj1",
            file_name="architecture.docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            raw_text=(
                "The architecture uses a microservices pattern with Azure Kubernetes Service. "
                "API Gateway via Azure API Management. "
                "Cosmos DB for NoSQL storage and Azure SQL for relational data."
            ),
            parse_status="parsed",
            analysis_status="analyzed",
            uploaded_at="2026-01-01T00:00:00Z",
        )
        doc3 = ProjectDocument(
            id="doc3",
            project_id="proj1",
            file_name="broken.pdf",
            mime_type="application/pdf",
            raw_text="",
            parse_status="parse_failed",
            parse_error="Could not extract text",
            uploaded_at="2026-01-01T00:00:00Z",
        )
        db.add_all([doc1, doc2, doc3])
        await db.commit()
        return "proj1"

    return _setup


class TestSearchProjectDocuments:
    @pytest.mark.asyncio
    async def test_keyword_search_finds_matching_documents(
        self, db: AsyncSession, sample_project_with_docs
    ) -> None:
        project_id = await sample_project_with_docs()
        results = await search_project_documents(project_id, "concurrent users", db)
        assert len(results) >= 1
        assert any("concurrent users" in r["excerpt"].lower() for r in results)

    @pytest.mark.asyncio
    async def test_keyword_search_returns_document_metadata(
        self, db: AsyncSession, sample_project_with_docs
    ) -> None:
        project_id = await sample_project_with_docs()
        results = await search_project_documents(project_id, "microservices", db)
        assert len(results) >= 1
        result = results[0]
        assert "documentId" in result
        assert "fileName" in result
        assert "excerpt" in result

    @pytest.mark.asyncio
    async def test_skips_failed_parse_documents(
        self, db: AsyncSession, sample_project_with_docs
    ) -> None:
        project_id = await sample_project_with_docs()
        results = await search_project_documents(project_id, "broken", db)
        # doc3 has parse_failed status and empty text, should not appear
        assert all(r["fileName"] != "broken.pdf" for r in results)

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_match(
        self, db: AsyncSession, sample_project_with_docs
    ) -> None:
        project_id = await sample_project_with_docs()
        results = await search_project_documents(
            project_id, "xyznonexistentterm", db
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_for_missing_project(
        self, db: AsyncSession
    ) -> None:
        results = await search_project_documents("nonexistent", "query", db)
        assert results == []


class TestProjectDocumentSearchTool:
    def test_tool_has_correct_name_and_description(self) -> None:
        tool = ProjectDocumentSearchTool()
        assert tool.name == "project_document_search"
        assert "uploaded" in tool.description.lower() or "document" in tool.description.lower()
