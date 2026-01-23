"""
Refactored domain-level operations for Microsoft Learn MCP client.

Based on actual response contract from Microsoft Learn MCP server.
Eliminates unnecessary type checking and response normalization.
"""

import logging
from typing import Any

from ..learn_mcp_client import MicrosoftLearnMCPClient

logger = logging.getLogger(__name__)


async def _call_mcp_tool(
    client: MicrosoftLearnMCPClient,
    tool_name: str,
    arguments: dict[str, Any],
    operation_name: str,
) -> dict[str, Any]:
    """
    Base wrapper for MCP tool calls with logging and error handling.

    Args:
        client: Initialized MCP client
        tool_name: Name of the MCP tool to call
        arguments: Tool arguments
        operation_name: Human-readable operation name for logging

    Returns:
        Response from MCP server

    Raises:
        Exception: Re-raises any exception from the MCP call
    """
    logger.info(f"{operation_name}: {arguments}")

    try:
        response = await client.call_tool(tool_name, arguments)
        logger.debug(f"{operation_name} completed successfully")
        return response

    except Exception as e:
        logger.error(f"{operation_name} failed: {e}")
        raise


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
            - results: List of search results with title, content, contentUrl
            - query: Original query
            - total_results: Number of results returned

    Example:
        ```python
        results = await search_microsoft_docs(
            client,
            "Azure Container Apps networking"
        )
        for result in results["results"]:
            print(f"{result['title']}: {result['contentUrl']}")
        ```
    """
    response = await _call_mcp_tool(
        client,
        "microsoft_docs_search",
        {"query": query},
        f"Searching Microsoft docs for '{query}'",
    )

    meta = response.get("meta") if isinstance(response, dict) else None

    # Normalize content to a list of result dicts
    content = response.get("content")
    if isinstance(content, list):
        items = content
    elif isinstance(content, dict):
        # Some servers return { results: [...] }
        items = (
            content.get("results")
            if isinstance(content.get("results"), list)
            else [content]
        )
    else:
        items = []

    results = items[:max_results]

    return {
        "results": results,
        "query": query,
        "total_results": len(results),
        "meta": meta or {},
    }


async def fetch_documentation(
    client: MicrosoftLearnMCPClient, url: str
) -> dict[str, Any]:
    """
    Fetch and convert a Microsoft documentation page to markdown.

    Args:
        client: Initialized MicrosoftLearnMCPClient instance
        url: URL of the Microsoft Learn documentation page

    Returns:
        Dictionary with:
            - url: Original URL
            - content: Full content in markdown format
            - length: Content length in characters

    Example:
        ```python
        doc = await fetch_documentation(
            client,
            "https://learn.microsoft.com/azure/container-apps/"
        )
        print(doc["content"])
        ```
    """
    response = await _call_mcp_tool(
        client,
        "microsoft_docs_fetch",
        {"url": url},
        f"Fetching documentation from '{url}'",
    )

    meta = response.get("meta") if isinstance(response, dict) else None

    # Content is a markdown string
    content = response.get("content", "")

    return {
        "url": url,
        "content": content,
        "length": len(content),
        "meta": meta or {},
    }


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
            - samples: List of code samples with description, codeSnippet, language, link
            - query: Original query
            - language_filter: Applied language filter (if any)
            - total_samples: Number of samples returned

    Example:
        ```python
        samples = await search_code_samples(
            client,
            "Azure Blob Storage upload",
            language="python"
        )
        for sample in samples["samples"]:
            print(f"{sample['language']}: {sample['link']}")
            print(sample['codeSnippet'])
        ```
    """
    arguments = {"query": query}
    if language:
        arguments["language"] = language

    response = await _call_mcp_tool(
        client,
        "microsoft_code_sample_search",
        arguments,
        f"Searching code samples for '{query}' (language: {language})",
    )

    meta = response.get("meta") if isinstance(response, dict) else None

    # Normalize content to a list of sample dicts
    content = response.get("content")
    if isinstance(content, list):
        items = content
    elif isinstance(content, dict):
        # Some servers return { samples: [...] } or { results: [...] }
        items = (
            content.get("samples")
            if isinstance(content.get("samples"), list)
            else content.get("results")
            if isinstance(content.get("results"), list)
            else [content]
        )
    else:
        items = []

    samples = items[:max_results]

    return {
        "samples": samples,
        "query": query,
        "language_filter": language,
        "total_samples": len(samples),
        "meta": meta or {},
    }


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

    # Search documentation
    docs = await search_microsoft_docs(client, topic, max_results=5)

    result = {
        "topic": topic,
        "documentation": docs,
        "code_samples": None,
        "summary": "",
    }

    # Optionally search code samples
    if include_code:
        try:
            samples = await search_code_samples(client, topic, max_results=3)
            result["code_samples"] = samples
        except Exception as e:  # noqa: BLE001
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

