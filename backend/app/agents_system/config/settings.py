"""
Agent system settings and configuration.
Centralizes all configuration parameters for agents, tools, and orchestration.
"""

import json
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Agent system configuration settings.

    Settings are loaded from environment variables and configuration files.
    """

    # MCP Configuration
    MCP_CONFIG_PATH: str = str(
        Path(__file__).parent.parent.parent.parent
        / "config"
        / "mcp"
        / "mcp_config.json"
    )
    MCP_DEFAULT_TIMEOUT: int = 30
    MCP_MAX_RETRIES: int = 3

    # Agent Configuration (TODO: Expand as needed)
    # AGENT_MODEL: str = "gpt-4"
    # AGENT_TEMPERATURE: float = 0.7

    # Tool Configuration (TODO: Expand as needed)
    # TOOL_TIMEOUT: int = 60
    # TOOL_RETRY_POLICY: str = "exponential"

    # Orchestration Settings (TODO: Expand as needed)
    # MAX_ITERATIONS: int = 10
    # PARALLEL_EXECUTION: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True

    def load_mcp_config(self) -> dict[str, Any]:
        """
        Load MCP configuration from file.

        Returns:
            Dictionary with MCP server configurations

        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config file is invalid JSON
        """
        config_path = Path(self.MCP_CONFIG_PATH)

        if not config_path.exists():
            raise FileNotFoundError(
                f"MCP config file not found: {config_path}. "
                f"Create it at {config_path} or set MCP_CONFIG_PATH environment variable."
            )

        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_mcp_server_config(self, server_name: str) -> dict[str, Any]:
        """
        Get configuration for a specific MCP server.

        Args:
            server_name: Name of the MCP server (e.g., "microsoft_learn")

        Returns:
            Server configuration dictionary

        Raises:
            KeyError: If server not found in config
        """
        config = self.load_mcp_config()

        if server_name not in config:
            raise KeyError(
                f"MCP server '{server_name}' not found in config. "
                f"Available servers: {list(config.keys())}"
            )

        return config[server_name]


# Global settings instance
settings = Settings()
