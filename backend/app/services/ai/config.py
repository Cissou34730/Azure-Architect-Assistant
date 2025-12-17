"""
AI Service Configuration
Centralized configuration for all AI providers.
"""

import os
from typing import Literal
from pydantic_settings import BaseSettings


class AIConfig(BaseSettings):
    """Configuration for AI services (LLM and Embedding providers)."""
    
    # Provider selection
    llm_provider: Literal["openai", "azure", "anthropic", "local"] = "openai"
    embedding_provider: Literal["openai", "azure", "local"] = "openai"
    
    # OpenAI Configuration
    openai_api_key: str = ""
    openai_llm_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_timeout: float = 90.0
    openai_max_retries: int = 3
    
    # Azure OpenAI Configuration (optional)
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-02-15-preview"
    azure_llm_deployment: str = ""
    azure_embedding_deployment: str = ""
    
    # Model Parameters
    default_temperature: float = 0.7
    default_max_tokens: int = 1000
    
    # Rate Limiting
    max_requests_per_minute: int = 60
    max_tokens_per_minute: int = 150000
    
    class Config:
        env_prefix = "AI_"
        env_file = ".env"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Fallback to OPENAI_API_KEY if AI_OPENAI_API_KEY not set
        if not self.openai_api_key:
            self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
    
    def validate_provider_config(self) -> None:
        """Validate that required config for selected provider is present."""
        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("OpenAI API key is required for OpenAI LLM provider")
        
        if self.llm_provider == "azure":
            if not all([self.azure_openai_endpoint, self.azure_openai_api_key, self.azure_llm_deployment]):
                raise ValueError("Azure endpoint, API key, and deployment name required for Azure provider")
        
        if self.embedding_provider == "openai" and not self.openai_api_key:
            raise ValueError("OpenAI API key is required for OpenAI embedding provider")
        
        if self.embedding_provider == "azure":
            if not all([self.azure_openai_endpoint, self.azure_openai_api_key, self.azure_embedding_deployment]):
                raise ValueError("Azure endpoint, API key, and deployment name required for Azure embeddings")
