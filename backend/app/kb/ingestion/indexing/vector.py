"""
Vector Index Builder
Builds vector indexes using LlamaIndex.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

from llama_index.core import Document, VectorStoreIndex, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

from .base import BaseIndexBuilder

logger = logging.getLogger(__name__)


class VectorIndexBuilder(BaseIndexBuilder):
    """
    Vector index builder using LlamaIndex.
    Creates vector embeddings and builds searchable index.
    """
    
    def __init__(
        self,
        kb_id: str,
        storage_dir: str,
        embedding_model: str = "text-embedding-3-small",
        generation_model: str = "gpt-4o-mini"
    ):
        """
        Initialize vector index builder.
        
        Args:
            kb_id: Knowledge base identifier
            storage_dir: Directory for index storage
            embedding_model: Model for embeddings
            generation_model: Model for generation/LLM tasks
        """
        super().__init__(kb_id, storage_dir, embedding_model, generation_model)
        
        # Initialize LlamaIndex settings
        Settings.embed_model = OpenAIEmbedding(model=embedding_model)
        Settings.llm = OpenAI(model=generation_model, temperature=0.1)
        
        self.logger.info(f"VectorIndexBuilder initialized for KB '{kb_id}'")
        self.logger.info(f"  Storage: {storage_dir}")
        self.logger.info(f"  Embedding model: {embedding_model}")
        self.logger.info(f"  Generation model: {generation_model}")
    
    def build_index(
        self,
        documents: List[Dict[str, Any]],
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        Build vector index from documents.
        
        Args:
            documents: List of documents with 'content' and 'metadata' keys
            progress_callback: Optional callback(phase, progress, message, metrics)
            
        Returns:
            Path to the created index
        """
        from ..base import IngestionPhase
        
        self.logger.info("=" * 70)
        self.logger.info(f"Building vector index for KB: {self.kb_id}")
        self.logger.info("=" * 70)
        
        # Validate documents
        if not self.validate_documents(documents):
            raise ValueError("Document validation failed")
        
        if progress_callback:
            progress_callback(
                IngestionPhase.EMBEDDING,
                0,
                "Converting documents...",
                {'documents': len(documents)}
            )
        
        # Convert to LlamaIndex documents
        llama_docs = self._build_llama_documents(documents)
        
        if not llama_docs:
            raise ValueError("No valid documents to index")
        
        self.logger.info(f"Converted {len(llama_docs)} documents")
        
        if progress_callback:
            progress_callback(
                IngestionPhase.EMBEDDING,
                25,
                f"Building index from {len(llama_docs)} documents...",
                {'documents': len(llama_docs)}
            )
        
        # Build index
        self.logger.info("Generating embeddings and building index...")
        if progress_callback:
            progress_callback(
                IngestionPhase.EMBEDDING,
                50,
                "Generating embeddings...",
                {}
            )
        
        index = VectorStoreIndex.from_documents(
            llama_docs,
            show_progress=True
        )
        
        if progress_callback:
            progress_callback(
                IngestionPhase.INDEXING,
                75,
                "Persisting index to storage...",
                {}
            )
        
        # Persist index
        os.makedirs(self.storage_dir, exist_ok=True)
        index.storage_context.persist(persist_dir=self.storage_dir)
        
        self.logger.info(f"Index persisted to {self.storage_dir}")
        
        # Save metadata
        self._save_index_metadata(len(documents), len(llama_docs))
        
        if progress_callback:
            progress_callback(
                IngestionPhase.INDEXING,
                100,
                f"Index complete: {len(documents)} documents",
                {'documents': len(documents)}
            )
        
        self.logger.info("=" * 70)
        self.logger.info("Vector index build complete!")
        self.logger.info(f"  Documents: {len(documents)}")
        self.logger.info(f"  Storage: {self.storage_dir}")
        self.logger.info("=" * 70)
        
        return self.storage_dir
    
    def _build_llama_documents(self, documents: List[Dict[str, Any]]) -> List[Document]:
        """
        Convert documents to LlamaIndex Document objects.
        
        Args:
            documents: List of documents with 'content' and 'metadata' keys
            
        Returns:
            List of LlamaIndex Documents
        """
        llama_docs = []
        
        for i, doc in enumerate(documents):
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            
            if not content:
                self.logger.warning(f"Skipping document {i}: empty content")
                continue
            
            # Create document ID
            doc_id = metadata.get('url') or metadata.get('file_path') or f"doc_{i}"
            if len(doc_id) > 200:  # Truncate long IDs
                doc_id = doc_id[:200]
            
            llama_doc = Document(
                text=content,
                metadata=metadata,
                id_=doc_id
            )
            
            llama_docs.append(llama_doc)
        
        self.logger.info(f"Created {len(llama_docs)} LlamaIndex documents")
        return llama_docs
    
    def _save_index_metadata(self, doc_count: int, indexed_count: int):
        """Save index metadata"""
        metadata_file = os.path.join(self.storage_dir, "metadata.json")
        
        metadata = {
            'kb_id': self.kb_id,
            'documents': doc_count,
            'indexed_documents': indexed_count,
            'embedding_model': self.embedding_model,
            'generation_model': self.generation_model,
            'index_type': 'vector'
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        self.logger.info(f"Metadata saved to {metadata_file}")
