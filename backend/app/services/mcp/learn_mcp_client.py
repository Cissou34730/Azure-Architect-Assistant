"""
Microsoft Learn MCP Client.

Provides access to Microsoft's official documentation via the Model Context Protocol.
Connects to https://learn.microsoft.com/api/mcp using Streamable HTTP (SSE) transport.

Available tools:
- microsoft_docs_search: Semantic search across Microsoft documentation
- microsoft_docs_fetch: Fetch full documentation page as markdown
- microsoft_code_sample_search: Search for official Microsoft code samples
"""

import asyncio
import json
import logging
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from .exceptions import (
    MCPCapabilityError,
    MCPConfigurationError,
    MCPConnectionError,
    MCPProtocolError,
    MCPTimeoutError,
    MCPUnexpectedResponseError,
)

logger = logging.getLogger(__name__)


class MicrosoftLearnMCPClient:
    """
    MCP client for Microsoft Learn documentation server.

    Connects to Microsoft's official MCP server to search and fetch
    documentation, code samples, and technical guidance.

    Example:
        ```python
        config = {
            "endpoint": "https://learn.microsoft.com/api/mcp",
            "timeout": 30
        }
        client = MicrosoftLearnMCPClient(config)
        await client.initialize()

        # Search documentation
        result = await client.call_tool(
            "microsoft_docs_search",
            {"query": "Azure Container Apps"}
        )

        await client.close()
        ```
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize Microsoft Learn MCP client.

        Args:
            config: Configuration dictionary with keys:
                - endpoint (str): MCP server URL
                - timeout (int, optional): Request timeout in seconds (default: 30)
                - auto_reconnect (bool, optional): Auto-reconnect on failure (default: True)
                - max_retries (int, optional): Max retry attempts (default: 3)

        Raises:
            MCPConfigurationError: If required config parameters are missing
        """
        self._validate_config(config)

        self.endpoint = config["endpoint"]
        self.timeout = config.get("timeout", 30)
        self.auto_reconnect = config.get("auto_reconnect", True)
        self.max_retries = config.get("max_retries", 3)

        self._session: ClientSession | None = None
        self._tools_cache: dict[str, dict] = {}
        self._initialized = False
        self._connection_context = None
        self._streams = None

        logger.info(
            f"Microsoft Learn MCP client configured: endpoint={self.endpoint}, timeout={self.timeout}s"
        )

    def _validate_config(self, config: dict[str, Any]) -> None:
        """Validate configuration parameters."""
        if not config:
            raise MCPConfigurationError("Config dictionary cannot be empty")

        if "endpoint" not in config:
            raise MCPConfigurationError("Missing required config parameter: 'endpoint'")

        endpoint = config["endpoint"]
        if not isinstance(endpoint, str) or not endpoint.startswith("http"):
            raise MCPConfigurationError(
                f"Invalid endpoint URL: {endpoint}. Must start with http:// or https://"
            )

    async def initialize(self) -> None:
        """
        Initialize connection to Microsoft Learn MCP server.

        Establishes session, discovers available tools, and caches tool schemas.

        Raises:
            MCPConnectionError: If connection fails
            MCPProtocolError: If server response is invalid
            MCPTimeoutError: If initialization times out
        """
        if self._initialized:
            logger.warning("Client already initialized, skipping")
            return

        try:
            logger.info(f"Initializing connection to {self.endpoint}...")

            # Establish connection with timeout
            self._connection_context = streamablehttp_client(self.endpoint)
            self._streams = await asyncio.wait_for(
                self._connection_context.__aenter__(), timeout=self.timeout
            )

            read_stream, write_stream, _ = self._streams

            # Create and initialize session
            self._session = ClientSession(read_stream, write_stream)
            await asyncio.wait_for(self._session.__aenter__(), timeout=self.timeout)
            await asyncio.wait_for(self._session.initialize(), timeout=self.timeout)

            # Discover and cache tools
            await self._refresh_tools()

            self._initialized = True
            logger.info(
                f"Successfully initialized Microsoft Learn MCP client. "
                f"Discovered {len(self._tools_cache)} tools."
            )

        except asyncio.TimeoutError as e:
            raise MCPTimeoutError(
                f"Connection to {self.endpoint} timed out after {self.timeout}s",
                details={"endpoint": self.endpoint, "timeout": self.timeout},
            ) from e
        except Exception as e:
            # Clean up partial connection
            await self._cleanup()
            raise MCPConnectionError(
                f"Failed to connect to Microsoft Learn MCP server: {str(e)}",
                details={"endpoint": self.endpoint, "error": str(e)},
            ) from e

    async def _refresh_tools(self) -> None:
        """
        Discover and cache available tools from MCP server.

        Raises:
            MCPProtocolError: If tool list response is invalid
        """
        if not self._session:
            raise MCPConnectionError("Session not initialized")

        try:
            logger.debug("Discovering available tools...")
            tools_response = await self._session.list_tools()

            if not hasattr(tools_response, "tools"):
                raise MCPProtocolError(
                    "Invalid tools response: missing 'tools' attribute",
                    details={"response": str(tools_response)},
                )

            # Cache tool schemas
            self._tools_cache.clear()
            for tool in tools_response.tools:
                tool_dict = {
                    "name": tool.name,
                    "description": tool.description if hasattr(tool, "description") else "",
                    "inputSchema": tool.inputSchema if hasattr(tool, "inputSchema") else {},
                }
                self._tools_cache[tool.name] = tool_dict

            logger.info(f"Cached {len(self._tools_cache)} tools: {list(self._tools_cache.keys())}")

        except Exception as e:
            raise MCPProtocolError(
                f"Failed to discover tools: {str(e)}", details={"error": str(e)}
            ) from e

    async def close(self) -> None:
        """
        Close connection to MCP server and cleanup resources.

        Safe to call multiple times.
        """
        if not self._initialized:
            return

        try:
            logger.debug("Closing Microsoft Learn MCP client...")
            await self._cleanup()
            logger.debug("Microsoft Learn MCP client closed")
        except (asyncio.CancelledError, RuntimeError) as e:
            # Swallow expected shutdown-time cancellation/runtime errors quietly
            logger.debug(f"MCP client close suppressed during shutdown: {type(e).__name__}")
        except Exception as e:
            # Avoid noisy logs on shutdown for benign errors
            logger.debug(f"MCP client close encountered non-fatal error: {e}")
        finally:
            self._initialized = False

    async def _cleanup(self) -> None:
        """
        Internal cleanup of connection resources.
        
        IMPORTANT: During app shutdown, asyncio tasks are cancelled and the event loop
        is being torn down. Calling __aexit__ on context managers (session, transport)
        can trigger anyio's "Attempted to exit cancel scope in a different task" RuntimeError
        because the context was entered in a different task/context than it's being exited in.
        
        Solution: Drop all references and let Python's garbage collection and process exit
        handle resource cleanup. This is safe because:
        1. HTTP connections will be closed when the process exits
        2. anyio background tasks will be cancelled by asyncio shutdown
        3. File descriptors and sockets will be released by the OS
        """
        try:
            # Drop all references without calling __aexit__ to avoid anyio cancel scope errors
            if self._session:
                logger.debug("Dropping session reference during cleanup")
                self._session = None
            
            if self._connection_context:
                logger.debug("Dropping connection context reference during cleanup")
                self._connection_context = None
            
            if self._streams:
                logger.debug("Dropping streams reference during cleanup")
                self._streams = None

        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

    def list_tools(self) -> list[dict]:
        """
        Get list of available tools.

        Returns:
            List of tool dictionaries with name, description, and schema

        Raises:
            MCPConnectionError: If client not initialized
        """
        if not self._initialized:
            raise MCPConnectionError("Client not initialized. Call initialize() first.")

        return list(self._tools_cache.values())

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any], timeout: int | None = None
    ) -> dict[str, Any]:
        """
        Execute a tool call on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments as dictionary
            timeout: Optional timeout override (defaults to client timeout)

        Returns:
            Normalized response dictionary

        Raises:
            MCPConnectionError: If client not initialized
            MCPCapabilityError: If tool not found
            MCPTimeoutError: If call exceeds timeout
            MCPUnexpectedResponseError: If response format is invalid
        """
        if not self._initialized or not self._session:
            raise MCPConnectionError("Client not initialized. Call initialize() first.")

        # Validate tool exists
        self._validate_tool_call(tool_name, arguments)

        call_timeout = timeout or self.timeout

        try:
            logger.debug(f"Calling tool '{tool_name}' with args: {arguments}")

            # Execute tool call
            result = await asyncio.wait_for(
                self._session.call_tool(tool_name, arguments=arguments), timeout=call_timeout
            )

            # Normalize response
            normalized = self._normalize_response(result, tool_name)

            logger.debug(f"Tool '{tool_name}' completed successfully")
            return normalized

        except asyncio.TimeoutError as e:
            raise MCPTimeoutError(
                f"Tool call '{tool_name}' timed out after {call_timeout}s",
                details={"tool": tool_name, "timeout": call_timeout, "arguments": arguments},
            ) from e
        except Exception as e:
            logger.error(f"Tool call '{tool_name}' failed: {e}")
            raise MCPUnexpectedResponseError(
                f"Tool call failed: {str(e)}",
                details={"tool": tool_name, "arguments": arguments, "error": str(e)},
            ) from e

    def _validate_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """
        Validate that tool exists and arguments are provided.

        Args:
            tool_name: Tool to validate
            arguments: Arguments to validate

        Raises:
            MCPCapabilityError: If tool not found
        """
        if tool_name not in self._tools_cache:
            available_tools = list(self._tools_cache.keys())
            raise MCPCapabilityError(
                f"Tool '{tool_name}' not found. Available tools: {available_tools}",
                details={"tool": tool_name, "available_tools": available_tools},
            )

        if not isinstance(arguments, dict):
            raise MCPProtocolError(
                f"Tool arguments must be a dictionary, got {type(arguments).__name__}",
                details={"tool": tool_name, "arguments_type": type(arguments).__name__},
            )

    def _normalize_response(self, result: Any, tool_name: str) -> dict[str, Any]:
        """
        Normalize MCP tool response to standard dictionary format.

        Args:
            result: Raw CallToolResult from MCP
            tool_name: Name of the tool that was called

        Returns:
            Normalized dictionary response

        Raises:
            MCPUnexpectedResponseError: If response format is invalid
        """
        try:
            # Extract content from result
            if not hasattr(result, "content"):
                raise MCPUnexpectedResponseError(
                    "Response missing 'content' attribute",
                    details={"tool": tool_name, "response": str(result)},
                )

            content_blocks = result.content

            # Parse content blocks
            if not content_blocks:
                return {"tool": tool_name, "content": None, "error": None}

            # Handle text content
            parsed_content = []
            for block in content_blocks:
                if hasattr(block, "type") and block.type == "text":
                    text = block.text
                    # Try to parse as JSON if it looks like JSON
                    if text.strip().startswith(("{", "[")):
                        try:
                            parsed_content.append(json.loads(text))
                        except json.JSONDecodeError:
                            parsed_content.append(text)
                    else:
                        parsed_content.append(text)
                else:
                    parsed_content.append(str(block))

            # Return single item if only one content block
            final_content = parsed_content[0] if len(parsed_content) == 1 else parsed_content

            response = {
                "tool": tool_name,
                "content": final_content,
                "error": None,
                "isError": hasattr(result, "isError") and result.isError,
            }

            return response

        except Exception as e:
            raise MCPUnexpectedResponseError(
                f"Failed to normalize response: {str(e)}",
                details={"tool": tool_name, "error": str(e), "result": str(result)},
            ) from e

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
