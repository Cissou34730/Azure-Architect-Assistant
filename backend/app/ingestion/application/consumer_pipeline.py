"""
Consumer Pipeline for Ingestion
Contains all consumer logic for dequeue → embed → index workflow.
Proper separation from worker layer.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from app.ingestion.domain.models import JobRuntime
from app.ingestion.infrastructure.repository import DatabaseRepository
from app.ingestion.infrastructure.persistence import LocalDiskPersistenceStore
from app.kb.ingestion.indexing import IndexBuilderFactory

logger = logging.getLogger(__name__)


class ConsumerPipeline:
    """Consumer pipeline: Dequeue → Embed → Index"""
    
    def __init__(self, runtime: JobRuntime):
        """
        Initialize consumer pipeline.
        
        Args:
            runtime: JobRuntime with configuration and state
        """
        self.runtime = runtime
        self.kb_id = runtime.kb_id
        self.job_id = runtime.job_id
        self.state = runtime.state
        self.stop_event = runtime.stop_event
        
        # Get settings
        from app.ingestion.config import get_settings
        self.settings = get_settings()
        
        # Initialize infrastructure
        self.repository = DatabaseRepository()
        self.persistence = LocalDiskPersistenceStore()
        
        # Build index builder
        self.index_builder = self._create_index_builder()
        
        # Processing state
        self.consecutive_empty_batches = 0
        self.max_empty_batches = 10
        
        self.log_prefix = f"[ConsumerPipeline|KB={self.kb_id}|Job={self.job_id}]"
    
    def run(self) -> None:
        """
        Execute the consumer pipeline.
        Polls queue, embeds chunks, indexes them, commits results.
        """
        logger.info(f"{self.log_prefix} Starting consumer pipeline")
        
        try:
            # Main processing loop
            while True:
                # Check for immediate cancellation
                if self._should_cancel():
                    break
                
                # Check if producer finished
                producer_stopped = self._is_producer_stopped()
                
                # Dequeue and process batch
                if not self._process_next_batch(producer_stopped):
                    # No batch processed - check if we should exit
                    if self._should_exit_after_empty(producer_stopped):
                        break
            
            # Mark job as completed if successful
            self._finalize_job()
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Pipeline failed: {e}", exc_info=True)
            self.state.status = "failed"
            self.state.error = str(e)
            raise
        finally:
            logger.info(f"{self.log_prefix} Consumer pipeline finished")
    
    def _should_cancel(self) -> bool:
        """Check if immediate cancellation requested."""
        if self.state.cancel_requested:
            logger.info(f"{self.log_prefix} Cancellation requested - exiting immediately")
            return True
        return False
    
    def _is_producer_stopped(self) -> bool:
        """Check if producer has finished."""
        stopped = self.stop_event.is_set()
        if stopped and self.consecutive_empty_batches == 0:
            logger.info(f"{self.log_prefix} Producer finished - draining remaining queue")
        return stopped
    
    def _process_next_batch(self, producer_stopped: bool) -> bool:
        """
        Dequeue and process next batch.
        
        Returns:
            True if batch was processed, False if queue was empty
        """
        # Dequeue batch
        try:
            batch = self.repository.dequeue_batch(
                self.job_id, 
                limit=self.settings.batch_size
            )
        except Exception as exc:
            logger.error(f"{self.log_prefix} Dequeue error: {exc}")
            self.stop_event.wait(timeout=self.settings.dequeue_timeout)
            return False
        
        # Handle empty queue
        if not batch:
            return self._handle_empty_queue(producer_stopped)
        
        # Reset empty counter - we have work
        self.consecutive_empty_batches = 0
        
        # Prepare documents
        docs, ids = self._prepare_documents(batch)
        
        # Index documents
        self._index_documents(docs, ids)
        
        return True
    
    def _handle_empty_queue(self, producer_stopped: bool) -> bool:
        """
        Handle empty queue scenario.
        
        Returns:
            False (no batch processed)
        """
        if producer_stopped:
            # Producer stopped and queue empty
            self.consecutive_empty_batches += 1
            # Brief wait before rechecking
            self.stop_event.wait(timeout=self.settings.consumer_poll_interval)
        else:
            # Producer still running - normal wait
            self.consecutive_empty_batches = 0
            self.stop_event.wait(timeout=self.settings.consumer_poll_interval)
        
        return False
    
    def _should_exit_after_empty(self, producer_stopped: bool) -> bool:
        """Check if consumer should exit after consecutive empty batches."""
        if producer_stopped and self.consecutive_empty_batches >= self.max_empty_batches:
            logger.info(f"{self.log_prefix} Queue fully drained - exiting consumer")
            return True
        return False
    
    def _prepare_documents(self, batch: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[int]]:
        """
        Prepare documents from batch for indexing.
        
        Returns:
            Tuple of (documents, ids)
        """
        docs = []
        ids = []
        
        for item in batch:
            try:
                content = item['content']
                
                if not content or not content.strip():
                    logger.warning(
                        f"{self.log_prefix} Empty content: id={item['id']}, "
                        f"hash={item['doc_hash']}"
                    )
                
                docs.append({
                    'content': content,
                    'metadata': item['item_metadata'],
                    'doc_hash': item['doc_hash'],
                })
                ids.append(item['id'])
            except Exception as exc:
                logger.error(f"{self.log_prefix} Prep error: {exc}")
                try:
                    self.repository.commit_batch_error(item['id'], f"prep error: {exc}")
                except Exception:
                    pass
        
        return docs, ids
    
    def _index_documents(self, docs: List[Dict[str, Any]], ids: List[int]) -> None:
        """Index documents and commit results."""
        try:
            # Progress callback (could update metrics here)
            def progress_cb(_phase, _prog, _msg, _metrics=None):
                pass
            
            # Build index
            self.index_builder.build_index(docs, progress_cb, state=self.state)
            
            # Commit success
            self.repository.commit_batch_success(self.job_id, ids)
            
            # Update metrics
            self._update_metrics()
            
        except Exception as exc:
            logger.error(f"{self.log_prefix} Indexing error: {exc}", exc_info=True)
            for item_id in ids:
                try:
                    self.repository.commit_batch_error(item_id, str(exc))
                except Exception:
                    pass
    
    def _update_metrics(self) -> None:
        """Update state metrics with queue stats."""
        try:
            queue_stats = self.repository.get_queue_stats(self.job_id)
            self.state.metrics.update({
                'chunks_pending': queue_stats['pending'],
                'chunks_processing': queue_stats['processing'],
                'chunks_embedded': queue_stats['done'],
                'chunks_failed': queue_stats['error'],
                'chunks_queued': sum(queue_stats.values()),
            })
            self.persistence.save_state(self.state)
        except Exception as e:
            logger.warning(f"{self.log_prefix} Failed to update metrics: {e}")
    
    def _finalize_job(self) -> None:
        """Mark job as completed after successful processing."""
        # Only mark completed if not cancelled or failed
        if self.state.cancel_requested:
            return
        
        if self.state.status in {"failed", "cancelled"}:
            return
        
        logger.info(f"{self.log_prefix} All queue items processed - marking job as completed")
        
        self.state.status = "completed"
        self.state.phase = "completed"
        self.state.progress = 100
        self.state.message = "Ingestion completed successfully"
        self.state.completed_at = datetime.utcnow()
        
        # Update repository
        try:
            from app.ingestion.domain.enums import JobStatus
            self.repository.update_job_status(self.job_id, JobStatus.COMPLETED.value)
            self.persistence.save_state(self.state)
            logger.info(f"{self.log_prefix} Job marked as completed in DB")
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to update job status: {e}")
    
    def _create_index_builder(self):
        """Create index builder from runtime configuration."""
        kb_config = self._extract_kb_config()
        
        backend_root = Path(__file__).parent.parent.parent.parent
        if 'paths' in kb_config and 'index' in kb_config['paths']:
            index_path = kb_config['paths']['index']
            storage_dir = str(index_path) if Path(index_path).is_absolute() else str(backend_root / index_path)
        else:
            storage_dir = str(backend_root / "data" / "knowledge_bases" / self.kb_id / "index")
        
        embedding_model = kb_config.get('embedding_model', 'text-embedding-3-small')
        generation_model = kb_config.get('generation_model', 'gpt-4o-mini')
        index_type = kb_config.get('index_type', 'vector')
        
        return IndexBuilderFactory.create_builder(
            index_type=index_type,
            kb_id=self.kb_id,
            storage_dir=storage_dir,
            embedding_model=embedding_model,
            generation_model=generation_model,
        )
    
    def _extract_kb_config(self) -> Dict[str, Any]:
        """Extract KB config dict from producer args."""
        for value in self.runtime.producer_args:
            if isinstance(value, dict) and value.get("id"):
                return value
        return {}
