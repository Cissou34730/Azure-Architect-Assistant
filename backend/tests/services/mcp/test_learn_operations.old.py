"""Tests for Microsoft Learn operations."""

import pytest

from app.services.mcp.learn_mcp_client import MicrosoftLearnMCPClient
from app.services.mcp.operations import (
    fetch_documentation,
    get_azure_guidance,
    search_code_samples,
    search_microsoft_docs,
)


@pytest.fixture
async def mcp_client():
    """Fixture providing initialized MCP client."""
    config = {"endpoint": "https://learn.microsoft.com/api/mcp", "timeout": 30}
    client = MicrosoftLearnMCPClient(config)
    await client.initialize()
    yield client
    await client.close()


@pytest.mark.integration
class TestLearnOperations:
    """Integration tests for Microsoft Learn operations."""

    @pytest.mark.asyncio
    async def test_search_microsoft_docs(self, mcp_client):
        """Test searching Microsoft documentation."""
        result = await search_microsoft_docs(mcp_client, "Azure SQL Database")

        assert result is not None
        assert "results" in result
        assert "query" in result
        assert result["query"] == "Azure SQL Database"
        assert "total_results" in result
        assert isinstance(result["results"], list)

    @pytest.mark.asyncio
    async def test_search_microsoft_docs_with_max_results(self, mcp_client):
        """Test searching with max results limit."""
        result = await search_microsoft_docs(mcp_client, "Azure Functions", max_results=3)

        assert result is not None
        assert len(result["results"]) <= 3

    @pytest.mark.asyncio
    async def test_fetch_documentation(self, mcp_client):
        """Test fetching a documentation page."""
        result = await fetch_documentation(
            mcp_client, "https://learn.microsoft.com/azure/app-service/overview"
        )

        assert result is not None
        assert "url" in result
        assert "content" in result
        assert result["content"] is not None
        assert len(result["content"]) > 0

    @pytest.mark.asyncio
    async def test_search_code_samples(self, mcp_client):
        """Test searching for code samples."""
        result = await search_code_samples(mcp_client, "Azure Blob Storage upload")

        assert result is not None
        assert "samples" in result
        assert "query" in result
        assert result["query"] == "Azure Blob Storage upload"
        assert isinstance(result["samples"], list)

    @pytest.mark.asyncio
    async def test_search_code_samples_with_language(self, mcp_client):
        """Test searching code samples with language filter."""
        result = await search_code_samples(
            mcp_client, "Azure OpenAI completion", language="python", max_results=2
        )

        assert result is not None
        assert "samples" in result
        assert "language_filter" in result
        assert result["language_filter"] == "python"
        assert len(result["samples"]) <= 2

    @pytest.mark.asyncio
    async def test_get_azure_guidance(self, mcp_client):
        """Test getting comprehensive Azure guidance."""
        result = await get_azure_guidance(mcp_client, "Azure Container Apps")

        assert result is not None
        assert "topic" in result
        assert result["topic"] == "Azure Container Apps"
        assert "documentation" in result
        assert "code_samples" in result
        assert "summary" in result

        # Verify documentation section
        assert "results" in result["documentation"]
        assert len(result["documentation"]["results"]) > 0

        # Verify code samples section
        if result["code_samples"] and not result["code_samples"].get("error"):
            assert "samples" in result["code_samples"]

    @pytest.mark.asyncio
    async def test_get_azure_guidance_without_code(self, mcp_client):
        """Test getting Azure guidance without code samples."""
        result = await get_azure_guidance(mcp_client, "Azure Virtual Network", include_code=False)

        assert result is not None
        assert result["code_samples"] is None
        assert "documentation" in result
        assert len(result["documentation"]["results"]) > 0


@pytest.mark.unit
class TestOperationsResponseNormalization:
    """Unit tests for response normalization in operations."""

    @pytest.mark.asyncio
    async def test_search_docs_empty_result(self, mcp_client):
        """Test handling of empty search results."""
        # Search for something very specific that might return no results
        result = await search_microsoft_docs(mcp_client, "xyzabc123nonexistent")

        assert result is not None
        assert "results" in result
        assert isinstance(result["results"], list)
        # Even if no results, structure should be valid
        assert "query" in result
        assert "total_results" in result
