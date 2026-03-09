"""MCP / agent runtime settings mixin."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# Anchors - this file lives at backend/app/core/settings/agents.py
_BACKEND_ROOT: Path = Path(__file__).resolve().parents[3]


class AgentsSettingsMixin(BaseModel):
    mcp_config_path: Path = Field(
        default_factory=lambda: _BACKEND_ROOT / "config" / "mcp" / "mcp_config.json",
    )
    mcp_default_timeout: int = Field(30)
    mcp_max_retries: int = Field(3)

    # LangGraph runtime flags
    aaa_use_langgraph: bool = Field(default=True)
    aaa_enable_stage_routing: bool = Field(default=False)
    aaa_enable_multi_agent: bool = Field(default=False)

    @field_validator("mcp_config_path", mode="before")
    @classmethod
    def _resolve_mcp_path(cls, value: object) -> Path:
        if isinstance(value, str):
            return Path(value)
        return value  # type: ignore[return-value]

    @model_validator(mode="after")
    def _apply_langgraph_compat_flags(self) -> AgentsSettingsMixin:
        # Backend runtime is LangGraph-only.
        self.aaa_use_langgraph = True
        return self

    def load_mcp_config(self) -> dict[str, Any]:
        """Load MCP configuration from file."""
        if not self.mcp_config_path.exists():
            raise FileNotFoundError(
                f"MCP config file not found: {self.mcp_config_path}. "
                "Create it or set MCP_CONFIG_PATH environment variable."
            )
        with open(self.mcp_config_path, encoding="utf-8") as f:
            return json.load(f)

    def get_mcp_server_config(self, server_name: str) -> dict[str, Any]:
        """Get configuration for a specific MCP server."""
        config = self.load_mcp_config()
        if server_name not in config:
            raise KeyError(
                f"MCP server '{server_name}' not found in config. "
                f"Available servers: {list(config.keys())}"
            )
        return config[server_name]
