"""
MCP tool for agent system.
Provides agents with access to MCP operations and external tool execution.
"""

from typing import Optional, Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
import asyncio

from ...services.mcp.learn_mcp_client import MicrosoftLearnMCPClient
from ...services.mcp.operations.learn_operations import (
    search_microsoft_docs,
    fetch_documentation,
    search_code_samples,
)


class DocsSearchInput(BaseModel):
    """Input schema for Microsoft Docs Search tool."""
    query: str = Field(description="Search query for Microsoft documentation")
    max_results: int = Field(default=5, description="Maximum number of results to return")


class DocsFetchInput(BaseModel):
    """Input schema for Microsoft Docs Fetch tool."""
    url: str = Field(description="URL of the Microsoft Learn documentation page to fetch")


class CodeSamplesInput(BaseModel):
    """Input schema for Microsoft Code Samples Search tool."""
    query: str = Field(description="Search query for code samples")
    language: Optional[str] = Field(default=None, description="Programming language filter (e.g., 'python', 'csharp', 'javascript')")
    max_results: int = Field(default=3, description="Maximum number of code samples to return")


class MicrosoftDocsSearchTool(BaseTool):
    """Tool for searching Microsoft documentation with semantic search."""
    
    name: str = "microsoft_docs_search"
    description: str = """Search Microsoft and Azure official documentation with semantic search.
    Use this to find relevant documentation pages, guides, and best practices.
    Returns up to max_results content chunks with title, content excerpt, and URL.
    Example queries: 'Azure Private Link for SQL', 'WAF Security checklist', 'Container Apps networking'"""
    args_schema: Type[BaseModel] = DocsSearchInput
    
    mcp_client: Optional[MicrosoftLearnMCPClient] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, query: str, max_results: int = 5) -> str:
        """Synchronous wrapper - not used for async agents."""
        raise NotImplementedError("Use async version (_arun)")
    
    async def _arun(self, query: str, max_results: int = 5) -> str:
        """Execute the search asynchronously."""
        if not self.mcp_client:
            return "Error: MCP client not initialized"
        
        try:
            result = await search_microsoft_docs(self.mcp_client, query, max_results)
            
            # Format results for agent consumption
            formatted_results = []
            for idx, doc in enumerate(result["results"], 1):
                formatted_results.append(
                    f"{idx}. **{doc.get('title', 'No title')}**\n"
                    f"   URL: {doc.get('contentUrl', 'N/A')}\n"
                    f"   {doc.get('content', 'No content')[:200]}...\n"
                )
            
            return (
                f"Found {result['total_results']} results for '{query}':\n\n" +
                "\n".join(formatted_results)
            )
        except Exception as e:
            return f"Error searching Microsoft docs: {str(e)}"


class MicrosoftDocsFetchTool(BaseTool):
    """Tool for fetching complete Microsoft documentation pages."""
    
    name: str = "microsoft_docs_fetch"
    description: str = """Fetch and convert a full Microsoft Learn documentation page to markdown.
    Use this when you need complete documentation content, tutorials, or detailed guides.
    Requires a valid Microsoft Learn URL (e.g., https://learn.microsoft.com/...).
    Returns the full page content in markdown format."""
    args_schema: Type[BaseModel] = DocsFetchInput
    
    mcp_client: Optional[MicrosoftLearnMCPClient] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, url: str) -> str:
        """Synchronous wrapper - not used for async agents."""
        raise NotImplementedError("Use async version (_arun)")
    
    async def _arun(self, url: str) -> str:
        """Execute the fetch asynchronously."""
        if not self.mcp_client:
            return "Error: MCP client not initialized"
        
        try:
            result = await fetch_documentation(self.mcp_client, url)
            
            return (
                f"**Documentation from:** {result['url']}\n"
                f"**Length:** {result['length']} characters\n\n"
                f"{result['content']}"
            )
        except Exception as e:
            return f"Error fetching documentation from {url}: {str(e)}"


class MicrosoftCodeSamplesTool(BaseTool):
    """Tool for searching official Microsoft/Azure code samples."""
    
    name: str = "microsoft_code_samples_search"
    description: str = """Search for official Microsoft and Azure code samples and snippets.
    Use this when you need practical implementation examples, SDK usage, or code patterns.
    Can filter by programming language (python, csharp, javascript, etc.).
    Returns code snippets with descriptions and links to full examples.
    Example queries: 'Azure Blob Storage upload', 'Cosmos DB query', 'Key Vault secrets'"""
    args_schema: Type[BaseModel] = CodeSamplesInput
    
    mcp_client: Optional[MicrosoftLearnMCPClient] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, query: str, language: Optional[str] = None, max_results: int = 3) -> str:
        """Synchronous wrapper - not used for async agents."""
        raise NotImplementedError("Use async version (_arun)")
    
    async def _arun(self, query: str, language: Optional[str] = None, max_results: int = 3) -> str:
        """Execute the search asynchronously."""
        if not self.mcp_client:
            return "Error: MCP client not initialized"
        
        try:
            result = await search_code_samples(self.mcp_client, query, language, max_results)
            
            # Format code samples for agent consumption
            formatted_samples = []
            for idx, sample in enumerate(result["samples"], 1):
                formatted_samples.append(
                    f"{idx}. **{sample.get('description', 'No description')}**\n"
                    f"   Language: {sample.get('language', 'N/A')}\n"
                    f"   Link: {sample.get('link', 'N/A')}\n"
                    f"   ```{sample.get('language', '')}\n"
                    f"   {sample.get('codeSnippet', 'No code snippet')}\n"
                    f"   ```\n"
                )
            
            lang_filter = f" (filtered by {language})" if language else ""
            return (
                f"Found {result['total_samples']} code samples for '{query}'{lang_filter}:\n\n" +
                "\n".join(formatted_samples)
            )
        except Exception as e:
            return f"Error searching code samples: {str(e)}"


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
