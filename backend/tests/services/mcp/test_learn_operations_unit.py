"""Unit tests for MCP operations with mocked client."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.shared.mcp.operations.learn_operations import (
    fetch_documentation,
    get_azure_guidance,
    search_code_samples,
    search_microsoft_docs,
)


@pytest.fixture
def mock_client():
    client = Mock()
    client.call_tool = AsyncMock()
    return client


class TestSearchMicrosoftDocs:
    @pytest.mark.asyncio
    async def test_returns_results(self, mock_client):
        mock_client.call_tool.return_value = {
            "content": [
                {"title": "Azure App Service", "content": "Overview...", "contentUrl": "https://..."}
            ],
            "meta": {"duration_ms": 100},
        }
        result = await search_microsoft_docs(mock_client, "Azure App Service")
        assert result["query"] == "Azure App Service"
        assert len(result["results"]) == 1
        assert result["total_results"] == 1

    @pytest.mark.asyncio
    async def test_respects_max_results(self, mock_client):
        mock_client.call_tool.return_value = {
            "content": [{"title": f"Doc {i}"} for i in range(10)],
        }
        result = await search_microsoft_docs(mock_client, "test", max_results=3)
        assert len(result["results"]) == 3

    @pytest.mark.asyncio
    async def test_empty_response(self, mock_client):
        mock_client.call_tool.return_value = {"content": []}
        result = await search_microsoft_docs(mock_client, "nothing")
        assert result["results"] == []
        assert result["total_results"] == 0

    @pytest.mark.asyncio
    async def test_propagates_error(self, mock_client):
        mock_client.call_tool.side_effect = RuntimeError("connection lost")
        with pytest.raises(RuntimeError, match="connection lost"):
            await search_microsoft_docs(mock_client, "fail")


class TestFetchDocumentation:
    @pytest.mark.asyncio
    async def test_returns_content(self, mock_client):
        mock_client.call_tool.return_value = {
            "content": "# Azure\nOverview of Azure services.",
        }
        result = await fetch_documentation(mock_client, "https://learn.microsoft.com/azure/")
        assert result["url"] == "https://learn.microsoft.com/azure/"
        assert "Azure" in result["content"]
        assert result["length"] == len(result["content"])

    @pytest.mark.asyncio
    async def test_empty_content(self, mock_client):
        mock_client.call_tool.return_value = {"content": ""}
        result = await fetch_documentation(mock_client, "https://example.com")
        assert result["content"] == ""
        assert result["length"] == 0


class TestSearchCodeSamples:
    @pytest.mark.asyncio
    async def test_returns_samples(self, mock_client):
        mock_client.call_tool.return_value = {
            "content": [
                {"description": "Upload blob", "codeSnippet": "from azure...", "language": "python", "link": "https://..."}
            ],
        }
        result = await search_code_samples(mock_client, "blob upload")
        assert len(result["samples"]) == 1
        assert result["query"] == "blob upload"
        assert result["language_filter"] is None

    @pytest.mark.asyncio
    async def test_with_language_filter(self, mock_client):
        mock_client.call_tool.return_value = {"content": [{"description": "sample"}]}
        result = await search_code_samples(mock_client, "test", language="python")
        assert result["language_filter"] == "python"
        # Verify the language argument was passed to the client
        call_args = mock_client.call_tool.call_args
        assert call_args[0][1]["language"] == "python"


class TestGetAzureGuidance:
    @pytest.mark.asyncio
    async def test_combines_docs_and_samples(self, mock_client):
        # First call: search_microsoft_docs, second: search_code_samples
        mock_client.call_tool.side_effect = [
            {"content": [{"title": "Doc 1"}]},
            {"content": [{"description": "Sample 1", "codeSnippet": "..."}]},
        ]
        result = await get_azure_guidance(mock_client, "Container Apps")
        assert result["topic"] == "Container Apps"
        assert len(result["documentation"]["results"]) == 1
        assert result["code_samples"] is not None
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_without_code_samples(self, mock_client):
        mock_client.call_tool.return_value = {"content": [{"title": "Doc 1"}]}
        result = await get_azure_guidance(mock_client, "VNet", include_code=False)
        assert result["code_samples"] is None

    @pytest.mark.asyncio
    async def test_code_sample_failure_graceful(self, mock_client):
        # Docs succeed, code samples fail
        mock_client.call_tool.side_effect = [
            {"content": [{"title": "Doc 1"}]},
            RuntimeError("timeout"),
        ]
        result = await get_azure_guidance(mock_client, "Functions")
        assert len(result["documentation"]["results"]) == 1
        assert "error" in result["code_samples"]

