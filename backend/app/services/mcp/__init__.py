"""
MCP (Model Context Protocol) service package.
Provides abstraction layer for external tool integrations via MCP.
"""

from .exceptions import (
    MCPCapabilityError,
    MCPConfigurationError,
    MCPConnectionError,
    MCPError,
    MCPProtocolError,
    MCPTimeoutError,
    MCPUnexpectedResponseError,
)
from .learn_mcp_client import MicrosoftLearnMCPClient
from .operations import (
    fetch_documentation,
    get_azure_guidance,
    search_code_samples,
    search_microsoft_docs,
)

__all__ = [
    "MCPCapabilityError",
    "MCPConfigurationError",
    "MCPConnectionError",
    "MCPError",
    "MCPProtocolError",
    "MCPTimeoutError",
    "MCPUnexpectedResponseError",
    "MicrosoftLearnMCPClient",
    "fetch_documentation",
    "get_azure_guidance",
    "search_code_samples",
    "search_microsoft_docs",
]

