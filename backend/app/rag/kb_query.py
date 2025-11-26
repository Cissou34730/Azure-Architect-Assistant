"""
Generic Knowledge Base Query Service
Handles retrieval and generation for answering questions from any knowledge base.
"""

import os
import logging
from typing import List, Dict, Optional
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class KnowledgeBaseQueryService:
    """Generic query service for any knowledge base."""
    
    def __init__(
        self,
        kb_id: str,
        storage_dir: str,
        embedding_model: str = "text-embedding-3-small",
        llm_model: str = "gpt-4o-mini",
        similarity_threshold: float = 0.5,
        preload: bool = True
    ):
        """
        Initialize the query service.
        
        Args:
            kb_id: Knowledge base identifier (e.g., 'waf', 'azure-docs')
            storage_dir: Directory with persisted index
            embedding_model: OpenAI embedding model name
            llm_model: OpenAI LLM model name (gpt-4o-mini for RAG)
            similarity_threshold: Minimum similarity score for results (0.5 is reasonable)
            preload: Whether to preload the index at initialization (True for production)
        """
        self.kb_id = kb_id
        self.storage_dir = os.path.abspath(storage_dir)
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        self.similarity_threshold = similarity_threshold
        
        logger.info(f"[{kb_id}] Initializing KnowledgeBaseQueryService")
        logger.info(f"[{kb_id}] Storage directory: {self.storage_dir}")
        logger.info(f"[{kb_id}] Directory exists: {os.path.exists(self.storage_dir)}")
        
        # Configure LlamaIndex settings
        Settings.embed_model = OpenAIEmbedding(model=embedding_model)
        Settings.llm = OpenAI(
            model=llm_model,
            temperature=0.1,  # More focused responses
            max_tokens=1000,  # Reasonable limit for answers
            timeout=90.0  # 90 second timeout for API call
        )
        
        # Index and query engine (lazy loaded or preloaded)
        self._index: Optional[VectorStoreIndex] = None
        self._query_engine = None
        
        # Preload index if requested
        if preload:
            logger.info(f"[{kb_id}] Preloading index at startup...")
            self._load_index()
            logger.info(f"[{kb_id}] Index preloaded successfully")
        else:
            logger.info(f"[{kb_id}] Index will be lazy-loaded on first query")
        
        logger.info(f"[{kb_id}] Query service initialized with LLM: {llm_model}")
    
    def _load_index(self) -> VectorStoreIndex:
        """
        Load index from storage (singleton pattern per instance).
        
        Returns:
            VectorStoreIndex
        """
        # Return cached index if already loaded
        if self._index is not None:
            logger.debug(f"[{self.kb_id}] Using cached index")
            return self._index
        
        # Load from disk
        from llama_index.core import load_index_from_storage
        
        logger.info(f"[{self.kb_id}] Loading index from {self.storage_dir}")
        
        # Verify directory exists
        if not os.path.exists(self.storage_dir):
            logger.error(f"[{self.kb_id}] Index directory not found: {self.storage_dir}")
            raise FileNotFoundError(
                f"Knowledge base '{self.kb_id}' index not found at {self.storage_dir}. "
                "Please run the ingestion pipeline first."
            )
        
        # List files in the directory
        index_files = os.listdir(self.storage_dir)
        logger.info(f"[{self.kb_id}] Index directory contains {len(index_files)} files")
        
        # Load index
        storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
        self._index = load_index_from_storage(storage_context)
        
        logger.info(f"[{self.kb_id}] Index loaded successfully")
        
        return self._index
    
    def _get_query_engine(self):
        """
        Get or create query engine.
        
        Returns:
            Query engine
        """
        if self._query_engine is None:
            index = self._load_index()
            self._query_engine = index.as_query_engine(
                similarity_top_k=5,
                response_mode="tree_summarize"
            )
        
        return self._query_engine
    
    def query(
        self,
        question: str,
        top_k: int = 3,
        metadata_filters: Optional[Dict[str, any]] = None,
        return_raw_nodes: bool = False
    ) -> Dict[str, any]:
        """
        Query the knowledge base.
        
        Args:
            question: User question
            top_k: Number of top chunks to retrieve
            metadata_filters: Optional metadata filters (e.g., {"section": "security"})
            return_raw_nodes: If True, return raw nodes instead of generating answer
            
        Returns:
            Dictionary with answer, sources, and scores
        """
        logger.info(f"[{self.kb_id}] Processing query: {question[:100]}...")
        
        import time
        total_start = time.time()
        
        # Get index and retriever
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
            retriever = index.as_retriever(
                similarity_top_k=top_k,
                filters=filters
            )
        
        # Retrieve relevant chunks
        retrieve_start = time.time()
        retrieved_nodes = retriever.retrieve(question)
        retrieve_time = time.time() - retrieve_start
        
        logger.info(f"[{self.kb_id}] Retrieved {len(retrieved_nodes)} nodes in {retrieve_time:.2f}s")
        
        # Filter by similarity threshold
        filtered_nodes = [
            node for node in retrieved_nodes
            if node.score >= self.similarity_threshold
        ]
        
        logger.info(f"[{self.kb_id}] After filtering (threshold={self.similarity_threshold}): {len(filtered_nodes)} nodes")
        
        if not filtered_nodes:
            return {
                'answer': f"I couldn't find relevant information in the {self.kb_id} knowledge base to answer your question. Please try rephrasing or asking a different question.",
                'sources': [],
                'scores': [],
                'has_results': False
            }
        
        # If raw nodes requested, return them
        if return_raw_nodes:
            return {
                'nodes': filtered_nodes,
                'has_results': True
            }
        
        # Build context from retrieved chunks
        context_parts = []
        sources = []
        scores = []
        
        for i, node in enumerate(filtered_nodes, 1):
            chunk_text = node.text
            context_parts.append(f"[Source {i}]\n{chunk_text}\n")
            sources.append({
                'url': node.metadata.get('url', ''),
                'title': node.metadata.get('title', ''),
                'section': node.metadata.get('section', ''),
                'score': float(node.score)
            })
            scores.append(float(node.score))
        
        context = "\n".join(context_parts)
        
        # Build generation prompt
        prompt = self._build_prompt(question, context)
        
        logger.info(f"[{self.kb_id}] Generating answer with LLM (model: {self.llm_model})")
        
        # Generate answer using LLM
        try:
            llm = Settings.llm
            response = llm.complete(prompt)
            answer = response.text.strip()
            
            logger.info(f"[{self.kb_id}] LLM response generated, length: {len(answer)} chars")
        except Exception as e:
            logger.error(f"[{self.kb_id}] LLM generation failed: {str(e)}")
            raise
        
        total_time = time.time() - total_start
        logger.info(f"[{self.kb_id}] Query completed in {total_time:.2f}s total")
        
        return {
            'answer': answer,
            'sources': sources,
            'scores': scores,
            'has_results': True,
            'query_time': total_time
        }
    
    def _build_prompt(self, question: str, context: str) -> str:
        """
        Build prompt for LLM generation.
        
        Args:
            question: User question
            context: Retrieved context chunks
            
        Returns:
            Formatted prompt
        """
        return f"""You are a helpful AI assistant that answers questions based on the provided context from the {self.kb_id} knowledge base.

Context from knowledge base:
{context}

Question: {question}

Instructions:
- Answer the question based ONLY on the provided context
- Be concise and specific
- If the context doesn't contain enough information to answer fully, say so
- Cite source numbers [Source N] when relevant
- Use technical terminology appropriately

Answer:"""


# Legacy alias for backward compatibility
class WAFQueryService(KnowledgeBaseQueryService):
    """
    Legacy WAF-specific query service.
    Maintained for backward compatibility.
    """
    
    def __init__(
        self,
        storage_dir: str = None,
        embedding_model: str = "text-embedding-3-small",
        llm_model: str = "gpt-4o-mini",
        similarity_threshold: float = 0.5
    ):
        """Initialize WAF query service with legacy interface."""
        if storage_dir is None:
            storage_dir = os.getenv("WAF_STORAGE_DIR")
            
            if storage_dir is None:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                backend_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
                storage_dir = os.path.join(backend_root, "data", "knowledge_bases", "waf", "index")
        
        super().__init__(
            kb_id="waf",
            storage_dir=storage_dir,
            embedding_model=embedding_model,
            llm_model=llm_model,
            similarity_threshold=similarity_threshold,
            preload=True  # Preload for backward compatibility
        )
