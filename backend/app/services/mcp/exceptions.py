"""
Custom exceptions for MCP service layer.
Maps low-level MCP SDK errors to domain-specific exceptions.
"""


class MCPError(Exception):
    """Base exception for all MCP-related errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class MCPConnectionError(MCPError):
    """Failed to establish or maintain connection to MCP server."""

    pass


class MCPTimeoutError(MCPError):
    """MCP operation exceeded timeout threshold."""

    pass


class MCPProtocolError(MCPError):
    """Invalid MCP protocol response or communication error."""

    pass


class MCPCapabilityError(MCPError):
    """Requested tool or capability not available on MCP server."""

    pass


class MCPUnexpectedResponseError(MCPError):
    """Response structure doesn't match expected format."""

    pass


class MCPConfigurationError(MCPError):
    """Invalid MCP client configuration."""

    pass
