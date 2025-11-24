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


class WAFQueryService:
    """Query service for WAF documentation."""
    
    def __init__(
        self,
        storage_dir: str = "waf_storage_clean",
        embedding_model: str = "text-embedding-3-small",
        llm_model: str = "gpt-4o-mini",
        similarity_threshold: float = 0.75
    ):
        """
        Initialize the query service.
        
        Args:
            storage_dir: Directory with persisted index
            embedding_model: OpenAI embedding model name
            llm_model: OpenAI LLM model name (gpt-4o-mini for RAG)
            similarity_threshold: Minimum similarity score for results
        """
        self.storage_dir = storage_dir
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        self.similarity_threshold = similarity_threshold
        
        # Configure LlamaIndex settings
        Settings.embed_model = OpenAIEmbedding(model=embedding_model)
        Settings.llm = OpenAI(model=llm_model)
        
        # Load index (lazy loading, cached after first load)
        self._index = None
        self._query_engine = None
        
        logger.info(f"Query service initialized with LLM: {llm_model}")
    
    def _load_index(self) -> VectorStoreIndex:
        """
        Load index from storage (cached).
        
        Returns:
            VectorStoreIndex
        """
        if self._index is None:
            from llama_index.core import load_index_from_storage
            
            logger.info(f"Loading index from {self.storage_dir}")
            storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
            self._index = load_index_from_storage(storage_context)
            logger.info("Index loaded successfully")
        
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
        top_k: int = 5,
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
        retrieved_nodes = retriever.retrieve(question)
        
        # Filter by similarity threshold
        filtered_nodes = [
            node for node in retrieved_nodes
            if node.score >= self.similarity_threshold
        ]
        
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
            context_parts.append(f"[Source {i}]\n{node.text}\n")
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
        
        # Generate answer using LLM
        llm = Settings.llm
        response = llm.complete(prompt)
        answer = response.text.strip()
        
        logger.info(f"Query completed. Retrieved {len(filtered_nodes)} relevant chunks")
        
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
        prompt = f"""You are an expert on the Azure Well-Architected Framework (WAF). Your role is to provide accurate, helpful answers based on the official WAF documentation.

Instructions:
- Answer the question using ONLY the information provided in the sources below
- Be specific and cite relevant details from the sources
- If the sources don't contain enough information to fully answer the question, acknowledge this
- Provide practical guidance when appropriate
- Structure your answer clearly with sections or bullet points if helpful

Sources:
{context}

Question: {question}

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
    
    # Check if index exists
    storage_dir = "waf_storage_clean"
    if not os.path.exists(storage_dir):
        logger.error(f"Index not found at {storage_dir}")
        logger.info("Please run indexer.py first to build the index")
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
