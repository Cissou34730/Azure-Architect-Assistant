"""AI provider settings mixin.

All AI provider configuration lives here.  Fields are read from the .env file
by BaseSettings (case-insensitive).  The ``AIConfig`` dataclass at the bottom
is a focused DTO used by AIService / providers - it is populated from these
fields via ``AIConfig.from_settings()`` rather than reading env vars directly.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass


class AISettingsMixin(BaseModel):
    # ── Provider selection ────────────────────────────────────────────────────
    ai_llm_provider: Literal["openai", "azure", "anthropic", "local"] = "openai"
    ai_embedding_provider: Literal["openai", "azure", "local"] = "openai"
    ai_fallback_provider: Literal["openai", "azure", "none"] = "none"
    ai_fallback_enabled: bool = False
    ai_fallback_on_transient_only: bool = True

    # ── Legacy bare env vars (OPENAI_API_KEY, OPENAI_MODEL, …) ──────────────
    # Kept so .env files using the un-prefixed form still work.
    openai_api_key: str | None = None           # reads OPENAI_API_KEY
    openai_model: str | None = None             # reads OPENAI_MODEL
    openai_embedding_model: str | None = None   # reads OPENAI_EMBEDDING_MODEL

    # ── AI-prefixed OpenAI settings (AI_OPENAI_* env vars) ──────────────────
    ai_openai_api_key: str = ""
    ai_openai_project: str = ""
    ai_openai_organization: str = ""
    ai_openai_llm_model: str = Field(default="gpt-4o-mini")
    ai_openai_embedding_model: str = Field(default="text-embedding-3-small")
    ai_openai_timeout: float = Field(default=600.0)
    ai_openai_max_retries: int = Field(default=0)  # callers own retry strategy

    # ── Azure OpenAI settings (AI_AZURE_* env vars) ──────────────────────────
    ai_azure_openai_endpoint: str = ""
    ai_azure_openai_api_key: str = ""
    ai_azure_openai_api_version: str = "2024-02-15-preview"
    ai_azure_llm_deployment: str = ""
    ai_azure_llm_deployments: str = ""
    ai_azure_embedding_deployment: str = ""

    # ── Model defaults ────────────────────────────────────────────────────────
    ai_default_temperature: float = Field(default=0.7)
    ai_default_max_tokens: int = Field(default=1000)

    # ── Rate limiting ─────────────────────────────────────────────────────────
    ai_max_requests_per_minute: int = Field(default=60)
    ai_max_tokens_per_minute: int = Field(default=150_000)
