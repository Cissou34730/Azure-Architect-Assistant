import pytest
import uuid
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.backfill_service import BackfillService
from app.models.project import Project, ProjectState
from app.models.checklist import Checklist, ChecklistItem, ChecklistTemplate
from app.agents_system.checklists.engine import ChecklistEngine
from app.agents_system.checklists.registry import ChecklistRegistry

@pytest.fixture
async def backfill_service(test_db_session: AsyncSession, test_engine, test_registry):
    # Register a dummy template so sync doesn't fail
    test_registry.register_template(ChecklistTemplate(
        slug="azure-waf-v1",
        title="Azure WAF V1",
        version="1.0",
        source="test",
        source_url="http://test",
        source_version="1.0",
        content={"categories": []}
    ))
    
    # Wrap test_db_session in an async context manager
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def session_factory():
        yield test_db_session
        
    return BackfillService(engine=test_engine, db_session_factory=session_factory)

@pytest.mark.asyncio
async def test_backfill_project(backfill_service: BackfillService, test_db_session: AsyncSession):
    """Test backfilling a single project from JSON state to SQL."""
    project_id = str(uuid.uuid4())
    
    # Setup legacy JSON state
    legacy_state = {
        "wafChecklist": {
            "azure-waf-v1": {
                "title": "Azure WAF V1",
                "version": "1.0",
                "items": {
                    "item-1": {
                        "title": "Legacy Item 1",
                        "status": "completed",
                        "severity": "high",
                        "evidence": "Legacy evidence"
                    }
                }
            }
        }
    }
    
    # Create Project and ProjectState
    project = Project(id=project_id, name="Legacy Project")
    test_db_session.add(project)
    
    project_state = ProjectState(
        project_id=project_id,
        state=json.dumps(legacy_state)
    )
    test_db_session.add(project_state)
    await test_db_session.commit()
    
    # Run backfill
    result = await backfill_service.backfill_project(project_id)
    assert result["status"] == "success"
    
    # Verify database content
    stmt = select(Checklist).where(Checklist.project_id == project_id)
    res = await test_db_session.execute(stmt)
    checklist = res.scalar_one()
    assert checklist.title == "Azure WAF V1"
    
    stmt = select(ChecklistItem).where(ChecklistItem.checklist_id == checklist.id)
    res = await test_db_session.execute(stmt)
    items = res.scalars().all()
    assert len(items) == 1
    assert items[0].title == "Legacy Item 1"
    
    # Check evaluations
    from app.models.checklist import ChecklistItemEvaluation
    stmt = select(ChecklistItemEvaluation).where(ChecklistItemEvaluation.item_id == items[0].id)
    res = await test_db_session.execute(stmt)
    evals = res.scalars().all()
    assert len(evals) == 1
    assert evals[0].status == "fixed"

@pytest.mark.asyncio
async def test_verify_project_consistency(backfill_service: BackfillService, test_db_session: AsyncSession):
    """Test consistency verification between JSON and SQL."""
    project_id = str(uuid.uuid4())
    legacy_state = {
        "wafChecklist": {
            "azure-waf-v1": {
                "title": "Azure WAF V1",
                "version": "1.0",
                "items": {
                    "c1": {"title": "C1", "status": "fixed", "severity": "low"}
                }
            }
        }
    }
    
    # Create models
    project = Project(id=project_id, name="Test")
    test_db_session.add(project)
    project_state = ProjectState(project_id=project_id, state=json.dumps(legacy_state))
    test_db_session.add(project_state)
    await test_db_session.commit()
    
    # Initially inconsistent (SQL empty)
    is_consistent, diffs = await backfill_service.verify_project_consistency(project_id)
    assert is_consistent is False
    
    # Backfill
    await backfill_service.backfill_project(project_id)
    
    # Now consistent
    is_consistent, diffs = await backfill_service.verify_project_consistency(project_id)
    assert is_consistent is True, f"Consistency check failed: {diffs}"
