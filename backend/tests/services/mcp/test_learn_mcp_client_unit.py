"""Unit tests for MicrosoftLearnMCPClient with mocked MCP session."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.mcp.exceptions import (
    MCPCapabilityError,
    MCPConnectionError,
    MCPTimeoutError,
)
from app.services.mcp.learn_mcp_client import MicrosoftLearnMCPClient


def _make_client() -> MicrosoftLearnMCPClient:
    return MicrosoftLearnMCPClient(
        {"endpoint": "https://learn.microsoft.com/api/mcp", "timeout": 10}
    )


class TestCallToolMocked:
    """Tests for call_tool using mocked internals."""

    @pytest.mark.asyncio
    async def test_call_tool_success(self):
        client = _make_client()
        client._initialized = True
        client._session = Mock()
        client._call_lock = AsyncMock()
        client._call_lock.__aenter__ = AsyncMock()
        client._call_lock.__aexit__ = AsyncMock()
        # Populate tool cache so _validate_tool_call passes
        mock_tool = Mock()
        mock_tool.name = "microsoft_docs_search"
        mock_tool.inputSchema = {"type": "object", "properties": {"query": {"type": "string"}}}
        client._tools_cache = {"microsoft_docs_search": mock_tool}

        mock_result = Mock()
        mock_result.content = [Mock(text='{"key": "value"}')]
        mock_result.content[0].text = '{"key": "value"}'
        client._session.call_tool = AsyncMock(return_value=mock_result)

        result = await client.call_tool("microsoft_docs_search", {"query": "test"})
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_call_tool_not_initialized_raises(self):
        client = _make_client()
        with pytest.raises(MCPConnectionError, match="not initialized"):
            await client.call_tool("any_tool", {})

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        client = _make_client()
        await client.close()
        await client.close()  # Should not raise


class TestListToolsMocked:
    """Tests for list_tools with mocked tool cache."""

    def test_list_tools_after_cache_populated(self):
        client = _make_client()
        client._initialized = True
        client._tools_cache = {
            "microsoft_docs_search": {"name": "microsoft_docs_search", "description": "Search docs"},
            "microsoft_docs_fetch": {"name": "microsoft_docs_fetch", "description": "Fetch page"},
        }

        tools = client.list_tools()
        assert len(tools) == 2
        names = {t["name"] for t in tools}
        assert "microsoft_docs_search" in names
        assert "microsoft_docs_fetch" in names

    def test_list_tools_empty_cache(self):
        client = _make_client()
        client._initialized = True
        client._tools_cache = {}

        tools = client.list_tools()
        assert tools == []
