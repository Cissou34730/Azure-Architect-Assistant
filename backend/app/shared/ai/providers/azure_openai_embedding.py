"""
Azure OpenAI Embedding Provider Implementation.
"""

import logging

from ..config import AIConfig
from .azure_openai_client import get_azure_openai_client
from .openai_embedding import EMBEDDING_DIMENSIONS, OpenAIEmbeddingProvider

logger = logging.getLogger(__name__)


class AzureOpenAIEmbeddingProvider(OpenAIEmbeddingProvider):
    """Azure OpenAI implementation of embedding provider."""

    def __init__(self, config: AIConfig):
        self.config = config
        self.client = get_azure_openai_client(config)
        self.model = config.azure_embedding_deployment
        logger.info(
            "Azure OpenAI Embedding Provider initialized with deployment: %s",
            self.model,
        )

    def get_embedding_dimension(self) -> int:
        # self.model holds the Azure deployment name (e.g. "my-ada-deployment").
        # Dimensions are determined by the underlying OpenAI model architecture,
        # which is stored separately as openai_embedding_model.
        return EMBEDDING_DIMENSIONS.get(self.config.openai_embedding_model, 1536)
