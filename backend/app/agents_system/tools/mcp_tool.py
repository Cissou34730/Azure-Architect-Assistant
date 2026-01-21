"""
MCP tool for agent system.
Provides agents with access to MCP operations and external tool execution.
"""

import json
from typing import Any

from langchain.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from ...services.mcp.exceptions import MCPError
from ...services.mcp.learn_mcp_client import MicrosoftLearnMCPClient
from ...services.mcp.operations.learn_operations import (
    fetch_documentation,
    search_code_samples,
    search_microsoft_docs,
)


def _append_mcp_log(*, tool: str, query: str | None = None, url: str | None = None, urls: list[str] | None = None) -> str:
    payload = {
        "tool": tool,
        "query": query,
        "url": url,
        "urls": urls or [],
    }
    return "\n\nAAA_MCP_LOG\n```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"


class DocsSearchInput(BaseModel):
    """Single-input schema for Microsoft Docs Search tool.

    Accepts either a string (query) or a dict with keys 'query' and optional 'max_results'.
    """

    payload: str | dict[str, Any] | Any = Field(description="Query string or dict payload")


class DocsFetchInput(BaseModel):
    """Single-input schema for Microsoft Docs Fetch tool.

    Accepts either a string (url) or a dict with key 'url'.
    """

    payload: str | dict[str, Any] | Any = Field(description="URL string or dict payload")


class CodeSamplesInput(BaseModel):
    """Single-input schema for Microsoft Code Samples Search tool.

    Accepts either a string (query) or a dict with keys 'query', 'language', 'max_results'.
    """

    payload: str | dict[str, Any] | Any = Field(description="Query string or dict payload")


class MicrosoftDocsSearchTool(BaseTool):
    """Tool for searching Microsoft documentation with semantic search."""

    name: str = "microsoft_docs_search"
    description: str = """Search Microsoft and Azure official documentation with semantic search.
    Use this to find relevant documentation pages, guides, and best practices.
    Returns up to max_results content chunks with title, content excerpt, and URL.
    Example queries: 'Azure Private Link for SQL', 'WAF Security checklist', 'Container Apps networking'"""
    args_schema: type[BaseModel] = DocsSearchInput

    # Use ClassVar if they are not to be validated by pydantic;
    # but here mcp_client is likely meant to be an instance attribute
    mcp_client: MicrosoftLearnMCPClient | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, query: str, max_results: int = 5) -> str:
        """Synchronous wrapper - not used for async agents."""
        raise NotImplementedError("Use async version (_arun)")

    async def _arun(self, query: str | dict[str, Any] | Any) -> str:
        """Execute the search asynchronously."""
        if not self.mcp_client:
            return "Error: MCP client not initialized"
        try:
            # Normalize input
            if isinstance(query, str):
                q = query
                max_results_val = 5
            elif isinstance(query, dict):
                q = query.get("query", "")
                max_results_val = query.get("max_results", 5)
            else:
                # support pydantic/other payloads
                q = getattr(query, "query", str(query))
                max_results_val = getattr(query, "max_results", 5)

            result = await search_microsoft_docs(self.mcp_client, q, max_results_val)

            # Format results for agent consumption
            formatted_results = []
            urls: list[str] = []
            for idx, doc in enumerate(result["results"], 1):
                url = doc.get("contentUrl", "N/A")
                if isinstance(url, str) and url.startswith("http"):
                    urls.append(url)
                formatted_results.append(
                    f"{idx}. **{doc.get('title', 'No title')}**\n"
                    f"   URL: {url}\n"
                    f"   {doc.get('content', 'No content')[:200]}...\n"
                )

            return (
                f"Found {result['total_results']} results for '{q}':\n\n"
                + "\n".join(formatted_results)
                + _append_mcp_log(tool=self.name, query=q, urls=urls)
            )
        except (MCPError, RuntimeError, ValueError) as e:
            return f"Error searching Microsoft docs: {e!s}" + _append_mcp_log(
                tool=self.name,
                query=str(query),
                urls=[],
            )


class MicrosoftDocsFetchTool(BaseTool):
    """Tool for fetching complete Microsoft documentation pages."""

    name: str = "microsoft_docs_fetch"
    description: str = """Fetch and convert a full Microsoft Learn documentation page to markdown.
    Use this when you need complete documentation content, tutorials, or detailed guides.
    Requires a valid Microsoft Learn URL (e.g., https://learn.microsoft.com/...).
    Returns the full page content in markdown format."""
    args_schema: type[BaseModel] = DocsFetchInput

    mcp_client: MicrosoftLearnMCPClient | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, url: str) -> str:
        """Synchronous wrapper - not used for async agents."""
        raise NotImplementedError("Use async version (_arun)")

    async def _arun(self, url: str | dict[str, Any] | Any) -> str:
        """Execute the fetch asynchronously."""
        if not self.mcp_client:
            return "Error: MCP client not initialized"
        try:
            if isinstance(url, str):
                u = url
            elif isinstance(url, dict):
                u = url.get("url", "")
            else:
                u = getattr(url, "url", str(url))

            result = await fetch_documentation(self.mcp_client, u)

            return (
                f"**Documentation from:** {result['url']}\n"
                f"**Length:** {result['length']} characters\n\n"
                f"{result['content']}"
                + _append_mcp_log(tool=self.name, url=u, urls=[u])
            )
        except (MCPError, RuntimeError, ValueError) as e:
            return f"Error fetching documentation from {url}: {e!s}" + _append_mcp_log(
                tool=self.name,
                url=str(url),
                urls=[str(url)],
            )


class MicrosoftCodeSamplesTool(BaseTool):
    """Tool for searching official Microsoft/Azure code samples."""

    name: str = "microsoft_code_samples_search"
    description: str = """Search for official Microsoft and Azure code samples and snippets.
    Use this when you need practical implementation examples, SDK usage, or code patterns.
    Can filter by programming language (python, csharp, javascript, etc.).
    Returns code snippets with descriptions and links to full examples.
    Example queries: 'Azure Blob Storage upload', 'Cosmos DB query', 'Key Vault secrets'"""
    args_schema: type[BaseModel] = CodeSamplesInput

    mcp_client: MicrosoftLearnMCPClient | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(
        self, query: str, language: str | None = None, max_results: int = 3
    ) -> str:
        """Synchronous wrapper - not used for async agents."""
        raise NotImplementedError("Use async version (_arun)")

    async def _arun(self, query: str | dict[str, Any] | Any) -> str:
        """Execute the search asynchronously."""
        if not self.mcp_client:
            return "Error: MCP client not initialized"
        try:
            q = ""
            language_val = None
            max_results_val = 3
            if isinstance(query, str):
                q = query
            elif isinstance(query, dict):
                q = query.get("query", "")
                language_val = query.get("language")
                max_results_val = query.get("max_results", 3)
            else:
                q = getattr(query, "query", str(query))
                language_val = getattr(query, "language", None)
                max_results_val = getattr(query, "max_results", 3)

            result = await search_code_samples(
                self.mcp_client, q, language_val, max_results_val
            )

            # Format code samples for agent consumption
            formatted_samples = []
            urls: list[str] = []
            for idx, sample in enumerate(result["samples"], 1):
                link = sample.get("link", "N/A")
                if isinstance(link, str) and link.startswith("http"):
                    urls.append(link)
                formatted_samples.append(
                    f"{idx}. **{sample.get('description', 'No description')}**\n"
                    f"   Language: {sample.get('language', 'N/A')}\n"
                    f"   Link: {link}\n"
                    f"   ```{sample.get('language', '')}\n"
                    f"   {sample.get('codeSnippet', 'No code snippet')}\n"
                    f"   ```\n"
                )

            lang_filter = f" (filtered by {language_val})" if language_val else ""
            return (
                f"Found {result['total_samples']} code samples for '{q}'{lang_filter}:\n\n"
                + "\n".join(formatted_samples)
                + _append_mcp_log(tool=self.name, query=q, urls=urls)
            )
        except (MCPError, RuntimeError, ValueError) as e:
            return f"Error searching code samples: {e!s}" + _append_mcp_log(
                tool=self.name,
                query=str(query),
                urls=[],
            )


async def create_mcp_tools(mcp_client: MicrosoftLearnMCPClient) -> list[BaseTool]:
    """
    Create and initialize all MCP tools with the provided client.

    Args:
        mcp_client: Initialized MicrosoftLearnMCPClient instance

    Returns:
        List of LangChain BaseTool instances ready for use with agents
    """
    tools = [
        MicrosoftDocsSearchTool(mcp_client=mcp_client),
        MicrosoftDocsFetchTool(mcp_client=mcp_client),
        MicrosoftCodeSamplesTool(mcp_client=mcp_client),
    ]

    return tools

