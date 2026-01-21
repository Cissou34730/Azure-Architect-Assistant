"""Tests for Microsoft Learn MCP client."""

import pytest

from app.services.mcp.exceptions import (
    MCPCapabilityError,
    MCPConfigurationError,
    MCPConnectionError,
)
from app.services.mcp.learn_mcp_client import MicrosoftLearnMCPClient


class TestMicrosoftLearnMCPClient:
    """Test suite for MicrosoftLearnMCPClient."""

    def test_init_valid_config(self):
        """Test client initialization with valid config."""
        config = {
            "endpoint": "https://learn.microsoft.com/api/mcp",
            "timeout": 30,
        }
        client = MicrosoftLearnMCPClient(config)

        assert client.endpoint == "https://learn.microsoft.com/api/mcp"
        assert client.timeout == 30
        assert client.auto_reconnect is True  # default
        assert client.max_retries == 3  # default

    def test_init_with_all_options(self):
        """Test client initialization with all config options."""
        config = {
            "endpoint": "https://learn.microsoft.com/api/mcp",
            "timeout": 60,
            "auto_reconnect": False,
            "max_retries": 5,
        }
        client = MicrosoftLearnMCPClient(config)

        assert client.endpoint == "https://learn.microsoft.com/api/mcp"
        assert client.timeout == 60
        assert client.auto_reconnect is False
        assert client.max_retries == 5

    def test_init_missing_endpoint(self):
        """Test client initialization fails without endpoint."""
        with pytest.raises(
            MCPConfigurationError, match="Config dictionary cannot be empty"
        ):
            MicrosoftLearnMCPClient({})

    def test_init_invalid_endpoint(self):
        """Test client initialization fails with invalid endpoint."""
        with pytest.raises(MCPConfigurationError, match="Invalid endpoint URL"):
            MicrosoftLearnMCPClient({"endpoint": "not-a-url"})

    def test_init_empty_config(self):
        """Test client initialization fails with empty config."""
        with pytest.raises(
            MCPConfigurationError, match="Config dictionary cannot be empty"
        ):
            MicrosoftLearnMCPClient(None)

    def test_list_tools_before_init(self):
        """Test that list_tools raises error before initialization."""
        config = {"endpoint": "https://learn.microsoft.com/api/mcp"}
        client = MicrosoftLearnMCPClient(config)

        with pytest.raises(MCPConnectionError, match="Client not initialized"):
            client.list_tools()

    @pytest.mark.asyncio
    async def test_call_tool_before_init(self):
        """Test that call_tool raises error before initialization."""
        config = {"endpoint": "https://learn.microsoft.com/api/mcp"}
        client = MicrosoftLearnMCPClient(config)

        with pytest.raises(MCPConnectionError, match="Client not initialized"):
            await client.call_tool("some_tool", {})

    @pytest.mark.asyncio
    async def test_close_before_init(self):
        """Test that close works even before initialization."""
        config = {"endpoint": "https://learn.microsoft.com/api/mcp"}
        client = MicrosoftLearnMCPClient(config)

        # Should not raise error
        await client.close()


@pytest.mark.integration
class TestMicrosoftLearnMCPClientIntegration:
    """Integration tests with real Microsoft Learn MCP server."""

    @pytest.mark.asyncio
    async def test_initialize_and_discover_tools(self):
        """Test connection to real Microsoft Learn MCP server."""
        config = {
            "endpoint": "https://learn.microsoft.com/api/mcp",
            "timeout": 30,
        }
        client = MicrosoftLearnMCPClient(config)

        try:
            await client.initialize()

            # Verify tools were discovered
            tools = client.list_tools()
            assert len(tools) > 0, "Should discover at least one tool"

            # Verify expected tools exist
            tool_names = [tool["name"] for tool in tools]
            assert "microsoft_docs_search" in tool_names
            assert "microsoft_docs_fetch" in tool_names
            assert "microsoft_code_sample_search" in tool_names

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test client works as async context manager."""
        config = {"endpoint": "https://learn.microsoft.com/api/mcp"}

        async with MicrosoftLearnMCPClient(config) as client:
            tools = client.list_tools()
            assert len(tools) > 0

        # Client should be closed after exiting context

    @pytest.mark.asyncio
    async def test_search_docs(self):
        """Test actual documentation search."""
        config = {"endpoint": "https://learn.microsoft.com/api/mcp"}

        async with MicrosoftLearnMCPClient(config) as client:
            result = await client.call_tool(
                "microsoft_docs_search", {"query": "Azure Container Apps"}
            )

            assert result is not None
            assert result["tool"] == "microsoft_docs_search"
            assert result["content"] is not None
            assert result["error"] is None

    @pytest.mark.asyncio
    async def test_fetch_docs(self):
        """Test fetching a documentation page."""
        config = {"endpoint": "https://learn.microsoft.com/api/mcp"}

        async with MicrosoftLearnMCPClient(config) as client:
            result = await client.call_tool(
                "microsoft_docs_fetch",
                {"url": "https://learn.microsoft.com/azure/container-apps/overview"},
            )

            assert result is not None
            assert result["tool"] == "microsoft_docs_fetch"
            assert result["content"] is not None
            assert result["error"] is None

    @pytest.mark.asyncio
    async def test_search_code_samples(self):
        """Test searching for code samples."""
        config = {"endpoint": "https://learn.microsoft.com/api/mcp"}

        async with MicrosoftLearnMCPClient(config) as client:
            result = await client.call_tool(
                "microsoft_code_sample_search",
                {"query": "Azure OpenAI chat", "language": "python"},
            )

            assert result is not None
            assert result["tool"] == "microsoft_code_sample_search"
            assert result["content"] is not None
            assert result["error"] is None

    @pytest.mark.asyncio
    async def test_invalid_tool_call(self):
        """Test calling a non-existent tool."""
        config = {"endpoint": "https://learn.microsoft.com/api/mcp"}

        async with MicrosoftLearnMCPClient(config) as client:
            with pytest.raises(MCPCapabilityError, match=r"Tool.*not found"):
                await client.call_tool("nonexistent_tool", {})

