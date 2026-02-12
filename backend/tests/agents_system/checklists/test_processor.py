import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents_system.checklists.processor import WafResultProcessor, find_json_blocks
from app.agents_system.checklists.engine import ChecklistEngine


# ---------------------------------------------------------------------------
# Unit tests for find_json_blocks utility
# ---------------------------------------------------------------------------


class TestFindJsonBlocks:
    def test_extracts_single_block(self) -> None:
        text = 'AAA_STATE_UPDATE: {"key": "value"}'
        result = find_json_blocks(text, "AAA_STATE_UPDATE:")
        assert len(result) == 1
        assert result[0] == {"key": "value"}

    def test_extracts_nested_block(self) -> None:
        text = 'AAA_STATE_UPDATE: {"wafChecklist": {"items": []}}'
        result = find_json_blocks(text, "AAA_STATE_UPDATE:")
        assert len(result) == 1
        assert result[0]["wafChecklist"]["items"] == []

    def test_skips_invalid_json(self) -> None:
        text = 'AAA_STATE_UPDATE: {invalid json}'
        result = find_json_blocks(text, "AAA_STATE_UPDATE:")
        assert len(result) == 0

    def test_handles_no_matches(self) -> None:
        text = "no updates here"
        result = find_json_blocks(text, "AAA_STATE_UPDATE:")
        assert result == []


# ---------------------------------------------------------------------------
# Unit tests for WafResultProcessor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_processor_delegates_to_engine() -> None:
    mock_engine = AsyncMock(spec=ChecklistEngine)
    mock_engine.default_template_slug.return_value = "azure-waf-reliability-v1"
    mock_engine.ensure_project_checklist.return_value = MagicMock()
    mock_engine.process_agent_result.return_value = {"status": "success"}

    processor = WafResultProcessor(mock_engine)

    result = {
        "output": """
        I have evaluated your architecture.
        AAA_STATE_UPDATE: {
            "wafChecklist": {
                "slug": "azure-waf-reliability-v1",
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

    # Verify the engine's ensure + process pipeline was invoked
    mock_engine.ensure_project_checklist.assert_called_once_with(
        "proj-1", "azure-waf-reliability-v1"
    )
    mock_engine.process_agent_result.assert_called_once()


@pytest.mark.asyncio
async def test_processor_ignores_non_waf_updates() -> None:
    mock_engine = AsyncMock(spec=ChecklistEngine)
    processor = WafResultProcessor(mock_engine)

    result = {
        "output": 'AAA_STATE_UPDATE: {"other": "data"}'
    }

    await processor.process_orchestrator_result("proj-1", result)
    mock_engine.process_agent_result.assert_not_called()
    mock_engine.ensure_project_checklist.assert_not_called()


@pytest.mark.asyncio
async def test_processor_ignores_empty_output() -> None:
    mock_engine = AsyncMock(spec=ChecklistEngine)
    processor = WafResultProcessor(mock_engine)

    await processor.process_orchestrator_result("proj-1", {"output": ""})
    mock_engine.process_agent_result.assert_not_called()


@pytest.mark.asyncio
async def test_processor_ignores_no_items() -> None:
    mock_engine = AsyncMock(spec=ChecklistEngine)
    mock_engine.default_template_slug.return_value = "azure-waf-reliability-v1"
    processor = WafResultProcessor(mock_engine)

    result = {
        "output": 'AAA_STATE_UPDATE: {"wafChecklist": {"slug": "azure-waf-reliability-v1", "items": []}}'
    }

    await processor.process_orchestrator_result("proj-1", result)
    mock_engine.ensure_project_checklist.assert_not_called()
