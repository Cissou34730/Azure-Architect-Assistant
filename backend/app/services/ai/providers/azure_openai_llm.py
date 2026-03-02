"""
Azure OpenAI LLM Provider Implementation.
"""

import logging

from ..config import AIConfig
from .azure_openai_client import get_azure_openai_client
from .openai_llm import OpenAILLMProvider

logger = logging.getLogger(__name__)


class AzureOpenAILLMProvider(OpenAILLMProvider):
    """Azure OpenAI implementation of LLM provider."""

    def __init__(self, config: AIConfig):
        self.config = config
        self.client = get_azure_openai_client(config)
        self.model = config.azure_llm_deployment
        logger.info("Azure OpenAI LLM Provider initialized with deployment: %s", self.model)
