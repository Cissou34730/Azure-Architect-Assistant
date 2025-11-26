"""
Generic Knowledge Base Service
Wrapper around the existing query logic, now KB-agnostic.
"""

import os
import logging
from typing import Dict, List, Optional
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

from .manager import KBConfig

logger = logging.getLogger(__name__)

# Global index cache across all KBs
_INDEX_CACHE: Dict[str, VectorStoreIndex] = {}


class KnowledgeBaseService:
    """Generic service for querying a knowledge base."""
    
    def __init__(self, kb_config: KBConfig, similarity_threshold: float = 0.5):
        """
        Initialize knowledge base service.
        
        Args:
            kb_config: KB configuration
            similarity_threshold: Minimum similarity score for results
        """
        self.kb_config = kb_config
        self.kb_id = kb_config.id
        self.kb_name = kb_config.name
        self.storage_dir = kb_config.index_path
        self.similarity_threshold = similarity_threshold
        self._settings_configured = False
        
        logger.info(f"[{self.kb_id}] Service initialized - Storage: {self.storage_dir}")
    
    def _ensure_settings(self):
        """Lazy configuration of LlamaIndex settings."""
        if not self._settings_configured:
            # Configure LlamaIndex settings for this KB
            Settings.embed_model = OpenAIEmbedding(model=self.kb_config.embedding_model)
            Settings.llm = OpenAI(
                model=self.kb_config.generation_model,
                temperature=0.1,
                max_tokens=1000,
                timeout=90.0
            )
            self._settings_configured = True
    
    def _load_index(self) -> VectorStoreIndex:
        """Load index from storage with global caching."""
        self._ensure_settings()  # Configure settings before loading index
        
        cache_key = self.storage_dir
        
        if cache_key in _INDEX_CACHE:
            logger.info(f"[{self.kb_id}] Using cached index")
            return _INDEX_CACHE[cache_key]
        
        from llama_index.core import load_index_from_storage
        
        logger.info(f"[{self.kb_id}] Loading index from {self.storage_dir}")
        
        if not os.path.exists(self.storage_dir):
            raise FileNotFoundError(f"Index not found: {self.storage_dir}")
        
        storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
        index = load_index_from_storage(storage_context)
        
        _INDEX_CACHE[cache_key] = index
        logger.info(f"[{self.kb_id}] Index loaded and cached")
        
        return index
    
    def query(
        self,
        question: str,
        top_k: int = 5,
        metadata_filters: Optional[Dict] = None
    ) -> Dict:
        """
        Query the knowledge base.
        
        Args:
            question: Question to ask
            top_k: Number of chunks to retrieve
            metadata_filters: Optional metadata filters
            
        Returns:
            Dictionary with answer, sources, scores, kb_id, kb_name
        """
        logger.info(f"[{self.kb_id}] Processing query: {question[:100]}...")
        
        # Load index and create retriever
        index = self._load_index()
        retriever = index.as_retriever(similarity_top_k=top_k)
        
        # Apply metadata filters if provided
        if metadata_filters:
            from llama_index.core.vector_stores import MetadataFilters, MetadataFilter
            filters = MetadataFilters(
                filters=[
                    MetadataFilter(key=k, value=v)
                    for k, v in metadata_filters.items()
                ]
            )
            retriever = index.as_retriever(similarity_top_k=top_k, filters=filters)
        
        # Retrieve relevant chunks
        retrieved_nodes = retriever.retrieve(question)
        logger.info(f"[{self.kb_id}] Retrieved {len(retrieved_nodes)} nodes")
        
        # Filter by similarity threshold and limit to top_k
        filtered_nodes = [
            node for node in retrieved_nodes
            if node.score >= self.similarity_threshold
        ]
        
        # Explicitly limit to top_k (in case retriever didn't respect it)
        filtered_nodes = filtered_nodes[:top_k]
        
        logger.info(f"[{self.kb_id}] After filtering: {len(filtered_nodes)} nodes")
        
        if not filtered_nodes:
            return {
                'answer': f"No relevant information found in {self.kb_name}.",
                'sources': [],
                'scores': [],
                'has_results': False,
                'kb_id': self.kb_id,
                'kb_name': self.kb_name
            }
        
        # Build context and sources
        context_parts = []
        sources = []
        scores = []
        
        for i, node in enumerate(filtered_nodes, 1):
            context_parts.append(f"[Source {i} - {self.kb_name}]\n{node.text}\n")
            sources.append({
                'url': node.metadata.get('url', ''),
                'title': node.metadata.get('title', ''),
                'section': node.metadata.get('section', ''),
                'score': float(node.score),
                'kb_id': self.kb_id,
                'kb_name': self.kb_name
            })
            scores.append(float(node.score))
        
        context = "\n".join(context_parts)
        
        # Build prompt
        prompt = self._build_prompt(question, context)
        
        # Generate answer
        try:
            llm = Settings.llm
            response = llm.complete(prompt)
            answer = response.text.strip()
            logger.info(f"[{self.kb_id}] Answer generated: {len(answer)} chars")
        except Exception as e:
            logger.error(f"[{self.kb_id}] Generation failed: {e}")
            raise
        
        return {
            'answer': answer,
            'sources': sources,
            'scores': scores,
            'has_results': True,
            'kb_id': self.kb_id,
            'kb_name': self.kb_name
        }
    
    def _build_prompt(self, question: str, context: str) -> str:
        """Build generation prompt with context."""
        return f"""You are an expert assistant for {self.kb_name}.

Use the following context to answer the question. Be specific and cite sources using [Source N].

Context:
{context}

Question: {question}

Answer:"""
    
    def is_index_ready(self) -> bool:
        """Check if index exists and is ready."""
        return os.path.exists(self.storage_dir)


def clear_index_cache(kb_id: Optional[str] = None, storage_dir: Optional[str] = None):
    """
    Clear cached indexes from memory.
    
    Args:
        kb_id: KB ID to clear (optional, for logging)
        storage_dir: Storage directory path to remove from cache
    """
    global _INDEX_CACHE
    
    if storage_dir:
        if storage_dir in _INDEX_CACHE:
            del _INDEX_CACHE[storage_dir]
            logger.info(f"[{kb_id or 'Unknown'}] Cleared index cache for: {storage_dir}")
        else:
            logger.debug(f"[{kb_id or 'Unknown'}] Index not in cache: {storage_dir}")
    else:
        # Clear all cached indexes
        _INDEX_CACHE.clear()
        logger.info("Cleared all index caches")


def get_cached_index_count() -> int:
    """Get number of cached indexes."""
    return len(_INDEX_CACHE)
