"""
OpenAI Embedder
Generates embeddings using OpenAI embedding models.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable

from llama_index.core import Document

from .embedder_base import BaseEmbedder
from app.services.ai import get_ai_service

logger = logging.getLogger(__name__)


class OpenAIEmbedder(BaseEmbedder):
    """
    Generate embeddings using OpenAI embedding models.
    Uses unified AIService for consistent configuration and monitoring.
    """
    
    def __init__(self, model_name: str = "text-embedding-3-small"):
        """
        Initialize OpenAI embedder.
        
        Args:
            model_name: OpenAI embedding model name
        """
        super().__init__(model_name)
        self.ai_service = get_ai_service()
        self.logger.info(f"OpenAIEmbedder initialized with model: {model_name}")
    
    def embed_documents(
        self,
        documents: List[Dict[str, Any]],
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for documents using OpenAI.
        
        Args:
            documents: List of documents with 'content' and 'metadata' keys
            progress_callback: Optional callback(phase, progress, message, metrics)
            
        Returns:
            List of LlamaIndex Documents with embeddings
        """
        if not self.validate_documents(documents):
            raise ValueError("Document validation failed")
        
        self.logger.info(f"Generating embeddings for {len(documents)} documents")
        
        # Convert to LlamaIndex documents
        llama_docs = []
        for i, doc in enumerate(documents):
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            
            if not content:
                self.logger.warning(f"Skipping document {i}: empty content")
                continue
            
            # Create document ID
            doc_id = metadata.get('url') or metadata.get('file_path') or f"doc_{metadata.get('doc_id', i)}"
            if len(doc_id) > 200:
                doc_id = doc_id[:200]
            
            llama_doc = Document(
                text=content,
                metadata=metadata,
                id_=doc_id
            )
            llama_docs.append(llama_doc)
        
        if progress_callback:
            from app.ingestion.domain.phase_tracker import IngestionPhase
            progress_callback(
                IngestionPhase.EMBEDDING,
                25,
                f"Generating embeddings for {len(llama_docs)} documents...",
                {'documents': len(llama_docs)}
            )
        
        # Generate embeddings using AIService
        # Extract all texts for batch processing
        texts = [doc.text for doc in llama_docs]
        
        # Use asyncio to run async batch embedding
        try:
            embeddings = asyncio.run(self.ai_service.embed_batch(texts))
        except RuntimeError:
            # If already in event loop, create task
            loop = asyncio.get_event_loop()
            embeddings = loop.run_until_complete(self.ai_service.embed_batch(texts))
        
        # Assign embeddings to documents
        for i, (doc, embedding) in enumerate(zip(llama_docs, embeddings)):
            doc.embedding = embedding
            
            # Progress callback every 10 documents
            if progress_callback and i % 10 == 0:
                progress = 25 + int((i / len(llama_docs)) * 50)  # 25-75%
                from app.ingestion.domain.phase_tracker import IngestionPhase
                progress_callback(
                    IngestionPhase.EMBEDDING,
                    progress,
                    f"Embedded {i}/{len(llama_docs)} documents",
                    {'embedded': i, 'total': len(llama_docs)}
                )
        
        if progress_callback:
            from app.ingestion.domain.phase_tracker import IngestionPhase
            progress_callback(
                IngestionPhase.EMBEDDING,
                75,
                f"Embedding complete: {len(llama_docs)} documents",
                {'documents': len(llama_docs)}
            )
        
        self.logger.info(f"Generated embeddings for {len(llama_docs)} documents")
        return llama_docs
