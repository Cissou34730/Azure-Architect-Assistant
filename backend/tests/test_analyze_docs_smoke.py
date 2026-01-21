import json

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models import Project, ProjectDocument, ProjectState
from app.models.project import Base
from app.routers.project_management.services.document_service import DocumentService


@pytest.fixture
async def setup_test_db(engine):
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_session


@pytest.mark.asyncio
async def test_analyze_docs_persists_ingestion_stats_and_requirements(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    class _StubLlmService:
        async def analyze_documents(self, document_texts: list[str]) -> dict:
            return {
                "requirements": [
                    {
                        "category": "business",
                        "text": "Must support multi-region users",
                        "ambiguity": {"isAmbiguous": False, "notes": ""},
                        "sources": [],
                    }
                ],
                "clarificationQuestions": [],
            }

    from app.services import llm_service  # noqa: PLC0415
    monkeypatch.setattr(llm_service, "get_llm_service", lambda: _StubLlmService())

    async with async_session() as session:
        project = Project(id="p-1", name="Test Project")
        session.add(project)
        session.add_all([
            ProjectDocument(id="d-1", project_id=project.id, file_name="a.txt", raw_text="hello"),
            ProjectDocument(id="d-2", project_id=project.id, file_name="empty.txt", raw_text=""),
        ])
        await session.commit()

        service = DocumentService()
        state = await service.analyze_documents(project.id, session)

        _verify_ingestion_stats(state)
        _verify_requirements(state)

        # Confirm persistence into ProjectState
        result = await session.execute(select(ProjectState).where(ProjectState.project_id == project.id))
        persisted = result.scalar_one_or_none()
        assert persisted is not None
        assert "ingestionStats" in json.loads(persisted.state)


def _verify_ingestion_stats(state: dict) -> None:
    stats = state.get("ingestionStats", {})
    assert stats.get("attemptedDocuments") == 2
    assert stats.get("parsedDocuments") == 1
    assert stats.get("failedDocuments") == 1


def _verify_requirements(state: dict) -> None:
    reqs = state.get("requirements", [])
    assert reqs, "requirements should not be empty"
    assert isinstance(reqs[0].get("id"), str)


