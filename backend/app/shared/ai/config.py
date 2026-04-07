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
    llm_provider: Literal["openai", "azure", "anthropic", "local", "copilot"] = "openai"
    embedding_provider: Literal["openai", "azure", "local"] = "openai"
    fallback_provider: Literal["openai", "azure", "none"] = "none"
    fallback_enabled: bool = False
    fallback_on_transient_only: bool = True

    # OpenAI
    openai_api_key: str = ""
    openai_project: str = ""
    openai_organization: str = ""
    openai_llm_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_timeout: float = 600.0
    openai_max_retries: int = 0

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-02-15-preview"
    azure_llm_deployment: str = ""      # active deployment used for LLM inference
    azure_llm_deployments: str = ""     # comma-separated list for model-selection UI only; not used for inference
    azure_embedding_deployment: str = ""

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
        if self.llm_provider == "azure":
            return self.azure_llm_deployment
        if self.llm_provider == "copilot":
            return self.copilot_default_model
        return self.openai_llm_model

    @property
    def active_embedding_model(self) -> str:
        """Return the configured runtime embedding identity for the selected provider."""
        if self.embedding_provider == "azure":
            return self.azure_embedding_deployment
        return self.openai_embedding_model

    @classmethod
    def from_settings(cls, settings: AppSettings) -> AIConfig:
        """Build an AIConfig from the centralised AppSettings."""
        effective_emb_model = settings.openai_embedding_model or settings.ai_openai_embedding_model
        return cls(
            llm_provider=settings.effective_ai_llm_provider,
            embedding_provider=settings.ai_embedding_provider,
            fallback_provider=settings.ai_fallback_provider,
            fallback_enabled=settings.ai_fallback_enabled,
            fallback_on_transient_only=settings.ai_fallback_on_transient_only,
            openai_api_key=settings.effective_openai_api_key,
            openai_project=settings.ai_openai_project,
            openai_organization=settings.ai_openai_organization,
            openai_llm_model=settings.effective_openai_llm_model,
            openai_embedding_model=effective_emb_model,
            openai_timeout=settings.ai_openai_timeout,
            openai_max_retries=settings.ai_openai_max_retries,
            azure_openai_endpoint=settings.effective_azure_openai_endpoint,
            azure_openai_api_key=settings.effective_azure_openai_api_key,
            azure_openai_api_version=settings.ai_azure_openai_api_version,
            azure_llm_deployment=settings.effective_azure_llm_deployment,
            azure_llm_deployments=settings.effective_azure_llm_deployments,
            azure_embedding_deployment=settings.effective_azure_embedding_deployment,
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
        needs_openai = (
            self.llm_provider == "openai"
            or self.embedding_provider == "openai"
            or (self.fallback_enabled and self.fallback_provider == "openai")
        )
        needs_copilot = self.llm_provider == "copilot"
        needs_azure_llm = self.llm_provider == "azure" or (
            self.fallback_enabled and self.fallback_provider == "azure"
        )
        # Embedding fallback is not supported (dimension mismatch risk),
        # so Azure embedding credentials are only required when Azure is
        # the *primary* embedding provider.
        needs_azure_embedding = self.embedding_provider == "azure"

        if needs_openai and not self.openai_api_key:
            raise ValueError("OpenAI API key is required for OpenAI provider")

        if needs_azure_llm and not all(
            [
                self.azure_openai_endpoint,
                self.azure_openai_api_key,
                self.azure_llm_deployment,
            ]
        ):
            raise ValueError(
                "Azure endpoint, API key, and LLM deployment name required for Azure provider"
            )

        if needs_azure_embedding and not all(
            [
                self.azure_openai_endpoint,
                self.azure_openai_api_key,
                self.azure_embedding_deployment,
            ]
        ):
            raise ValueError(
                "Azure endpoint, API key, and embedding deployment name required for Azure embeddings"
            )

        if needs_copilot and not self.copilot_default_model:
            raise ValueError("Copilot default model is required for Copilot provider")

