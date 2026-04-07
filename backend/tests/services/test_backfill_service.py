import json
import uuid
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.checklists.application.backfill_service import BackfillService
from app.models.checklist import Checklist, ChecklistItem, ChecklistTemplate
from app.models.project import Project, ProjectState


@pytest.fixture
async def backfill_service(test_db_session: AsyncSession, test_engine, test_registry):
    # Ensure a template exists in the registry for checklist bootstrap.
    test_registry.register_template(
        ChecklistTemplate(
            slug="azure-waf-v1",
            title="Azure WAF V1",
            version="1.0",
            source="test",
            source_url="http://test",
            source_version="1.0",
            content={
                "items": [
                    {"id": "item-1", "title": "Legacy Item 1", "pillar": "Security", "severity": "high"}
                ]
            },
        )
    )

    @asynccontextmanager
    async def session_factory():
        yield test_db_session

    return BackfillService(engine=test_engine, db_session_factory=session_factory)


@pytest.mark.asyncio
async def test_backfill_project_bootstraps_normalized_checklist(
    backfill_service: BackfillService, test_db_session: AsyncSession
):
    project_id = str(uuid.uuid4())
    project = Project(id=project_id, name="Bootstrap Project")
    test_db_session.add(project)
    test_db_session.add(ProjectState(project_id=project_id, state=json.dumps({})))
    await test_db_session.commit()

    result = await backfill_service.backfill_project(project_id)
    assert result["status"] == "success"
    assert result["checklists_ensured"] >= 1

    checklist = (
        await test_db_session.execute(
            select(Checklist).where(Checklist.project_id == project_id)
        )
    ).scalar_one()
    items = (
        await test_db_session.execute(
            select(ChecklistItem).where(ChecklistItem.checklist_id == checklist.id)
        )
    ).scalars().all()
    assert len(items) >= 1


@pytest.mark.asyncio
async def test_verify_project_consistency_checks_normalized_rows(
    backfill_service: BackfillService, test_db_session: AsyncSession
):
    project_id = str(uuid.uuid4())
    project = Project(id=project_id, name="Consistency Test")
    test_db_session.add(project)
    test_db_session.add(ProjectState(project_id=project_id, state=json.dumps({})))
    await test_db_session.commit()

    consistent_before, _ = await backfill_service.verify_project_consistency(project_id)
    assert consistent_before is False

    await backfill_service.backfill_project(project_id)

    consistent_after, diffs = await backfill_service.verify_project_consistency(project_id)
    assert consistent_after is True
    assert diffs == []

