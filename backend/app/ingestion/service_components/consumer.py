"""Consumer worker thread - handles dequeuing, embedding, and indexing."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Any

from .repository import (
    dequeue_batch,
    commit_batch_success,
    commit_batch_error,
    get_queue_stats,
)
from .runtime import JobRuntime
from .storage import persist_state

logger = logging.getLogger(__name__)


class ConsumerWorker:
    """Worker that processes the queue in a separate thread."""

    @staticmethod
    def run(runtime: JobRuntime) -> None:
        """
        Consumer thread entry point.
        
        Polls queue for chunks, embeds them, indexes them, commits results.
        Honors stop_event for graceful shutdown.
        """
        logger.info("Starting consumer thread for KB %s", runtime.kb_id)
        stop_event = runtime.stop_event

        # Build index builder
        index_builder = ConsumerWorker._create_index_builder(runtime)
        
        # Main processing loop
        while not stop_event.is_set():
            # Dequeue next batch
            try:
                batch = dequeue_batch(runtime.job_id, limit=50)
            except Exception as exc:
                logger.error("Consumer dequeue error for KB %s: %s", runtime.kb_id, exc)
                stop_event.wait(timeout=1.0)
                continue

            if not batch:
                # No work; sleep briefly
                stop_event.wait(timeout=0.1)
                continue

            # Prepare documents for indexing
            docs = []
            ids = []
            for item in batch:
                try:
                    content = item['content']
                    
                    # Debug: log if content is empty
                    if not content or not content.strip():
                        logger.warning(
                            f"Consumer received empty content: id={item['id']}, "
                            f"hash={item['doc_hash']}, metadata={item['item_metadata']}"
                        )
                    
                    docs.append({
                        'content': content,
                        'metadata': item['item_metadata'],
                        'doc_hash': item['doc_hash'],
                    })
                    ids.append(item['id'])
                except Exception as exc:
                    logger.error("Consumer prep error: %s", exc)
                    try:
                        commit_batch_error(item['id'], f"prep error: {exc}")
                    except Exception:
                        pass

            # Index documents
            try:
                def progress_cb(_phase, _prog, _msg, _metrics=None):
                    pass  # Could update runtime.state metrics here if desired
                
                index_builder.build_index(docs, progress_cb, state=runtime.state)
                commit_batch_success(runtime.job_id, ids)
                
                # Update metrics with queue stats
                try:
                    queue_stats = get_queue_stats(runtime.job_id)
                    runtime.state.metrics.update({
                        'chunks_pending': queue_stats['pending'],
                        'chunks_processing': queue_stats['processing'],
                        'chunks_embedded': queue_stats['done'],
                        'chunks_failed': queue_stats['error'],
                        'chunks_queued': sum(queue_stats.values()),
                    })
                    persist_state(runtime.state)
                except Exception as e:
                    logger.warning(f"Failed to update queue metrics: {e}")
                    
            except Exception as exc:
                logger.error("Consumer indexing error for KB %s: %s", runtime.kb_id, exc, exc_info=True)
                for item_id in ids:
                    try:
                        commit_batch_error(item_id, str(exc))
                    except Exception:
                        pass

        logger.info("Consumer thread exiting for KB %s", runtime.kb_id)

    @staticmethod
    def _create_index_builder(runtime: JobRuntime):
        """Create index builder from runtime configuration."""
        from app.kb.ingestion.indexing import IndexBuilderFactory
        
        # Extract kb_config from producer args
        kb_config = ConsumerWorker._extract_kb_config(runtime.producer_args)
        kb_id = runtime.kb_id
        
        backend_root = Path(__file__).parent.parent.parent.parent
        if 'paths' in kb_config and 'index' in kb_config['paths']:
            index_path = kb_config['paths']['index']
            storage_dir = str(index_path) if Path(index_path).is_absolute() else str(backend_root / index_path)
        else:
            storage_dir = str(backend_root / "data" / "knowledge_bases" / kb_id / "index")
            
        embedding_model = kb_config.get('embedding_model', 'text-embedding-3-small')
        generation_model = kb_config.get('generation_model', 'gpt-4o-mini')
        index_type = kb_config.get('index_type', 'vector')

        return IndexBuilderFactory.create_builder(
            index_type=index_type,
            kb_id=kb_id,
            storage_dir=storage_dir,
            embedding_model=embedding_model,
            generation_model=generation_model,
        )

    @staticmethod
    def _extract_kb_config(args) -> Dict[str, Any]:
        """Extract KB config dict from producer args tuple."""
        for value in args:
            if isinstance(value, dict) and value.get("id"):
                return value
        return {}
