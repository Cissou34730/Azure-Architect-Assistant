"""
Domain-level operations for Microsoft Learn MCP client.

Provides high-level, business-oriented functions for interacting with
Microsoft Learn documentation, built on top of the low-level MCP client.
"""

import logging
from typing import Any

from ..learn_mcp_client import MicrosoftLearnMCPClient

logger = logging.getLogger(__name__)


async def search_microsoft_docs(
    client: MicrosoftLearnMCPClient, query: str, max_results: int = 5
) -> dict[str, Any]:
    """
    Search Microsoft documentation with semantic search.

    Args:
        client: Initialized MicrosoftLearnMCPClient instance
        query: Search query string
        max_results: Maximum number of results to return (default: 5)

    Returns:
        Dictionary with:
            - results: List of search results with title, url, excerpt
            - query: Original query
            - total_results: Number of results found

    Example:
        ```python
        results = await search_microsoft_docs(
            client,
            "Azure Container Apps networking"
        )
        for result in results["results"]:
            print(f"{result['title']}: {result['url']}")
        ```
    """
    logger.info(f"Searching Microsoft docs for: {query}")

    try:
        response = await client.call_tool("microsoft_docs_search", {"query": query})

        # Parse and normalize response
        content = response.get("content", {})

        if isinstance(content, dict):
            results = content.get("results", [])[:max_results]
        elif isinstance(content, list):
            results = content[:max_results]
        else:
            results = []

        normalized = {
            "results": results,
            "query": query,
            "total_results": len(results),
        }

        logger.info(f"Found {len(results)} results for query: {query}")
        return normalized

    except Exception as e:
        logger.error(f"Failed to search Microsoft docs: {e}")
        raise


async def fetch_documentation(client: MicrosoftLearnMCPClient, url: str) -> dict[str, Any]:
    """
    Fetch and convert a Microsoft documentation page to markdown.

    Args:
        client: Initialized MicrosoftLearnMCPClient instance
        url: URL of the Microsoft Learn documentation page

    Returns:
        Dictionary with:
            - url: Original URL
            - title: Document title
            - content: Full content in markdown format
            - sections: List of section headings
            - last_updated: Last update timestamp (if available)

    Example:
        ```python
        doc = await fetch_documentation(
            client,
            "https://learn.microsoft.com/azure/container-apps/"
        )
        print(doc["content"])
        ```
    """
    logger.info(f"Fetching documentation from: {url}")

    try:
        response = await client.call_tool("microsoft_docs_fetch", {"url": url})

        content = response.get("content", {})

        if isinstance(content, str):
            # Content is raw markdown
            normalized = {
                "url": url,
                "title": None,
                "content": content,
                "sections": [],
                "last_updated": None,
            }
        elif isinstance(content, dict):
            # Content is structured
            normalized = {
                "url": url,
                "title": content.get("title"),
                "content": content.get("content", content.get("text", "")),
                "sections": content.get("sections", []),
                "last_updated": content.get("last_updated"),
            }
        else:
            normalized = {
                "url": url,
                "title": None,
                "content": str(content),
                "sections": [],
                "last_updated": None,
            }

        logger.info(f"Successfully fetched documentation from: {url}")
        return normalized

    except Exception as e:
        logger.error(f"Failed to fetch documentation: {e}")
        raise


async def search_code_samples(
    client: MicrosoftLearnMCPClient,
    query: str,
    language: str | None = None,
    max_results: int = 3,
) -> dict[str, Any]:
    """
    Search for official Microsoft/Azure code snippets and examples.

    Args:
        client: Initialized MicrosoftLearnMCPClient instance
        query: Search query for code samples
        language: Optional programming language filter (e.g., "python", "csharp", "javascript")
        max_results: Maximum number of samples to return (default: 3)

    Returns:
        Dictionary with:
            - samples: List of code samples with title, language, code, description, source_url
            - query: Original query
            - language_filter: Applied language filter (if any)

    Example:
        ```python
        samples = await search_code_samples(
            client,
            "Azure OpenAI chat completion",
            language="python"
        )
        for sample in samples["samples"]:
            print(f"{sample['title']} ({sample['language']})")
            print(sample['code'])
        ```
    """
    logger.info(f"Searching code samples for: {query} (language: {language})")

    try:
        arguments = {"query": query}
        if language:
            arguments["language"] = language

        response = await client.call_tool("microsoft_code_sample_search", arguments)

        content = response.get("content", {})

        if isinstance(content, dict):
            samples = content.get("samples", [])[:max_results]
        elif isinstance(content, list):
            samples = content[:max_results]
        else:
            samples = []

        normalized = {
            "samples": samples,
            "query": query,
            "language_filter": language,
            "total_samples": len(samples),
        }

        logger.info(f"Found {len(samples)} code samples for query: {query}")
        return normalized

    except Exception as e:
        logger.error(f"Failed to search code samples: {e}")
        raise


async def get_azure_guidance(
    client: MicrosoftLearnMCPClient, topic: str, include_code: bool = True
) -> dict[str, Any]:
    """
    Get comprehensive Azure guidance on a topic.

    Combines documentation search with code samples for a complete view.

    Args:
        client: Initialized MicrosoftLearnMCPClient instance
        topic: Azure topic to get guidance on
        include_code: Whether to include code samples (default: True)

    Returns:
        Dictionary with:
            - topic: Original topic
            - documentation: Search results from docs
            - code_samples: Code samples (if include_code=True)
            - summary: Brief summary of findings

    Example:
        ```python
        guidance = await get_azure_guidance(
            client,
            "Azure SQL Private Endpoint"
        )
        print(f"Found {len(guidance['documentation']['results'])} docs")
        print(f"Found {len(guidance['code_samples']['samples'])} code samples")
        ```
    """
    logger.info(f"Getting Azure guidance for topic: {topic}")

    try:
        # Search documentation
        docs = await search_microsoft_docs(client, topic, max_results=5)

        result = {"topic": topic, "documentation": docs, "code_samples": None, "summary": ""}

        # Optionally search code samples
        if include_code:
            try:
                samples = await search_code_samples(client, topic, max_results=3)
                result["code_samples"] = samples
            except Exception as e:
                logger.warning(f"Failed to fetch code samples: {e}")
                result["code_samples"] = {"samples": [], "error": str(e)}

        # Generate summary
        doc_count = len(docs.get("results", []))
        sample_count = (
            len(result["code_samples"].get("samples", []))
            if result["code_samples"] and not result["code_samples"].get("error")
            else 0
        )

        result["summary"] = (
            f"Found {doc_count} documentation pages and {sample_count} code samples for '{topic}'"
        )

        logger.info(f"Successfully retrieved Azure guidance for: {topic}")
        return result

    except Exception as e:
        logger.error(f"Failed to get Azure guidance: {e}")
        raise
