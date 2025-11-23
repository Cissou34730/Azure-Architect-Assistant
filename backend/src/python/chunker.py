"""
Chunking and Validation System
Handles document chunking and exports chunks for manual validation.
"""

import os
import json
import csv
from typing import List, Dict
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.core.schema import Document
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChunkValidator:
    """Handles chunking and validation workflow."""
    
    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 120
    ):
        """
        Initialize the chunk validator.
        
        Args:
            chunk_size: Target chunk size in tokens
            chunk_overlap: Overlap between chunks in tokens
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = TokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    
    def load_documents(self, documents_file: str) -> List[Dict[str, any]]:
        """
        Load documents from JSONL file.
        
        Args:
            documents_file: Path to JSONL file
            
        Returns:
            List of documents
        """
        documents = []
        with open(documents_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    documents.append(json.loads(line))
        logger.info(f"Loaded {len(documents)} documents")
        return documents
    
    def chunk_document(self, doc: Dict[str, any]) -> List[Dict[str, any]]:
        """
        Chunk a single document.
        
        Args:
            doc: Document dictionary
            
        Returns:
            List of chunk dictionaries
        """
        # Create LlamaIndex Document
        llama_doc = Document(
            text=doc['content'],
            metadata={
                'url': doc['url'],
                'title': doc['title'],
                'section': doc['section']
            }
        )
        
        # Split into chunks
        nodes = self.text_splitter.get_nodes_from_documents([llama_doc])
        
        # Convert to dictionaries
        chunks = []
        for i, node in enumerate(nodes):
            chunks.append({
                'chunk_id': f"{doc['url']}#chunk_{i}",
                'url': doc['url'],
                'title': doc['title'],
                'section': doc['section'],
                'chunk_index': i,
                'text': node.text,
                'token_count': len(node.text.split()),  # Rough estimate
                'status': 'PENDING'  # PENDING, KEEP, DROP
            })
        
        return chunks
    
    def chunk_all_documents(self, documents: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """
        Chunk all documents.
        
        Args:
            documents: List of document dictionaries
            
        Returns:
            List of all chunks
        """
        all_chunks = []
        
        for i, doc in enumerate(documents, 1):
            logger.info(f"[{i}/{len(documents)}] Chunking: {doc['title']}")
            chunks = self.chunk_document(doc)
            all_chunks.extend(chunks)
        
        logger.info(f"Created {len(all_chunks)} chunks from {len(documents)} documents")
        return all_chunks
    
    def export_for_validation(
        self,
        chunks: List[Dict[str, any]],
        output_csv: str = "chunks_review.csv",
        output_jsonl: str = "chunks_review.jsonl"
    ):
        """
        Export chunks to CSV and JSONL for manual validation.
        
        Args:
            chunks: List of chunk dictionaries
            output_csv: Output CSV file path
            output_jsonl: Output JSONL file path
        """
        # Export to CSV
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['chunk_id', 'url', 'title', 'section', 'chunk_index', 'token_count', 'status', 'text']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(chunks)
        
        logger.info(f"Exported chunks to CSV: {output_csv}")
        
        # Export to JSONL (easier for programmatic processing)
        with open(output_jsonl, 'w', encoding='utf-8') as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
        
        logger.info(f"Exported chunks to JSONL: {output_jsonl}")
        
        print(f"\nValidation files created:")
        print(f"  CSV:   {output_csv}")
        print(f"  JSONL: {output_jsonl}")
        print(f"\nInstructions:")
        print(f"  1. Open {output_csv} in Excel or a text editor")
        print(f"  2. Review each chunk's text")
        print(f"  3. Set status to 'KEEP' or 'DROP' for each chunk")
        print(f"  4. Save the file")
        print(f"  5. Run indexer.py to build the vector index from validated chunks")
    
    def load_validated_chunks(self, validated_csv: str) -> List[Dict[str, any]]:
        """
        Load chunks that have been validated (marked as KEEP).
        
        Args:
            validated_csv: Path to validated CSV file
            
        Returns:
            List of chunks marked as KEEP
        """
        validated_chunks = []
        
        with open(validated_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['status'].upper() == 'KEEP':
                    validated_chunks.append(row)
        
        logger.info(f"Loaded {len(validated_chunks)} validated chunks (KEEP)")
        return validated_chunks
    
    def auto_validate_all(self, chunks: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """
        Auto-validate all chunks as KEEP (for testing/development).
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            List of chunks with status set to KEEP
        """
        for chunk in chunks:
            chunk['status'] = 'KEEP'
        
        logger.info(f"Auto-validated all {len(chunks)} chunks as KEEP")
        return chunks


def main():
    """Main entry point for chunking and validation."""
    validator = ChunkValidator(chunk_size=800, chunk_overlap=120)
    
    # Load documents
    documents_file = "waf_documents.jsonl"
    if not os.path.exists(documents_file):
        logger.error(f"Documents file not found: {documents_file}")
        logger.info("Please run ingestion.py first")
        return
    
    documents = validator.load_documents(documents_file)
    
    # Chunk documents
    chunks = validator.chunk_all_documents(documents)
    
    # Export for validation
    validator.export_for_validation(chunks)
    
    print(f"\nChunking Summary:")
    print(f"Total chunks created: {len(chunks)}")
    print(f"Average chunks per document: {len(chunks) / len(documents):.1f}")


if __name__ == "__main__":
    main()
