"""Tests for refactored Microsoft Learn operations."""

import pytest

from app.services.mcp.learn_mcp_client import MicrosoftLearnMCPClient
from app.services.mcp import operations


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
        result = await operations.search_microsoft_docs(
            mcp_client, "Azure Container Apps"
        )

        assert result is not None
        assert "results" in result
        assert "query" in result
        assert result["query"] == "Azure Container Apps"
        assert "total_results" in result
        assert isinstance(result["results"], list)

        # Verify result structure matches actual response
        if len(result["results"]) > 0:
            first_result = result["results"][0]
            assert "title" in first_result
            assert "content" in first_result
            assert "contentUrl" in first_result

    @pytest.mark.asyncio
    async def test_search_microsoft_docs_with_max_results(self, mcp_client):
        """Test searching with max results limit."""
        result = await operations.search_microsoft_docs(
            mcp_client, "Azure Functions", max_results=3
        )

        assert result is not None
        assert len(result["results"]) <= 3
        assert result["total_results"] <= 3

    @pytest.mark.asyncio
    async def test_fetch_documentation(self, mcp_client):
        """Test fetching a documentation page."""
        result = await operations.fetch_documentation(
            mcp_client, "https://learn.microsoft.com/azure/container-apps/overview"
        )

        assert result is not None
        assert "url" in result
        assert "content" in result
        assert "length" in result
        assert isinstance(result["content"], str)
        assert result["length"] > 0
        assert len(result["content"]) == result["length"]

    @pytest.mark.asyncio
    async def test_search_code_samples(self, mcp_client):
        """Test searching for code samples."""
        result = await operations.search_code_samples(
            mcp_client, "Azure Blob Storage upload"
        )

        assert result is not None
        assert "samples" in result
        assert "query" in result
        assert result["query"] == "Azure Blob Storage upload"
        assert isinstance(result["samples"], list)

        # Verify sample structure matches actual response
        if len(result["samples"]) > 0:
            first_sample = result["samples"][0]
            assert "description" in first_sample
            assert "codeSnippet" in first_sample
            assert "language" in first_sample
            assert "link" in first_sample

    @pytest.mark.asyncio
    async def test_search_code_samples_with_language(self, mcp_client):
        """Test searching code samples with language filter."""
        result = await operations.search_code_samples(
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
        result = await operations.get_azure_guidance(mcp_client, "Azure Container Apps")

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
        result = await operations.get_azure_guidance(
            mcp_client, "Azure Virtual Network", include_code=False
        )

        assert result is not None
        assert result["code_samples"] is None
        assert "documentation" in result
        assert len(result["documentation"]["results"]) > 0


@pytest.mark.integration
class TestOperationsComparison:
    """Compare old and new implementations to ensure compatibility."""

    @pytest.mark.asyncio
    async def test_search_docs_response_format(self, mcp_client):
        """Verify new implementation returns expected response format."""
        from app.services.mcp.operations.learn_operations import search_microsoft_docs

        query = "Azure SQL Database"

        result = await search_microsoft_docs(mcp_client, query, max_results=3)

        # Verify response structure
        assert "results" in result
        assert "query" in result
        assert "total_results" in result
        assert result["query"] == query
        assert isinstance(result["results"], list)
        assert len(result["results"]) <= 3
