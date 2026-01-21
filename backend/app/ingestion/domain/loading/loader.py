"""
Document Loader
Wraps existing source handlers to provide batch-based loading with checkpoint support.
"""

import inspect
import logging
from collections.abc import Generator
from typing import Any

from llama_index.core import Document

from app.ingestion.domain.sources.factory import SourceHandlerFactory

logger = logging.getLogger(__name__)


def _enrich_document(doc: Document, kb_id: str, doc_index: int) -> Document | None:
    """Validate and enrich a single document with necessary metadata."""
    if not doc.text or not doc.text.strip():
        logger.warning(f'Skipping document {doc_index}: empty text')
        return None

    # Ensure document has an ID
    if not doc.id_:
        doc.id_ = f'{kb_id}_doc_{doc_index}'

    # Ensure metadata has source reference
    if not doc.metadata:
        doc.metadata = {}
    if 'kb_id' not in doc.metadata:
        doc.metadata['kb_id'] = kb_id
    if 'doc_id' not in doc.metadata:
        doc.metadata['doc_id'] = doc_index

    return doc


def fetch_batches(
    kb_config: dict[str, Any],
    checkpoint: dict[str, Any] | None = None,
    batch_size: int = 10,
) -> Generator[list[Document], None, None]:
    """
    Fetch document batches from configured source with checkpoint support.

    Args:
        kb_config: Knowledge base configuration with 'source_type' and 'source_config'
        checkpoint: Optional checkpoint dict with 'last_batch_id' and 'cursor'
        batch_size: Number of documents per batch

    Yields:
        Lists of LlamaIndex Documents
    """
    source_type = kb_config.get('source_type')
    source_config = kb_config.get('source_config', {})
    kb_id = kb_config.get('kb_id')

    if not source_type:
        raise ValueError("kb_config must contain 'source_type'")

    if not kb_id:
        raise ValueError("kb_config must contain 'kb_id'")

    logger.info(f'Loading documents: type={source_type}, kb_id={kb_id}')

    handler = SourceHandlerFactory.create_handler(
        source_type=source_type,
        kb_id=kb_id,
        job=None,
        state=None,
    )

    try:
        result = handler.ingest(source_config)
    except Exception as e:
        logger.error(f'Failed to ingest from {source_type}: {e}')
        raise

    if inspect.isgenerator(result):
        yield from _stream_batches(result, kb_id)
    else:
        yield from _process_list(result, kb_id, checkpoint, batch_size)


def _stream_batches(
    generator: Generator[list[Document], None, None], kb_id: str
) -> Generator[list[Document], None, None]:
    """Handle results as a stream of batches."""
    logger.info('Handler is streaming batches')
    doc_index = 0
    for batch in generator:
        validated_batch = []
        for doc in batch:
            enriched = _enrich_document(doc, kb_id, doc_index)
            if enriched:
                validated_batch.append(enriched)
            doc_index += 1

        if validated_batch:
            yield validated_batch
    logger.info(f'Completed loading {doc_index} documents in batches')


def _process_list(
    all_documents: list[Document], kb_id: str, checkpoint: dict[str, Any] | None, batch_size: int
) -> Generator[list[Document], None, None]:
    """Handle results as a flat list."""
    if not all_documents:
        logger.warning('No documents returned from source')
        return

    valid_documents = []
    for i, doc in enumerate(all_documents):
        enriched = _enrich_document(doc, kb_id, i)
        if enriched:
            valid_documents.append(enriched)

    logger.info(f'Validated {len(valid_documents)}/{len(all_documents)} documents')

    start_idx = 0
    if checkpoint:
        last_batch_id = checkpoint.get('last_batch_id', 0)
        start_idx = (last_batch_id + 1) * batch_size
        logger.info(f'Resuming from batch {last_batch_id + 1}, doc index {start_idx}')

    for batch_start in range(start_idx, len(valid_documents), batch_size):
        batch = valid_documents[batch_start : batch_start + batch_size]
        if batch:
            yield batch
    logger.info(f'Completed loading {len(valid_documents)} documents in batches')
