"""Consumer worker - dequeues, embeds, and indexes chunks."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Any

from app.ingestion.domain.models import JobRuntime
from app.ingestion.config import get_settings

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
        settings = get_settings()
        kb_id = runtime.kb_id
        job_id = runtime.job_id
        log_prefix = f"[Consumer|KB={kb_id}|Job={job_id}]"
        
        logger.info(f"{log_prefix} Starting consumer thread")
        stop_event = runtime.stop_event

        # Import repository and persistence from runtime context
        # Note: These should be injected via runtime or accessed via service registry
        from app.ingestion.infrastructure.repository import DatabaseRepository
        from app.ingestion.infrastructure.persistence import LocalDiskPersistenceStore
        
        repository = DatabaseRepository()
        persistence = LocalDiskPersistenceStore()
        
        # Build index builder
        index_builder = ConsumerWorker._create_index_builder(runtime)
        
        # Main processing loop
        while not stop_event.is_set():
            # Dequeue next batch
            try:
                batch = repository.dequeue_batch(job_id, limit=settings.batch_size)
            except Exception as exc:
                logger.error(f"{log_prefix} Dequeue error: {exc}")
                stop_event.wait(timeout=settings.dequeue_timeout)
                continue

            if not batch:
                # No work; sleep briefly
                stop_event.wait(timeout=settings.consumer_poll_interval)
                continue

            # Prepare documents for indexing
            docs = []
            ids = []
            for item in batch:
                try:
                    content = item['content']
                    
                    if not content or not content.strip():
                        logger.warning(
                            f"{log_prefix} Empty content: id={item['id']}, "
                            f"hash={item['doc_hash']}"
                        )
                    
                    docs.append({
                        'content': content,
                        'metadata': item['item_metadata'],
                        'doc_hash': item['doc_hash'],
                    })
                    ids.append(item['id'])
                except Exception as exc:
                    logger.error(f"{log_prefix} Prep error: {exc}")
                    try:
                        repository.commit_batch_error(item['id'], f"prep error: {exc}")
                    except Exception:
                        pass

            # Index documents
            try:
                def progress_cb(_phase, _prog, _msg, _metrics=None):
                    pass  # Could update runtime.state metrics here
                
                index_builder.build_index(docs, progress_cb, state=runtime.state)
                repository.commit_batch_success(job_id, ids)
                
                # Update metrics with queue stats
                try:
                    queue_stats = repository.get_queue_stats(job_id)
                    runtime.state.metrics.update({
                        'chunks_pending': queue_stats['pending'],
                        'chunks_processing': queue_stats['processing'],
                        'chunks_embedded': queue_stats['done'],
                        'chunks_failed': queue_stats['error'],
                        'chunks_queued': sum(queue_stats.values()),
                    })
                    persistence.save_state(runtime.state)
                except Exception as e:
                    logger.warning(f"{log_prefix} Failed to update metrics: {e}")
                    
            except Exception as exc:
                logger.error(f"{log_prefix} Indexing error: {exc}", exc_info=True)
                for item_id in ids:
                    try:
                        repository.commit_batch_error(item_id, str(exc))
                    except Exception:
                        pass

        logger.info(f"{log_prefix} Consumer thread exiting")

    @staticmethod
    def _create_index_builder(runtime: JobRuntime):
        """Create index builder from runtime configuration."""
        from app.kb.ingestion.indexing import IndexBuilderFactory
        
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
