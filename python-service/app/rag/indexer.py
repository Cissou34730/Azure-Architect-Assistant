"""
WAF Documentation Index Builder - Phase 2
Loads APPROVED documents, chunks them, generates embeddings, and builds vector index.
Only runs after manual validation of cleaned documents.
"""

import os
import json
import logging
from typing import List, Dict
from dotenv import load_dotenv
from llama_index.core import Document, VectorStoreIndex, StorageContext
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WAFIndexBuilder:
    """Builds vector index from approved documents."""
    
    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
        storage_dir: str = "waf_storage_clean"
    ):
        """
        Initialize the index builder.
        
        Args:
            chunk_size: Target chunk size in tokens
            chunk_overlap: Overlap between chunks in tokens
            storage_dir: Directory to persist the index
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.storage_dir = storage_dir
        
        # Initialize text splitter
        self.text_splitter = TokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # Initialize embedding model
        self.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
        
        logger.info(f"Initialized IndexBuilder with chunk_size={chunk_size}, overlap={chunk_overlap}")
    
    def load_approved_documents(self, manifest_file: str = "validation_manifest.json") -> List[Dict]:
        """
        Load documents marked as APPROVED from manifest.
        
        Args:
            manifest_file: Path to validation manifest
            
        Returns:
            List of approved document metadata
        """
        if not os.path.exists(manifest_file):
            raise FileNotFoundError(f"Manifest not found: {manifest_file}")
        
        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        # Filter for approved documents
        approved = [doc for doc in manifest if doc['status'] == 'APPROVED']
        
        logger.info(f"Loaded {len(approved)} APPROVED documents from {len(manifest)} total")
        
        if len(approved) == 0:
            raise ValueError("No APPROVED documents found. Please validate documents first.")
        
        return approved
    
    def read_document_content(self, file_path: str) -> str:
        """
        Read cleaned document content from file.
        
        Args:
            file_path: Path to .md file
            
        Returns:
            Document text content
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove metadata header (everything before ---)
        if '---' in content:
            parts = content.split('---', 1)
            if len(parts) > 1:
                content = parts[1].strip()
        
        return content
    
    def build_llama_documents(self, approved_docs: List[Dict]) -> List[Document]:
        """
        Build LlamaIndex Document objects from approved documents.
        
        Args:
            approved_docs: List of approved document metadata
            
        Returns:
            List of LlamaIndex Document objects
        """
        documents = []
        
        for doc_meta in approved_docs:
            # Read content
            content = self.read_document_content(doc_meta['file_path'])
            
            # Create LlamaIndex Document
            doc = Document(
                text=content,
                metadata={
                    'document_id': doc_meta['document_id'],
                    'url': doc_meta['url'],
                    'title': doc_meta['title'],
                    'section': doc_meta['section']
                },
                id_=doc_meta['document_id']
            )
            
            documents.append(doc)
            logger.info(f"Loaded: {doc_meta['title']}")
        
        return documents
    
    def build_index(self, manifest_file: str = "validation_manifest.json"):
        """
        Build vector index from approved documents.
        
        Args:
            manifest_file: Path to validation manifest
        """
        logger.info("="*70)
        logger.info("PHASE 2: Building Vector Index from Approved Documents")
        logger.info("="*70)
        
        # Load approved documents
        approved_docs = self.load_approved_documents(manifest_file)
        
        logger.info(f"\nApproved documents by section:")
        sections = {}
        for doc in approved_docs:
            sections[doc['section']] = sections.get(doc['section'], 0) + 1
        for section, count in sections.items():
            logger.info(f"  {section}: {count}")
        
        # Build LlamaIndex documents
        logger.info("\nLoading document content...")
        documents = self.build_llama_documents(approved_docs)
        
        # Chunk documents
        logger.info(f"\nChunking {len(documents)} documents...")
        nodes = self.text_splitter.get_nodes_from_documents(documents)
        logger.info(f"Created {len(nodes)} chunks")
        
        # Build index with embeddings
        logger.info("\nGenerating embeddings and building index...")
        logger.info("(This may take several minutes depending on document count)")
        
        index = VectorStoreIndex(
            nodes=nodes,
            embed_model=self.embed_model,
            show_progress=True
        )
        
        # Persist index
        logger.info(f"\nPersisting index to {self.storage_dir}/")
        index.storage_context.persist(persist_dir=self.storage_dir)
        
        # Save build metadata
        build_info = {
            'total_documents': len(documents),
            'total_chunks': len(nodes),
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'embedding_model': 'text-embedding-3-small',
            'sections': sections
        }
        
        with open(os.path.join(self.storage_dir, 'build_info.json'), 'w') as f:
            json.dump(build_info, f, indent=2)
        
        logger.info("\n" + "="*70)
        logger.info("INDEX BUILD COMPLETE")
        logger.info("="*70)
        logger.info(f"Documents indexed: {len(documents)}")
        logger.info(f"Total chunks: {len(nodes)}")
        logger.info(f"Storage location: {self.storage_dir}/")
        logger.info("\nThe index is ready for queries!")
        logger.info("="*70 + "\n")


def main():
    """Main entry point for Phase 2 index building."""
    
    # Check if manifest exists
    manifest_file = "validation_manifest.json"
    if not os.path.exists(manifest_file):
        print(f"ERROR: {manifest_file} not found!")
        print("Please run Phase 1 (ingestion.py) first.")
        return
    
    # Load manifest to check for approved docs
    with open(manifest_file, 'r') as f:
        manifest = json.load(f)
    
    approved_count = sum(1 for doc in manifest if doc['status'] == 'APPROVED')
    pending_count = sum(1 for doc in manifest if doc['status'] == 'PENDING_REVIEW')
    rejected_count = sum(1 for doc in manifest if doc['status'] == 'REJECTED')
    
    print("\nValidation Status:")
    print(f"  APPROVED: {approved_count}")
    print(f"  PENDING_REVIEW: {pending_count}")
    print(f"  REJECTED: {rejected_count}")
    
    if approved_count == 0:
        print("\nERROR: No APPROVED documents found!")
        print(f"Please edit {manifest_file} and set status to 'APPROVED' for documents to index.")
        return
    
    if pending_count > 0:
        print(f"\nWARNING: {pending_count} documents still PENDING_REVIEW")
        response = input("Continue with only APPROVED documents? (y/n): ")
        if response.lower() != 'y':
            print("Aborted. Please complete validation first.")
            return
    
    # Build index
    builder = WAFIndexBuilder(
        chunk_size=800,
        chunk_overlap=120,
        storage_dir="waf_storage_clean"
    )
    
    builder.build_index(manifest_file)


if __name__ == "__main__":
    main()
