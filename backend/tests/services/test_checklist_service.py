"""
Tests for ChecklistService.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.checklist import ChecklistItemEvaluation


@pytest.mark.asyncio
async def test_service_sync_project(test_checklist_service):
    """Test synchronizing a project via the service."""
    project_id = str(uuid4())
    project_state = {
        "wafChecklist": {
            "templates": [
                {
                    "slug": "waf-2024",
                    "title": "WAF 2024",
                    "version": "1.0",
                    "items": ["item1", "item2"]
                }
            ],
            "evaluations": []
        }
    }

    # Mock engine.sync_project_state_to_db
    test_checklist_service.engine.sync_project_state_to_db = AsyncMock(return_value={"status": "success"})

    await test_checklist_service.sync_project(project_id, project_state)

    test_checklist_service.engine.sync_project_state_to_db.assert_called_once_with(
        project_id, project_state, None
    )

@pytest.mark.asyncio
async def test_service_get_progress(test_checklist_service):
    """Test getting progress via the service."""
    project_id = str(uuid4())
    test_checklist_service.engine.compute_progress = AsyncMock(return_value={"percent_complete": 50})

    result = await test_checklist_service.get_progress(project_id)

    assert result["percent_complete"] == 50
    test_checklist_service.engine.compute_progress.assert_called_once_with(project_id, None)

@pytest.mark.asyncio
async def test_service_evaluate_item(test_checklist_service):
    """Test evaluating an item via the service."""
    project_id = str(uuid4())
    item_id = uuid4()
    payload = {"status": "fixed", "evidence": "good stuff"}

    mock_eval = MagicMock(spec=ChecklistItemEvaluation)
    test_checklist_service.engine.evaluate_item = AsyncMock(return_value=mock_eval)

    result = await test_checklist_service.evaluate_item(project_id, item_id, payload)

    assert result == mock_eval
    test_checklist_service.engine.evaluate_item.assert_called_once_with(project_id, item_id, payload)

@pytest.mark.asyncio
async def test_service_list_next_actions(test_checklist_service):
    """Test listing next actions via the service."""
    project_id = str(uuid4())
    test_checklist_service.engine.list_next_actions = AsyncMock(return_value=[{"id": "item1"}])

    result = await test_checklist_service.list_next_actions(project_id, limit=5)

    assert len(result) == 1
    assert result[0]["id"] == "item1"
    test_checklist_service.engine.list_next_actions.assert_called_once_with(project_id, 5, None)


@pytest.mark.asyncio
async def test_service_ensure_project_checklist(test_checklist_service):
    project_id = str(uuid4())
    test_checklist_service.engine.ensure_project_checklists = AsyncMock(return_value=[MagicMock()])

    result = await test_checklist_service.ensure_project_checklist(project_id)

    assert result is True
    test_checklist_service.engine.ensure_project_checklists.assert_called_once_with(project_id, None)
