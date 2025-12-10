"""
Chunking Adapter
Adapts existing chunker implementations to produce Chunk dataclass with content_hash.
"""

import hashlib
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from llama_index.core import Document

from .factory import ChunkerFactory

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """
    Chunk dataclass for orchestrator pipeline.
    
    Attributes:
        text: Chunk content text
        content_hash: SHA256 hash for idempotency
        metadata: Source metadata and context
    """
    text: str
    content_hash: str
    metadata: Dict[str, Any]


def compute_content_hash(text: str, kb_id: str, source_id: str) -> str:
    """
    Compute deterministic content hash for chunk.
    
    Args:
        text: Normalized chunk text
        kb_id: Knowledge base identifier
        source_id: Source document identifier
        
    Returns:
        SHA256 hex digest
    """
    # Normalize text: strip whitespace, lowercase
    normalized = text.strip().lower()
    
    # Create composite key
    composite = f"{kb_id}::{source_id}::{normalized}"
    
    # Compute hash
    return hashlib.sha256(composite.encode('utf-8')).hexdigest()


def create_chunker_from_config(kb_config: Dict[str, Any]):
    """
    Create chunker instance from KB configuration.
    
    Args:
        kb_config: Knowledge base config with optional chunking params
        
    Returns:
        Configured chunker instance
    """
    chunking_config = kb_config.get('chunking', {})
    strategy = chunking_config.get('strategy', 'semantic')
    chunk_size = chunking_config.get('chunk_size', 1024)
    chunk_overlap = chunking_config.get('chunk_overlap', 200)
    
    logger.info(f"Creating chunker: strategy={strategy}, size={chunk_size}, overlap={chunk_overlap}")
    
    return ChunkerFactory.create_chunker(
        strategy=strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )


def chunk_documents_to_chunks(
    documents: List[Document],
    chunker,
    kb_id: str
) -> List[Chunk]:
    """
    Chunk documents and produce Chunk dataclass instances with content_hash.
    
    Args:
        documents: List of LlamaIndex Documents
        chunker: Chunker instance from ChunkerFactory
        kb_id: Knowledge base identifier for hash computation
        
    Returns:
        List of Chunk instances with computed content_hash
    """
    if not documents:
        return []
    
    logger.info(f"Chunking {len(documents)} documents")
    
    # Use existing chunker to process documents
    # Chunkers return list of dicts with 'content' and 'metadata'
    chunk_dicts = chunker.chunk_documents(documents)
    
    # Convert to Chunk dataclass with content_hash
    chunks = []
    for i, chunk_dict in enumerate(chunk_dicts):
        content = chunk_dict.get('content', '')
        metadata = chunk_dict.get('metadata', {})
        
        if not content or not content.strip():
            logger.warning(f"Skipping empty chunk {i}")
            continue
        
        # Extract source identifiers for hash
        source_id = (
            metadata.get('url') or
            metadata.get('file_path') or
            metadata.get('source') or
            f"doc_{metadata.get('doc_id', i)}"
        )
        
        # Compute content hash
        content_hash = compute_content_hash(
            text=content,
            kb_id=kb_id,
            source_id=source_id
        )
        
        # Enrich metadata
        metadata['kb_id'] = kb_id
        metadata['chunk_index'] = i
        metadata['content_hash'] = content_hash
        
        chunks.append(Chunk(
            text=content,
            content_hash=content_hash,
            metadata=metadata
        ))
    
    logger.info(f"Produced {len(chunks)} chunks from {len(documents)} documents")
    return chunks
