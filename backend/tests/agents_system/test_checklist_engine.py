"""
Integration tests for ChecklistEngine with database.
"""

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.checklist import (
    Checklist,
    ChecklistItem,
    ChecklistItemEvaluation,
)
from app.models.project import Project


@pytest.mark.asyncio
async def test_engine_sync_full_workflow(test_engine, test_db_session, test_registry):
    """
    Test the full workflow:
    1. Synchronize from project state (JSON -> DB)
    2. Reconstruct state (DB -> JSON)
    3. Verify consistency
    """
    project_id = str(uuid4())

    # Pre-requisite: Project must exist in DB
    project = Project(id=project_id, name="Test Project")
    test_db_session.add(project)
    await test_db_session.commit()

    # 1. Prepare legacy state
    project_state = {
        "wafChecklist": {
            "template": "azure-waf-v1",
            "items": [
                {"id": "sec-01", "evaluations": [{"status": "covered", "evidence": "MFA enabled"}]},
                {"id": "rel-01", "evaluations": [{"status": "partial", "evidence": "Backups configured but not tested"}]}
            ]
        }
    }

    # 2. Sync to DB
    await test_engine.sync_project_state_to_db(project_id, project_state)

    # 3. Verify records in DB
    result = await test_db_session.execute(select(Checklist).where(Checklist.project_id == project_id))
    checklist = result.scalar_one()
    assert checklist.template_slug == "azure-waf-v1"

    result = await test_db_session.execute(select(ChecklistItem).where(ChecklistItem.checklist_id == checklist.id))
    items = result.scalars().all()
    assert len(items) == 2

    sec_item = next(i for i in items if i.template_item_id == "sec-01")
    assert sec_item.pillar == "Security"
    assert (sec_item.severity.value if hasattr(sec_item.severity, "value") else sec_item.severity) == "high"

    # 4. Sync back to state (DB -> JSON)
    reconstructed = await test_engine.sync_db_to_project_state(project_id)

    waf_json = reconstructed.get("azure-waf-v1", {})
    assert waf_json["version"] == "1.0"
    assert len(waf_json["items"]) == 2

    # 5. Idempotency test: Sync again with same data
    await test_engine.sync_project_state_to_db(project_id, project_state)

    # Counts should remain the same
    result = await test_db_session.execute(select(ChecklistItem).where(ChecklistItem.checklist_id == checklist.id))
    assert len(result.scalars().all()) == 2

@pytest.mark.asyncio
async def test_engine_process_agent_result(test_engine, test_db_session):
    """Test processing agent results containing WAF evaluations."""
    project_id = str(uuid4())

    # Pre-requisite
    project = Project(id=project_id, name="Test Project")
    test_db_session.add(project)
    await test_db_session.commit()

    agent_result = {
        "output": "I have evaluated the security of the architecture.",
        "AAA_STATE_UPDATE": {
            "wafChecklist": {
                "template": "azure-waf-v1",
                "items": [
                    {
                        "id": "sec-01",
                        "pillar": "Security",
                        "topic": "Secure Admin Access",
                        "evaluations": [
                            {
                                "status": "covered",
                                "evidence": "Managed identities are used everywhere.",
                                "evaluator": "SecurityAgent"
                            }
                        ]
                    }
                ]
            }
        }
    }

    # First need to have the items in DB for agent to evaluate
    # Simulate a minimal sync first or initialize
    minimal_state = {
        "wafChecklist": {
            "template": "azure-waf-v1",
            "items": []
        }
    }
    await test_engine.sync_project_state_to_db(project_id, minimal_state)

    # Process agent result
    summary = await test_engine.process_agent_result(project_id, agent_result)
    assert summary["items_processed"] == 1

    # Verify evaluation record
    result = await test_db_session.execute(
        select(ChecklistItemEvaluation).join(ChecklistItem).join(Checklist).where(Checklist.project_id == project_id)
    )
    evaluation = result.scalar_one()
    assert evaluation.status == "fixed"
    assert evaluation.evaluator == "SecurityAgent"

@pytest.mark.asyncio
async def test_engine_compute_progress(test_engine, test_db_session):
    """Test progress computation."""
    project_id = str(uuid4())

    # Pre-requisite
    project = Project(id=project_id, name="Test Project")
    test_db_session.add(project)
    await test_db_session.commit()

    # Create checklist with 2 items, 1 fulfilled
    state = {
        "wafChecklist": {
            "template": "azure-waf-v1",
            "items": [
                {"id": "i1", "evaluations": [{"status": "covered", "evidence": "done"}]},
                {"id": "i2", "evaluations": [{"status": "notCovered", "evidence": "todo"}]}
            ]
        }
    }
    await test_engine.sync_project_state_to_db(project_id, state)

    progress = await test_engine.compute_progress(project_id)
    assert progress["total_items"] == 2
    assert progress["completed_items"] == 1
    assert progress["percent_complete"] == 50.0

@pytest.mark.asyncio
async def test_engine_list_next_actions(test_engine, test_db_session):
    """Test listing next actions prioritized by severity."""
    project_id = str(uuid4())

    # Pre-requisite
    project = Project(id=project_id, name="Test Project")
    test_db_session.add(project)
    await test_db_session.commit()

    # Create 3 items with different severities, none fulfilled
    state = {
        "wafChecklist": {
            "template": "azure-waf-v1",
            "items": [
                {"id": "low", "title": "Low Item", "severity": "low"},
                {"id": "high", "title": "High Item", "severity": "high"},
                {"id": "crit", "title": "Crit Item", "severity": "critical"},
            ]
        }
    }
    await test_engine.sync_project_state_to_db(project_id, state)

    actions = await test_engine.list_next_actions(project_id, limit=3)
    assert len(actions) == 3
    assert actions[0]["template_item_id"] == "crit"
    assert actions[1]["template_item_id"] == "high"
    assert actions[2]["template_item_id"] == "low"


@pytest.mark.asyncio
async def test_engine_ensure_project_checklist_bootstraps_template_items(
    test_engine, test_db_session
):
    """Bootstrap creates checklist + items even without prior WAF evaluations."""
    project_id = str(uuid4())
    project = Project(id=project_id, name="Bootstrap Test")
    test_db_session.add(project)
    await test_db_session.commit()

    checklist = await test_engine.ensure_project_checklist(project_id, "azure-waf-v1")
    assert checklist is not None

    result = await test_db_session.execute(
        select(Checklist).where(Checklist.project_id == project_id)
    )
    persisted = result.scalar_one()

    items_result = await test_db_session.execute(
        select(ChecklistItem).where(ChecklistItem.checklist_id == persisted.id)
    )
    items = items_result.scalars().all()
    assert len(items) == 2
