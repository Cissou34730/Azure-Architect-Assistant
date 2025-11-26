"""
Generic Index Builder
Builds vector indexes from cleaned documents using LlamaIndex.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from llama_index.core import Document, VectorStoreIndex, StorageContext, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

from ..base import IndexBuilder

logger = logging.getLogger(__name__)


class GenericIndexBuilder(IndexBuilder):
    """
    Generic index builder for any knowledge base.
    Chunks documents, generates embeddings, and builds vector index.
    """
    
    def __init__(self, kb_config: Dict[str, Any]):
        """
        Initialize index builder.
        
        Args:
            kb_config: Knowledge base configuration
        """
        super().__init__(kb_config)
        
        # Get storage directory
        backend_root = Path(__file__).parent.parent.parent.parent.parent
        if 'paths' in kb_config and 'index' in kb_config['paths']:
            index_path = kb_config['paths']['index']
            if os.path.isabs(index_path):
                self.storage_dir = index_path
            else:
                self.storage_dir = str(backend_root / index_path)
        else:
            # Default path
            self.storage_dir = str(backend_root / "data" / "knowledge_bases" / self.kb_id / "index")
        
        # Initialize LlamaIndex settings
        Settings.embed_model = OpenAIEmbedding(model=self.embedding_model)
        Settings.llm = OpenAI(
            model=kb_config.get('generation_model', 'gpt-4o-mini'),
            temperature=0.1
        )
        
        # Initialize text splitter
        self.text_splitter = SentenceSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        
        self.logger.info(f"Initialized for KB '{self.kb_id}'")
        self.logger.info(f"  Storage: {self.storage_dir}")
        self.logger.info(f"  Chunk size: {self.chunk_size}, Overlap: {self.chunk_overlap}")
        self.logger.info(f"  Embedding model: {self.embedding_model}")
    
    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk documents into smaller pieces.
        
        Args:
            documents: List of cleaned documents
            
        Returns:
            List of chunks with metadata
        """
        chunks = []
        
        for doc in documents:
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            
            # Split into sentences/chunks
            text_chunks = self.text_splitter.split_text(content)
            
            for i, chunk_text in enumerate(text_chunks):
                chunks.append({
                    'text': chunk_text,
                    'metadata': {
                        **metadata,
                        'chunk_index': i,
                        'total_chunks': len(text_chunks)
                    }
                })
        
        self.logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")
        return chunks
    
    def build_llama_documents(self, documents: List[Dict[str, Any]]) -> List[Document]:
        """
        Convert cleaned documents to LlamaIndex Document objects.
        
        Args:
            documents: List of cleaned documents
            
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
            
            # Create document ID from URL or index
            doc_id = metadata.get('url', f"doc_{i}")
            if len(doc_id) > 200:  # Truncate long URLs
                doc_id = doc_id[:200]
            
            llama_doc = Document(
                text=content,
                metadata=metadata,
                id_=doc_id
            )
            
            llama_docs.append(llama_doc)
        
        self.logger.info(f"Created {len(llama_docs)} LlamaIndex documents")
        return llama_docs
    
    def build_index(
        self,
        documents: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> str:
        """
        Build vector index from documents.
        
        Args:
            documents: List of cleaned documents
            progress_callback: Optional callback(phase, current, total, message)
            
        Returns:
            Path to the created index
        """
        from ..base import IngestionPhase
        
        self.logger.info("="*70)
        self.logger.info(f"Building index for KB: {self.kb_id}")
        self.logger.info("="*70)
        
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
        llama_docs = self.build_llama_documents(documents)
        
        if not llama_docs:
            raise ValueError("No valid documents to index")
        
        # Get chunk count for progress
        chunks = self.chunk_documents(documents)
        total_chunks = len(chunks)
        
        self.logger.info(f"Documents: {len(documents)}, Chunks: {total_chunks}")
        
        if progress_callback:
            progress_callback(
                IngestionPhase.EMBEDDING,
                25,
                f"Chunking {len(documents)} documents into {total_chunks} chunks...",
                {'total_chunks': total_chunks}
            )
        
        # Build index
        self.logger.info("Building vector index...")
        if progress_callback:
            progress_callback(
                IngestionPhase.EMBEDDING,
                50,
                "Generating embeddings and building index...",
                {'total_chunks': total_chunks}
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
                {'total_chunks': total_chunks}
            )
        
        # Persist index
        os.makedirs(self.storage_dir, exist_ok=True)
        index.storage_context.persist(persist_dir=self.storage_dir)
        
        self.logger.info(f"Index persisted to {self.storage_dir}")
        
        # Save metadata
        metadata_file = os.path.join(self.storage_dir, "metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                'kb_id': self.kb_id,
                'documents': len(documents),
                'chunks': total_chunks,
                'chunk_size': self.chunk_size,
                'chunk_overlap': self.chunk_overlap,
                'embedding_model': self.embedding_model
            }, f, indent=2)
        
        if progress_callback:
            progress_callback(
                IngestionPhase.INDEXING,
                100,
                f"Index complete: {len(documents)} docs, {total_chunks} chunks",
                {'documents': len(documents), 'chunks': total_chunks}
            )
        
        self.logger.info("="*70)
        self.logger.info("Index build complete!")
        self.logger.info(f"  Documents: {len(documents)}")
        self.logger.info(f"  Chunks: {total_chunks}")
        self.logger.info(f"  Storage: {self.storage_dir}")
        self.logger.info("="*70)
        
        return self.storage_dir
