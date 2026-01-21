import json

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.agents_system.services.project_context import update_project_state
from app.models import Project, ProjectState
from app.models.project import Base


@pytest.mark.asyncio
async def test_update_project_state_no_overwrite_surfaces_conflicts() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        project = Project(id="p-1", name="Test Project")
        session.add(project)
        session.add(
            ProjectState(
                project_id=project.id,
                state=json.dumps({"nfrs": {"availability": "99.9%"}}),
            )
        )
        await session.commit()

        updated = await update_project_state(
            project.id,
            updates={"nfrs": {"availability": "99.99%"}},
            db=session,
            merge=True,
        )

        # Existing value should be preserved
        assert updated.get("nfrs", {}).get("availability") == "99.9%"

        # Conflicts should be surfaced
        conflicts = updated.get("conflicts")
        assert isinstance(conflicts, list)
        assert any(c.get("path") == "nfrs.availability" for c in conflicts if isinstance(c, dict))

        # Persisted state should also keep the existing value
        result = await session.execute(select(ProjectState).where(ProjectState.project_id == project.id))
        persisted = result.scalar_one_or_none()
        assert persisted is not None
        persisted_state = json.loads(persisted.state)
        assert persisted_state.get("nfrs", {}).get("availability") == "99.9%"

