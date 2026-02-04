import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents_system.checklists.processor import WafResultProcessor
from app.agents_system.checklists.engine import ChecklistEngine

@pytest.mark.asyncio
async def test_processor_extracts_state_update():
    mock_engine = AsyncMock(spec=ChecklistEngine)
    # Mock instantiate_checklist to return a mock checklist
    mock_engine.instantiate_checklist.return_value = MagicMock()
    mock_engine.get_project_checklist.return_value = MagicMock(id=1, completion_percentage=50.0)
    
    processor = WafResultProcessor(mock_engine)
    
    result = {
        "output": """
        I have evaluated your architecture.
        AAA_STATE_UPDATE: {
            "wafChecklist": {
                "slug": "waf-2024",
                "items": [
                    {
                        "id": "waf-item-1",
                        "evaluations": [{"status": "covered", "evidence": "good"}]
                    }
                ]
            }
        }
        """
    }
    
    await processor.process_orchestrator_result("proj-1", result)
    
    # Verify engine calls
    mock_engine.instantiate_checklist.assert_called_with("proj-1", "waf-2024")
    mock_engine.update_item_evaluation.assert_called()
    call_args = mock_engine.update_item_evaluation.call_args[1]
    assert call_args["item_id"] == "waf-item-1"
    assert call_args["status"] == "fulfilled"
    assert call_args["evidence"]["description"] == "good"
    
    mock_engine.calculate_progress.assert_called_with(1)

@pytest.mark.asyncio
async def test_processor_ignores_non_waf_updates():
    mock_engine = AsyncMock(spec=ChecklistEngine)
    processor = WafResultProcessor(mock_engine)
    
    result = {
        "output": "AAA_STATE_UPDATE: {\"other\": \"data\"}"
    }
    
    await processor.process_orchestrator_result("proj-1", result)
    mock_engine.update_item_evaluation.assert_not_called()
