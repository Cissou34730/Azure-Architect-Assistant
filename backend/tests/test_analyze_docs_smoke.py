import json

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models import Project, ProjectDocument, ProjectState
from app.models.project import Base
from app.routers.project_management.services.document_service import DocumentService


@pytest.mark.asyncio
async def test_analyze_docs_persists_ingestion_stats_and_requirements(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    class _StubLlmService:
        async def analyze_documents(self, document_texts: list[str]) -> dict:
            # Minimal shape expected by DocumentService; UUIDs are added by normalization.
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

    import app.services.llm_service as llm_service

    monkeypatch.setattr(llm_service, "get_llm_service", lambda: _StubLlmService())

    async with session_factory() as session:
        project = Project(id="p-1", name="Test Project")
        session.add(project)
        session.add_all(
            [
                ProjectDocument(
                    id="d-1",
                    project_id=project.id,
                    file_name="a.txt",
                    mime_type="text/plain",
                    raw_text="hello",
                ),
                ProjectDocument(
                    id="d-2",
                    project_id=project.id,
                    file_name="empty.txt",
                    mime_type="text/plain",
                    raw_text="",
                ),
            ]
        )
        await session.commit()

        service = DocumentService()
        state = await service.analyze_documents(project.id, session)

        assert isinstance(state.get("ingestionStats"), dict)
        assert state["ingestionStats"]["attemptedDocuments"] == 2
        assert state["ingestionStats"]["parsedDocuments"] == 1
        assert state["ingestionStats"]["failedDocuments"] == 1
        assert isinstance(state["ingestionStats"]["failures"], list)

        assert isinstance(state.get("requirements"), list)
        assert state["requirements"], "requirements should not be empty"
        assert isinstance(state["requirements"][0].get("id"), str) and state["requirements"][0]["id"]

        # Confirm persistence into ProjectState
        result = await session.execute(select(ProjectState).where(ProjectState.project_id == project.id))
        persisted = result.scalar_one_or_none()
        assert persisted is not None

        persisted_payload = json.loads(persisted.state)
        assert "ingestionStats" in persisted_payload
        assert "requirements" in persisted_payload

