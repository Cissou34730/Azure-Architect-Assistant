"""
Vector Index Builder
Creates and persists vector index using LlamaIndex and OpenAI embeddings.
"""

import os
import json
from typing import List, Dict
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.schema import Document, TextNode
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class WAFIndexer:
    """Builds and persists vector index for WAF documentation."""
    
    def __init__(
        self,
        storage_dir: str = "waf_storage_clean",
        embedding_model: str = "text-embedding-3-small",
        llm_model: str = "gpt-4-turbo-preview"
    ):
        """
        Initialize the indexer.
        
        Args:
            storage_dir: Directory for persistent storage
            embedding_model: OpenAI embedding model name
            llm_model: OpenAI LLM model name
        """
        self.storage_dir = storage_dir
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        
        # Configure LlamaIndex settings
        Settings.embed_model = OpenAIEmbedding(model=embedding_model)
        Settings.llm = OpenAI(model=llm_model)
        
        # Ensure storage directory exists
        os.makedirs(storage_dir, exist_ok=True)
        
        logger.info(f"Indexer initialized with embedding model: {embedding_model}")
        logger.info(f"Storage directory: {storage_dir}")
    
    def load_validated_chunks(self, chunks_file: str) -> List[Dict[str, any]]:
        """
        Load validated chunks from JSONL file.
        
        Args:
            chunks_file: Path to chunks JSONL file
            
        Returns:
            List of chunks marked as KEEP
        """
        chunks = []
        
        with open(chunks_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    chunk = json.loads(line)
                    if chunk.get('status', '').upper() == 'KEEP':
                        chunks.append(chunk)
        
        logger.info(f"Loaded {len(chunks)} validated chunks")
        return chunks
    
    def create_nodes_from_chunks(self, chunks: List[Dict[str, any]]) -> List[TextNode]:
        """
        Convert chunks to LlamaIndex TextNodes.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            List of TextNode objects
        """
        nodes = []
        
        for chunk in chunks:
            node = TextNode(
                text=chunk['text'],
                id_=chunk['chunk_id'],
                metadata={
                    'url': chunk['url'],
                    'title': chunk['title'],
                    'section': chunk['section'],
                    'chunk_index': int(chunk['chunk_index'])
                }
            )
            nodes.append(node)
        
        logger.info(f"Created {len(nodes)} TextNodes")
        return nodes
    
    def build_index(self, nodes: List[TextNode]) -> VectorStoreIndex:
        """
        Build vector index from nodes.
        
        Args:
            nodes: List of TextNode objects
            
        Returns:
            VectorStoreIndex
        """
        logger.info("Building vector index (this may take a while)...")
        
        # Create index
        index = VectorStoreIndex(
            nodes=nodes,
            show_progress=True
        )
        
        logger.info("Vector index built successfully")
        return index
    
    def persist_index(self, index: VectorStoreIndex):
        """
        Persist index to storage.
        
        Args:
            index: VectorStoreIndex to persist
        """
        logger.info(f"Persisting index to {self.storage_dir}")
        index.storage_context.persist(persist_dir=self.storage_dir)
        logger.info("Index persisted successfully")
    
    def load_index(self) -> VectorStoreIndex:
        """
        Load index from storage.
        
        Returns:
            VectorStoreIndex loaded from storage
        """
        from llama_index.core import load_index_from_storage
        
        logger.info(f"Loading index from {self.storage_dir}")
        storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
        index = load_index_from_storage(storage_context)
        logger.info("Index loaded successfully")
        return index
    
    def build_and_persist(self, chunks_file: str):
        """
        Complete workflow: load chunks, build index, persist.
        
        Args:
            chunks_file: Path to validated chunks file
        """
        # Load chunks
        chunks = self.load_validated_chunks(chunks_file)
        
        if not chunks:
            logger.error("No validated chunks found. Please validate chunks first.")
            return
        
        # Create nodes
        nodes = self.create_nodes_from_chunks(chunks)
        
        # Build index
        index = self.build_index(nodes)
        
        # Persist
        self.persist_index(index)
        
        print(f"\nIndexing Summary:")
        print(f"Total chunks indexed: {len(chunks)}")
        print(f"Storage location: {self.storage_dir}")
        print(f"Embedding model: {self.embedding_model}")
        print(f"\nIndex is ready for querying!")


def main():
    """Main entry point for indexing."""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY not found in environment")
        logger.info("Please set OPENAI_API_KEY in .env file")
        return
    
    indexer = WAFIndexer(
        storage_dir="waf_storage_clean",
        embedding_model="text-embedding-3-small",
        llm_model="gpt-4-turbo-preview"
    )
    
    # Check for chunks file
    chunks_file = "chunks_review.jsonl"
    if not os.path.exists(chunks_file):
        logger.error(f"Chunks file not found: {chunks_file}")
        logger.info("Please run chunker.py and validate chunks first")
        
        # For development: try auto-validating
        logger.info("\nAttempting to auto-validate all chunks...")
        from chunker import ChunkValidator
        
        validator = ChunkValidator()
        if os.path.exists("waf_documents.jsonl"):
            documents = validator.load_documents("waf_documents.jsonl")
            chunks = validator.chunk_all_documents(documents)
            chunks = validator.auto_validate_all(chunks)
            
            # Save auto-validated chunks
            with open(chunks_file, 'w', encoding='utf-8') as f:
                for chunk in chunks:
                    f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
            
            logger.info(f"Auto-validated chunks saved to {chunks_file}")
        else:
            logger.error("No documents file found. Please run crawler.py and ingestion.py first")
            return
    
    # Build and persist index
    indexer.build_and_persist(chunks_file)


if __name__ == "__main__":
    main()
