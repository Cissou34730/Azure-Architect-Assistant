"""
WAF Query Service
Handles retrieval and generation for answering questions about Azure Well-Architected Framework.
"""

import os
import sys
import json
from typing import List, Dict, Optional
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Global cache for loaded indices (singleton pattern)
_INDEX_CACHE = {}


class WAFQueryService:
    """Query service for WAF documentation."""
    
    def __init__(
        self,
        storage_dir: str = None,
        embedding_model: str = "text-embedding-3-small",
        llm_model: str = "gpt-4o-mini",
        similarity_threshold: float = 0.5
    ):
        """
        Initialize the query service.
        
        Args:
            storage_dir: Directory with persisted index (defaults to data/knowledge_bases/waf/index)
            embedding_model: OpenAI embedding model name
            llm_model: OpenAI LLM model name (gpt-4o-mini for RAG)
            similarity_threshold: Minimum similarity score for results (0.5 is reasonable for cosine similarity)
        """
        # Use environment variable if set, otherwise calculate path
        logger.info("[WAFQueryService] Initializing path resolution")
        
        if storage_dir is None:
            storage_dir = os.getenv("WAF_STORAGE_DIR")
            logger.info(f"[WAFQueryService] Environment variable WAF_STORAGE_DIR: {storage_dir}")
            
            if storage_dir is None:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
                storage_dir = os.path.join(project_root, "data", "knowledge_bases", "waf", "index")
                logger.info(f"[WAFQueryService] Calculated path - script_dir: {script_dir}, project_root: {project_root}")
        
        self.storage_dir = os.path.abspath(storage_dir)
        logger.info(f"[WAFQueryService] Final storage_dir: {self.storage_dir}")
        logger.info(f"[WAFQueryService] Directory exists: {os.path.exists(self.storage_dir)}")
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        self.similarity_threshold = similarity_threshold
        
        # Configure LlamaIndex settings
        Settings.embed_model = OpenAIEmbedding(model=embedding_model)
        Settings.llm = OpenAI(
            model=llm_model,
            temperature=0.1,  # More focused responses
            max_tokens=1000,  # Reasonable limit for answers
            timeout=90.0  # 90 second timeout for API call
        )
        
        # Don't load index in __init__, use lazy loading via _load_index()
        self._index = None
        self._query_engine = None
        
        logger.info(f"Query service initialized with LLM: {llm_model}")
    
    def _load_index(self) -> VectorStoreIndex:
        """
        Load index from storage with caching (singleton pattern).
        Significantly reduces query time by avoiding 27s reload on each query.
        
        Returns:
            VectorStoreIndex
        """
        # Check global cache first
        cache_key = self.storage_dir
        if cache_key in _INDEX_CACHE:
            logger.info(f"[WAFQueryService] Using cached index from {self.storage_dir}")
            return _INDEX_CACHE[cache_key]
        
        # Load from disk if not cached
        from llama_index.core import load_index_from_storage
        
        logger.info(f"[WAFQueryService] Loading index from {self.storage_dir} (first time - will be cached)")
        
        # Check if directory exists
        if not os.path.exists(self.storage_dir):
            logger.error(f"[WAFQueryService] Index directory not found: {self.storage_dir}")
            logger.error(f"[WAFQueryService] Directory contents of parent: {os.listdir(os.path.dirname(self.storage_dir)) if os.path.exists(os.path.dirname(self.storage_dir)) else 'Parent does not exist'}")
            raise FileNotFoundError(f"WAF index not found at {self.storage_dir}. Please run the ingestion pipeline first.")
        
        # List files in the directory
        index_files = os.listdir(self.storage_dir)
        logger.info(f"[WAFQueryService] Index directory contains {len(index_files)} files: {index_files[:5]}...")
        
        storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
        index = load_index_from_storage(storage_context)
        
        # Cache globally for reuse across instances
        _INDEX_CACHE[cache_key] = index
        
        logger.info("[WAFQueryService] Index loaded successfully and cached")
        
        return _INDEX_CACHE[cache_key]
    
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
        top_k: int = 3,  # Reduced from 5 to 3 for faster responses
        metadata_filters: Optional[Dict[str, any]] = None
    ) -> Dict[str, any]:
        """
        Query the WAF documentation.
        
        Args:
            question: User question
            top_k: Number of top chunks to retrieve
            metadata_filters: Optional metadata filters (e.g., {"section": "pillar"})
            
        Returns:
            Dictionary with answer, sources, and scores
        """
        logger.info(f"Processing query: {question}")
        
        import time
        total_start = time.time()
        
        # Load index and get retriever
        index_start = time.time()
        index = self._load_index()
        index_time = time.time() - index_start
        logger.info(f"[query] Index load time: {index_time:.2f}s")
        
        retriever_start = time.time()
        retriever = index.as_retriever(similarity_top_k=top_k)
        retriever_time = time.time() - retriever_start
        logger.info(f"[query] Retriever creation time: {retriever_time:.2f}s")
        
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
        
        logger.info(f"[query] Retrieved {len(retrieved_nodes)} nodes in {retrieve_time:.2f}s")
        for i, node in enumerate(retrieved_nodes[:3], 1):
            logger.info(f"[query] Node {i}: score={node.score:.4f}, title={node.metadata.get('title', 'N/A')[:50]}")
        
        # Filter by similarity threshold
        filtered_nodes = [
            node for node in retrieved_nodes
            if node.score >= self.similarity_threshold
        ]
        
        logger.info(f"[query] After filtering (threshold={self.similarity_threshold}): {len(filtered_nodes)} nodes")
        
        if not filtered_nodes:
            return {
                'answer': "I couldn't find relevant information in the Azure Well-Architected Framework documentation to answer your question. Please try rephrasing or asking a different question.",
                'sources': [],
                'scores': [],
                'has_results': False
            }
        
        # Build context from retrieved chunks
        context_parts = []
        sources = []
        scores = []
        
        for i, node in enumerate(filtered_nodes, 1):
            chunk_text = node.text
            logger.info(f"[query] Chunk {i} length: {len(chunk_text)} chars")
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
        
        logger.info(f"[query] Total prompt length: {len(prompt)} chars (~{len(prompt)//4} tokens)")
        logger.info(f"[query] Generating answer with LLM (model: {self.llm_model})")
        
        # Generate answer using LLM
        try:
            import time
            start_time = time.time()
            
            llm = Settings.llm
            response = llm.complete(prompt)
            answer = response.text.strip()
            
            elapsed_time = time.time() - start_time
            logger.info(f"[query] LLM response received in {elapsed_time:.2f}s, length: {len(answer)} chars")
        except Exception as e:
            logger.error(f"[query] LLM generation failed: {str(e)}")
            raise
        
        total_time = time.time() - total_start
        logger.info(f"Query completed in {total_time:.2f}s total. Retrieved {len(filtered_nodes)} relevant chunks")
        
        return {
            'answer': answer,
            'sources': sources,
            'scores': scores,
            'has_results': True
        }
    
    def _build_prompt(self, question: str, context: str) -> str:
        """
        Build generation prompt.
        
        Args:
            question: User question
            context: Retrieved context
            
        Returns:
            Formatted prompt
        """
        prompt = f"""You are an Azure Well-Architected Framework expert. Answer the question using ONLY the provided sources.

Sources:
{context}

Question: {question}

Provide a clear, concise answer with specific details from the sources. If the sources lack information, state this clearly.

Answer:"""
        
        return prompt
    
    def query_with_discussion(
        self,
        question: str,
        top_k: int = 5,
        metadata_filters: Optional[Dict[str, any]] = None
    ) -> Dict[str, any]:
        """
        Query that combines documentation retrieval with discussion capability.
        
        Args:
            question: User question
            top_k: Number of top chunks to retrieve
            metadata_filters: Optional metadata filters
            
        Returns:
            Dictionary with answer, sources, scores, and discussion points
        """
        # Get base query response
        response = self.query(question, top_k, metadata_filters)
        
        if not response['has_results']:
            return response
        
        # Add discussion capability
        # This could be extended to include follow-up questions, clarifications, etc.
        response['discussion_enabled'] = True
        response['suggested_follow_ups'] = self._generate_follow_up_questions(question, response['answer'])
        
        return response
    
    def query_stream(
        self,
        question: str,
        top_k: int = 3,
        metadata_filters: Optional[Dict[str, any]] = None
    ):
        """
        Query with streaming response (yields chunks as they arrive).
        
        Args:
            question: User question
            top_k: Number of top chunks to retrieve
            metadata_filters: Optional metadata filters
            
        Yields:
            Answer chunks as they are generated
        """
        logger.info(f"Processing streaming query: {question}")
        
        # Load index and get retriever
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
        import time
        retrieve_start = time.time()
        retrieved_nodes = retriever.retrieve(question)
        retrieve_time = time.time() - retrieve_start
        
        logger.info(f"[query_stream] Retrieved {len(retrieved_nodes)} nodes in {retrieve_time:.2f}s")
        
        # Filter by similarity threshold
        filtered_nodes = [
            node for node in retrieved_nodes
            if node.score >= self.similarity_threshold
        ]
        
        logger.info(f"[query_stream] After filtering: {len(filtered_nodes)} nodes")
        
        if not filtered_nodes:
            yield {
                'type': 'answer',
                'content': "I couldn't find relevant information in the Azure Well-Architected Framework documentation to answer your question. Please try rephrasing or asking a different question.",
                'done': True,
                'sources': [],
                'scores': []
            }
            return
        
        # Build context
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
        prompt = self._build_prompt(question, context)
        
        logger.info(f"[query_stream] Starting streaming generation")
        
        # Stream response
        llm = Settings.llm
        response_gen = llm.stream_complete(prompt)
        
        for chunk in response_gen:
            yield {
                'type': 'chunk',
                'content': chunk.delta,
                'done': False
            }
        
        # Send final metadata
        yield {
            'type': 'complete',
            'done': True,
            'sources': sources,
            'scores': scores
        }

    def _generate_follow_up_questions(self, original_question: str, answer: str) -> List[str]:
        """
        Generate follow-up questions based on the answer.
        
        Args:
            original_question: Original user question
            answer: Generated answer
            
        Returns:
            List of suggested follow-up questions
        """
        # Simple implementation - could be enhanced with LLM generation
        follow_ups = [
            "Can you provide more details about implementation best practices?",
            "What are common pitfalls to avoid?",
            "How does this relate to other WAF pillars?"
        ]
        
        return follow_ups[:3]


def main():
    """Main entry point for query service (CLI interface)."""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY not found in environment")
        return
    
    # Default storage path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
    storage_dir = os.path.abspath(os.path.join(project_root, "data", "knowledge_bases", "waf", "index"))
    
    logger.info(f"Looking for index at: {storage_dir}")
    
    # Check if index exists
    if not os.path.exists(storage_dir):
        logger.error(f"Index not found at {storage_dir}")
        logger.info("Please run scripts/ingest/waf_phase2.py first to build the index")
        return
    
    # Initialize service
    service = WAFQueryService(
        storage_dir=storage_dir,
        embedding_model="text-embedding-3-small",
        llm_model="gpt-4-turbo-preview",
        similarity_threshold=0.75
    )
    
    # CLI mode
    if len(sys.argv) > 1:
        # Single query from command line
        question = " ".join(sys.argv[1:])
        result = service.query_with_discussion(question)
        
        print(f"\n{'='*80}")
        print(f"Question: {question}")
        print(f"{'='*80}\n")
        print(f"Answer:\n{result['answer']}\n")
        
        if result.get('sources'):
            print(f"\nSources:")
            for i, source in enumerate(result['sources'], 1):
                print(f"  {i}. {source['title']} (score: {source['score']:.3f})")
                print(f"     {source['url']}")
        
        if result.get('suggested_follow_ups'):
            print(f"\nSuggested follow-up questions:")
            for q in result['suggested_follow_ups']:
                print(f"  - {q}")
    else:
        # Interactive mode
        print("WAF Query Service - Interactive Mode")
        print("Type 'exit' or 'quit' to end session\n")
        
        while True:
            question = input("Ask a question about Azure Well-Architected Framework: ").strip()
            
            if question.lower() in ['exit', 'quit', 'q']:
                break
            
            if not question:
                continue
            
            result = service.query_with_discussion(question)
            
            print(f"\n{'-'*80}")
            print(f"Answer:\n{result['answer']}\n")
            
            if result.get('sources'):
                print(f"Sources:")
                for i, source in enumerate(result['sources'], 1):
                    print(f"  {i}. {source['title']} (score: {source['score']:.3f})")
            
            print(f"{'-'*80}\n")


if __name__ == "__main__":
    main()
