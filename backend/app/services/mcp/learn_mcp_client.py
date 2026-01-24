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
import contextlib
import json
import logging
import random
import time
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from .exceptions import (
    MCPCapabilityError,
    MCPConfigurationError,
    MCPConnectionError,
    MCPError,
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
        self._tools_cache: dict[str, dict[str, Any]] = {}
        self._initialized = False
        self._connection_context: Any = None
        self._streams: Any = None

        # Background task that owns the async context managers.
        # AnyIO requires that a cancel scope is exited in the same task
        # where it was entered; FastAPI startup/shutdown run in different
        # tasks, so we keep enter/exit within a single dedicated task.
        self._runner_task: asyncio.Task[None] | None = None
        self._ready_event: asyncio.Event | None = None
        self._stop_event: asyncio.Event | None = None
        self._startup_error: BaseException | None = None
        self._call_lock = asyncio.Lock()

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

    async def _wait_for_existing_initialization(self) -> None:
        """Wait for an in-flight initialization to complete."""
        if self._ready_event:
            await asyncio.wait_for(self._ready_event.wait(), timeout=self.timeout)
        if self._startup_error:
            raise MCPConnectionError(
                f"Failed to connect to Microsoft Learn MCP server: {self._startup_error}",
                details={"endpoint": self.endpoint, "error": str(self._startup_error)},
            ) from self._startup_error

    def _check_startup_error(self) -> None:
        """Verify if any error occurred during background startup."""
        if self._startup_error:
            raise MCPConnectionError(
                f"Failed to connect to Microsoft Learn MCP server: {self._startup_error}",
                details={"endpoint": self.endpoint, "error": str(self._startup_error)},
            ) from self._startup_error

        if not self._initialized:
            raise MCPConnectionError(
                "Failed to initialize Microsoft Learn MCP client",
                details={"endpoint": self.endpoint},
            )

    async def initialize(self) -> None:
        """Initialize connection to Microsoft Learn MCP server."""
        if self._initialized:
            logger.warning("Client already initialized, skipping")
            return

        if self._runner_task and not self._runner_task.done():
            await self._wait_for_existing_initialization()
            if self._initialized:
                return

        try:
            logger.info("Initializing connection to %s...", self.endpoint)
            self._startup_error = None
            self._ready_event = asyncio.Event()
            self._stop_event = asyncio.Event()
            self._runner_task = asyncio.create_task(
                self._run_connection_owner(), name="mcp-microsoft-learn-client"
            )

            await asyncio.wait_for(self._ready_event.wait(), timeout=self.timeout)
            self._check_startup_error()

        except asyncio.TimeoutError as e:
            if self._runner_task and not self._runner_task.done():
                self._runner_task.cancel()
                with contextlib.suppress(Exception):
                    await self._runner_task
            raise MCPTimeoutError(
                f"Connection to {self.endpoint} timed out after {self.timeout}s",
                details={"endpoint": self.endpoint, "timeout": self.timeout},
            ) from e
        except Exception as e:
            await self.close()
            raise MCPConnectionError(
                f"Failed to connect to Microsoft Learn MCP server: {e!s}",
                details={"endpoint": self.endpoint, "error": str(e)},
            ) from e


    async def _run_connection_owner(self) -> None:
        """Owns MCP connection/session context managers for the app lifetime."""
        session = None
        connection_context = None
        streams = None
        
        try:
            # Establish connection with timeout
            connection_context = streamablehttp_client(self.endpoint)
            streams = await asyncio.wait_for(
                connection_context.__aenter__(), timeout=self.timeout
            )

            read_stream, write_stream, _ = streams

            # Create and initialize session
            session = ClientSession(read_stream, write_stream)
            await asyncio.wait_for(session.__aenter__(), timeout=self.timeout)
            await asyncio.wait_for(session.initialize(), timeout=self.timeout)

            # Store references for use by other methods
            self._session = session
            self._connection_context = connection_context
            self._streams = streams

            # Discover and cache tools
            await self._refresh_tools()

            self._initialized = True
            logger.info(
                f"Successfully initialized Microsoft Learn MCP client. "
                f"Discovered {len(self._tools_cache)} tools."
            )

        except BaseException as exc:  # noqa: BLE001
            self._startup_error = exc
            logger.error(f"MCP client initialization failed: {exc}")
        finally:
            if self._ready_event:
                self._ready_event.set()

        # Wait until shutdown requests stop.
        if self._stop_event:
            with contextlib.suppress(Exception):
                await self._stop_event.wait()

        # Cleanup in the same task that entered context managers.
        # This ensures __aexit__ is called in the same task as __aenter__
        try:
            if session:
                logger.debug("Exiting MCP session in owner task")
                await asyncio.wait_for(
                    session.__aexit__(None, None, None), timeout=5.0
                )
        except Exception as e:
            logger.warning(f"Error exiting session: {e}")
        
        try:
            if connection_context and streams:
                logger.debug("Exiting MCP connection context in owner task")
                await asyncio.wait_for(
                    connection_context.__aexit__(None, None, None), timeout=5.0
                )
        except Exception as e:
            logger.warning(f"Error exiting connection context: {e}")
        
        # Clear references
        self._session = None
        self._connection_context = None
        self._streams = None
        self._initialized = False

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
                    "description": tool.description
                    if hasattr(tool, "description")
                    else "",
                    "inputSchema": tool.inputSchema
                    if hasattr(tool, "inputSchema")
                    else {},
                }
                self._tools_cache[tool.name] = tool_dict

            logger.info(
                f"Cached {len(self._tools_cache)} tools: {list(self._tools_cache.keys())}"
            )

        except Exception as e:
            raise MCPProtocolError(
                f"Failed to discover tools: {e!s}", details={"error": str(e)}
            ) from e

    async def close(self) -> None:
        """
        Close connection to MCP server and cleanup resources.

        Safe to call multiple times.
        """
        try:
            logger.debug("Closing Microsoft Learn MCP client...")
            if self._stop_event:
                self._stop_event.set()

            if self._runner_task and not self._runner_task.done():
                try:
                    await asyncio.wait_for(self._runner_task, timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("MCP client runner task did not stop within 5s; cancelling")
                    self._runner_task.cancel()
                    with contextlib.suppress(Exception):
                        await self._runner_task

            logger.debug("Microsoft Learn MCP client closed")
        except (asyncio.CancelledError, MCPError) as e:
            logger.warning(f"Error during MCP client close: {e}")
        except Exception:
            logger.exception("Unexpected error during MCP client close")
        finally:
            self._initialized = False
            self._runner_task = None
            self._ready_event = None
            self._stop_event = None
            self._startup_error = None

    async def _cleanup_session(self) -> None:
        """Internal helper to close the MCP session (innermost).
        
        Note: This should NOT call __aexit__ from a different task.
        The session cleanup happens in _run_connection_owner() when it exits.
        This method just clears references.
        """
        if not self._session:
            return
        # Don't call __aexit__ from a different task - causes RuntimeError
        # The session will be cleaned up by _run_connection_owner() exiting
        logger.debug("Clearing MCP session reference (cleanup in owner task)")
        self._session = None

    async def _cleanup_connection_context(self) -> None:
        """Internal helper to close the MCP connection context (outermost).
        
        Note: This should NOT call __aexit__ from a different task.
        The connection cleanup happens in _run_connection_owner() when it exits.
        This method just clears references.
        """
        if not (self._connection_context and self._streams):
            return
        # Don't call __aexit__ from a different task - causes RuntimeError
        # The connection will be cleaned up by _run_connection_owner() exiting
        logger.debug("Clearing MCP connection reference (cleanup in owner task)")
        self._connection_context = None
        self._streams = None

    async def _cleanup(self) -> None:
        """
        Internal cleanup of connection resources.

        Properly closes session and connection context managers in reverse order
        of initialization to ensure clean shutdown.
        """
        try:
            await self._cleanup_session()
            await self._cleanup_connection_context()
        except (asyncio.CancelledError, MCPError) as e:
            logger.warning(f"Error during cleanup: {e}")
        except Exception:
            logger.exception("Unexpected error during cleanup")

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

        # Retry policy: 3 attempts total then fail.
        max_attempts = max(int(self.max_retries or 3), 1)
        attempt_details: list[dict[str, Any]] = []
        start_total = time.perf_counter()
        last_exc: BaseException | None = None

        for attempt_number in range(1, max_attempts + 1):
            start_attempt = time.perf_counter()
            try:
                logger.debug(
                    "Calling tool '%s' (attempt %s/%s) with args: %s",
                    tool_name,
                    attempt_number,
                    max_attempts,
                    arguments,
                )

                # Serialize calls to avoid overlapping session usage.
                async with self._call_lock:
                    result = await asyncio.wait_for(
                        self._session.call_tool(tool_name, arguments=arguments),
                        timeout=call_timeout,
                    )

                normalized = self._normalize_response(result, tool_name)
                elapsed_ms = (time.perf_counter() - start_attempt) * 1000.0
                attempt_details.append(
                    {"attempt": attempt_number, "latencyMs": round(elapsed_ms, 2), "error": None}
                )

                total_ms = (time.perf_counter() - start_total) * 1000.0
                normalized["meta"] = {
                    "endpoint": self.endpoint,
                    "tool": tool_name,
                    "attempts": attempt_number,
                    "timeoutSeconds": call_timeout,
                    "totalLatencyMs": round(total_ms, 2),
                    "attemptDetails": attempt_details,
                }

                logger.debug("Tool '%s' completed successfully", tool_name)
                return normalized

            except asyncio.TimeoutError as exc:
                elapsed_ms = (time.perf_counter() - start_attempt) * 1000.0
                attempt_details.append(
                    {"attempt": attempt_number, "latencyMs": round(elapsed_ms, 2), "error": "timeout"}
                )
                last_exc = exc

            except Exception as exc:  # noqa: BLE001
                elapsed_ms = (time.perf_counter() - start_attempt) * 1000.0
                attempt_details.append(
                    {"attempt": attempt_number, "latencyMs": round(elapsed_ms, 2), "error": str(exc)}
                )
                last_exc = exc

            if attempt_number < max_attempts:
                # Exponential backoff + jitter
                base = min(0.5 * (2 ** (attempt_number - 1)), 8.0)
                jitter = random.uniform(0.0, 0.25)
                await asyncio.sleep(min(base + jitter, 8.0))

        total_ms = (time.perf_counter() - start_total) * 1000.0
        if isinstance(last_exc, asyncio.TimeoutError):
            raise MCPTimeoutError(
                f"Tool call '{tool_name}' timed out after {call_timeout}s (attempts={max_attempts})",
                details={
                    "tool": tool_name,
                    "timeout": call_timeout,
                    "arguments": arguments,
                    "attempts": max_attempts,
                    "totalLatencyMs": round(total_ms, 2),
                    "attemptDetails": attempt_details,
                },
            ) from last_exc

        logger.error("Tool call '%s' failed after %s attempts: %s", tool_name, max_attempts, last_exc)
        raise MCPUnexpectedResponseError(
            f"Tool call failed after {max_attempts} attempts: {last_exc!s}",
            details={
                "tool": tool_name,
                "arguments": arguments,
                "error": str(last_exc),
                "attempts": max_attempts,
                "totalLatencyMs": round(total_ms, 2),
                "attemptDetails": attempt_details,
            },
        ) from last_exc

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

    def _parse_content_block(self, block: Any) -> Any:
        """Parse a single content block from MCP response."""
        if not (hasattr(block, "type") and block.type == "text"):
            return str(block)

        text = getattr(block, "text", "")
        # Try to parse as JSON if it looks like JSON
        if text.strip().startswith(("{", "[")):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        return text

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
            parsed_content = [self._parse_content_block(block) for block in content_blocks]

            # Return single item if only one content block
            final_content = (
                parsed_content[0] if len(parsed_content) == 1 else parsed_content
            )

            return {
                "tool": tool_name,
                "content": final_content,
                "error": None,
                "isError": getattr(result, "isError", False),
            }

        except Exception as e:
            if isinstance(e, MCPUnexpectedResponseError):
                raise
            raise MCPUnexpectedResponseError(
                f"Failed to normalize response: {e!s}",
                details={"tool": tool_name, "error": str(e), "result": str(result)},
            ) from e


    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

