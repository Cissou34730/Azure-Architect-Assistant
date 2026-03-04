"""
Abstract base class for MCP client implementations.
All concrete MCP clients must extend MCPClient and implement the public contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .exceptions import MCPConfigurationError


class MCPClient(ABC):
    """Abstract MCP client. Concrete clients handle a specific MCP server."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._validate_config(config)

    def _validate_config(self, config: dict[str, Any]) -> None:
        """Base configuration validation. Subclasses may extend."""
        if not config:
            raise MCPConfigurationError("Config dictionary cannot be empty")
        if "endpoint" not in config:
            raise MCPConfigurationError("Missing required config parameter: 'endpoint'")
        endpoint = config["endpoint"]
        if not isinstance(endpoint, str) or not endpoint.startswith("http"):
            raise MCPConfigurationError(
                f"Invalid endpoint URL: {endpoint}. Must start with http:// or https://"
            )

    @property
    @abstractmethod
    def is_initialized(self) -> bool:
        """Return True if the client is connected and ready to accept calls."""
        ...

    @abstractmethod
    async def initialize(self) -> None:
        """Establish connection to the MCP server."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Disconnect and release all resources. Safe to call multiple times."""
        ...

    @abstractmethod
    def list_tools(self) -> list[dict[str, Any]]:
        """Return available tool schemas discovered from the server."""
        ...

    @abstractmethod
    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Execute a tool call on the MCP server and return the normalized response."""
        ...

