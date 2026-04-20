"""MCP / agent runtime settings mixin."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# Anchors - this file lives at backend/app/shared/config/settings/agents.py
_BACKEND_ROOT: Path = Path(__file__).resolve().parents[4]


class AgentsSettingsMixin(BaseModel):
    mcp_config_path: Path = Field(
        default_factory=lambda: _BACKEND_ROOT / "config" / "mcp" / "mcp_config.json",
    )
    mcp_default_timeout: int = Field(30)
    mcp_max_retries: int = Field(3)

    # LangGraph runtime
    aaa_use_langgraph: bool = Field(default=True)

    # Memory & context engineering flags
    aaa_thread_memory_enabled: bool = Field(
        default=True,
        description="Enable LangGraph checkpointer for thread-scoped conversation memory",
    )
    aaa_context_compaction_enabled: bool = Field(
        default=True,
        description="Enable conversation summarization / compaction",
    )
    aaa_context_packs_enabled: bool = Field(
        default=False,
        description="Enable stage-specific context packs instead of monolithic summary",
    )
    aaa_context_debug_enabled: bool = Field(
        default=False,
        description="Expose context debug info in API responses",
    )
    aaa_context_max_history_turns: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Max recent turns kept in hot memory",
    )
    aaa_context_compact_threshold_tokens: int = Field(
        default=4000,
        ge=500,
        le=50000,
        description="Token threshold to trigger conversation compaction",
    )
    aaa_context_max_budget_tokens: int = Field(
        default=24000,
        ge=1000,
        le=128000,
        description="Total token budget for context pack assembly",
    )

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
