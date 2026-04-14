"""
AI Service Configuration - focused DTO populated from AppSettings.

``AIConfig`` is a Pydantic model.  It is **not** a
``BaseSettings`` subclass and does **not** read from environment variables
directly.  Use ``AIConfig.from_settings(get_app_settings())`` to build one,
or call ``AIConfig.default()`` as a shorthand.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.shared.config.app_settings import AppSettings


class AIConfig(BaseModel):
    """Focused AI provider configuration consumed by AIService and providers."""

    # Provider selection
    llm_provider: Literal["openai", "foundry", "anthropic", "local", "copilot"] = "openai"
    embedding_provider: Literal["openai", "foundry", "local"] = "openai"

    # OpenAI
    openai_api_key: str = ""
    openai_project: str = ""
    openai_organization: str = ""
    openai_llm_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_timeout: float = 600.0
    openai_max_retries: int = 0

    # AI Foundry
    foundry_endpoint: str = ""
    foundry_api_key: str = ""
    foundry_api_version: str = "2024-10-21"
    foundry_resource_id: str = ""
    foundry_model: str = ""
    foundry_embedding_model: str = ""

    # GitHub Copilot
    copilot_token: str = ""
    copilot_default_model: str = "gpt-5.2"
    copilot_allowed_models: str = ""
    copilot_request_timeout: float = 120.0
    copilot_startup_timeout: float = 30.0
    copilot_auth_poll_interval: float = 3.0
    copilot_auth_timeout: float = 300.0

    # Model defaults
    default_temperature: Annotated[float, Field(ge=0.0, le=2.0)] = 0.7
    default_max_tokens: Annotated[int, Field(gt=0)] = 1000

    # Rate limiting
    max_requests_per_minute: Annotated[int, Field(gt=0)] = 60
    max_tokens_per_minute: Annotated[int, Field(gt=0)] = 150_000

    @property
    def active_llm_model(self) -> str:
        """Return the configured runtime LLM identity for the selected provider."""
        if self.llm_provider == "foundry":
            return self.foundry_model
        if self.llm_provider == "copilot":
            return self.copilot_default_model
        return self.openai_llm_model

    @property
    def active_embedding_model(self) -> str:
        """Return the configured runtime embedding identity for the selected provider."""
        if self.embedding_provider == "foundry":
            return self.foundry_embedding_model or self.openai_embedding_model
        return self.openai_embedding_model

    @classmethod
    def from_settings(cls, settings: AppSettings) -> AIConfig:
        """Build an AIConfig from the centralised AppSettings."""
        effective_emb_model = settings.openai_embedding_model or settings.ai_openai_embedding_model
        return cls(
            llm_provider=settings.effective_ai_llm_provider,
            embedding_provider=settings.ai_embedding_provider,
            openai_api_key=settings.effective_openai_api_key,
            openai_project=settings.ai_openai_project,
            openai_organization=settings.ai_openai_organization,
            openai_llm_model=settings.effective_openai_llm_model,
            openai_embedding_model=effective_emb_model,
            openai_timeout=settings.ai_openai_timeout,
            openai_max_retries=settings.ai_openai_max_retries,
            foundry_endpoint=settings.effective_foundry_endpoint,
            foundry_api_key=settings.effective_foundry_api_key,
            foundry_api_version=settings.ai_foundry_api_version,
            foundry_resource_id=settings.effective_foundry_resource_id,
            foundry_model=settings.effective_foundry_model,
            copilot_token=settings.effective_copilot_token,
            copilot_default_model=settings.effective_copilot_default_model,
            copilot_allowed_models=settings.ai_copilot_allowed_models,
            copilot_request_timeout=settings.ai_copilot_request_timeout,
            copilot_startup_timeout=settings.ai_copilot_startup_timeout,
            copilot_auth_poll_interval=settings.ai_copilot_auth_poll_interval,
            copilot_auth_timeout=settings.ai_copilot_auth_timeout,
            default_temperature=settings.ai_default_temperature,
            default_max_tokens=settings.ai_default_max_tokens,
            max_requests_per_minute=settings.ai_max_requests_per_minute,
            max_tokens_per_minute=settings.ai_max_tokens_per_minute,
        )

    @classmethod
    def default(cls) -> AIConfig:
        """Convenience shorthand: build from the cached AppSettings singleton."""
        from app.shared.config.app_settings import get_app_settings  # noqa: PLC0415
        return cls.from_settings(get_app_settings())

    def validate_provider_config(self) -> None:
        """Validate that required config for selected provider is present."""
        needs_openai = self.llm_provider == "openai" or self.embedding_provider == "openai"
        needs_copilot = self.llm_provider == "copilot"
        needs_foundry_llm = self.llm_provider == "foundry"
        needs_foundry_embedding = self.embedding_provider == "foundry"

        if needs_openai and not self.openai_api_key:
            raise ValueError("OpenAI API key is required for OpenAI provider")

        if needs_foundry_llm and not all(
            [
                self.foundry_endpoint,
                self.foundry_api_key,
                self.foundry_resource_id,
                self.foundry_model,
            ]
        ):
            raise ValueError(
                "Foundry endpoint, API key, resource id, and runtime model required for Foundry provider"
            )

        if needs_foundry_embedding and not all(
            [
                self.foundry_endpoint,
                self.foundry_api_key,
                self.foundry_resource_id,
            ]
        ):
            raise ValueError(
                "Foundry endpoint, API key, and resource id required for Foundry embeddings"
            )

        if needs_copilot and not self.copilot_default_model:
            raise ValueError("Copilot default model is required for Copilot provider")

