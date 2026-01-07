"""
Document Loader
Wraps existing source handlers to provide batch-based loading with checkpoint support.
"""

import logging
from typing import Dict, Any, Generator, List, Optional
from llama_index.core import Document

from app.ingestion.domain.sources.factory import SourceHandlerFactory

logger = logging.getLogger(__name__)


def fetch_batches(
    kb_config: Dict[str, Any],
    checkpoint: Optional[Dict[str, Any]] = None,
    batch_size: int = 10,
) -> Generator[List[Document], None, None]:
    """
    Fetch document batches from configured source with checkpoint support.

    Args:
        kb_config: Knowledge base configuration with 'source_type' and 'source_config'
        checkpoint: Optional checkpoint dict with 'last_batch_id' and 'cursor'
        batch_size: Number of documents per batch

    Yields:
        Lists of LlamaIndex Documents

    Example:
        >>> for batch in fetch_batches(kb_config, checkpoint):
        ...     process_batch(batch)
    """
    source_type = kb_config.get("source_type")
    source_config = kb_config.get("source_config", {})
    kb_id = kb_config.get("kb_id")

    if not source_type:
        raise ValueError("kb_config must contain 'source_type'")

    if not kb_id:
        raise ValueError("kb_config must contain 'kb_id'")

    logger.info(f"Loading documents: type={source_type}, kb_id={kb_id}")

    # Create source handler (existing implementation)
    # Note: checkpoint support in handlers may need enhancement
    handler = SourceHandlerFactory.create_handler(
        source_type=source_type,
        kb_id=kb_id,
        job=None,  # Not using old job model
        state=None,  # Not using old state model
    )

    # Ingest documents from source
    # Handlers may return a list or a generator of batches
    try:
        result = handler.ingest(source_config)
    except Exception as e:
        logger.error(f"Failed to ingest from {source_type}: {e}")
        raise

    # Check if result is a generator (yields batches) or a list (all docs at once)
    import inspect

    if inspect.isgenerator(result):
        # Handler yields batches already - pass them through with validation
        logger.info("Handler is streaming batches")
        doc_index = 0
        for batch in result:
            # Validate and enrich batch
            validated_batch = []
            for doc in batch:
                if not doc.text or not doc.text.strip():
                    logger.warning(f"Skipping document {doc_index}: empty text")
                    doc_index += 1
                    continue

                # Ensure document has an ID
                if not doc.id_:
                    doc.id_ = f"{kb_id}_doc_{doc_index}"

                # Ensure metadata has source reference
                if not doc.metadata:
                    doc.metadata = {}
                if "kb_id" not in doc.metadata:
                    doc.metadata["kb_id"] = kb_id
                if "doc_id" not in doc.metadata:
                    doc.metadata["doc_id"] = doc_index

                validated_batch.append(doc)
                doc_index += 1

            if validated_batch:
                yield validated_batch

        logger.info(f"Completed loading {doc_index} documents in batches")
    else:
        # Handler returned all docs at once - batch them ourselves
        all_documents = result

        if not all_documents:
            logger.warning(f"No documents returned from {source_type}")
            return

        # Validate documents
        valid_documents = []
        for i, doc in enumerate(all_documents):
            if not doc.text or not doc.text.strip():
                logger.warning(f"Skipping document {i}: empty text")
                continue

            # Ensure document has an ID
            if not doc.id_:
                doc.id_ = f"{kb_id}_doc_{i}"

            # Ensure metadata has source reference
            if not doc.metadata:
                doc.metadata = {}
            if "kb_id" not in doc.metadata:
                doc.metadata["kb_id"] = kb_id
            if "doc_id" not in doc.metadata:
                doc.metadata["doc_id"] = i

            valid_documents.append(doc)

        logger.info(f"Validated {len(valid_documents)}/{len(all_documents)} documents")

        # Handle checkpoint resume
        start_idx = 0
        if checkpoint:
            last_batch_id = checkpoint.get("last_batch_id", 0)
            start_idx = (last_batch_id + 1) * batch_size
            logger.info(
                f"Resuming from batch {last_batch_id + 1}, doc index {start_idx}"
            )

        # Yield documents in batches
        for batch_start in range(start_idx, len(valid_documents), batch_size):
            batch = valid_documents[batch_start : batch_start + batch_size]
            if batch:
                logger.debug(
                    f"Yielding batch: docs {batch_start} to {batch_start + len(batch) - 1}"
                )
                yield batch

        logger.info(f"Completed loading {len(valid_documents)} documents in batches")
