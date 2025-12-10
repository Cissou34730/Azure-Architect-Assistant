"""
Consumer Pipeline for Ingestion
Contains all consumer logic for dequeue → embed → index workflow.
Proper separation from worker layer.

.. deprecated:: 2025-12-10
    This producer/consumer pipeline is deprecated. Use the orchestrator-based
    implementation in `app.ingestion.application.orchestrator` instead.
    See docs/ingestion/LEGACY_DEPRECATION.md for migration guide.
"""

import logging
import warnings
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.ingestion.domain.models import JobRuntime
from app.ingestion.infrastructure.repository import DatabaseRepository
from app.ingestion.infrastructure.embedding import EmbedderFactory
from app.ingestion.infrastructure.indexing import IndexBuilderFactory
from app.ingestion.domain.phase_tracker import IngestionPhase, PhaseStatus
from app.ingestion.application.phase_tracker import PhaseTracker
from app.ingestion.core.state_manager import aggregate_job_status
from app.ingestion.core.phase import PhaseStatus as CorePhaseStatus

logger = logging.getLogger(__name__)


class ConsumerPipeline:
    """
    Consumer pipeline: Dequeue → Embed → Index
    
    .. deprecated:: 2025-12-10
        Use `IngestionOrchestrator` from `app.ingestion.application.orchestrator`
        with the new `/ingestion/v2/jobs` API instead.
        See docs/ingestion/LEGACY_DEPRECATION.md
    """
    
    def __init__(self, runtime: JobRuntime):
        """
        Initialize consumer pipeline.
        
        Args:
            runtime: Job runtime context
        """
        warnings.warn(
            "ConsumerPipeline is deprecated. Use IngestionOrchestrator instead. "
            "See docs/ingestion/LEGACY_DEPRECATION.md",
            DeprecationWarning,
            stacklevel=2
        )
        self.runtime = runtime
        self.kb_id = runtime.kb_id
        self.job_id = runtime.job_id
        self.state = runtime.state
        self.stop_event = runtime.stop_event
        
        # Get settings
        from config import get_settings
        self.settings = get_settings()
        
        # Initialize infrastructure
        self.repository = DatabaseRepository()
        
        # Build embedder and index builder (separate responsibilities)
        self.embedder = self._create_embedder()
        self.index_builder = self._create_index_builder()
        
        # Processing state
        self.consecutive_empty_batches = 0
        self.max_empty_batches = 10
        
        # Phase tracking
        self.phase_tracker: Optional[PhaseTracker] = PhaseTracker(self.repository) if self.state and self.state.job_id else None
        
        self.total_embedded = 0
        self.total_indexed = 0
        
        self.log_prefix = f"[ConsumerPipeline|KB={self.kb_id}|Job={self.job_id}]"
    
    def run(self) -> None:
        """
        Execute the consumer pipeline.
        Polls queue, embeds chunks, indexes them, commits results.
        """
        logger.info(f"{self.log_prefix} Starting consumer pipeline")
        
        # Don't start EMBEDDING phase immediately - wait for queue items first
        embedding_phase_started = False
        
        try:
            # Main processing loop
            while True:
                # Check if we should stop
                self._should_stop()  # Just for logging
                
                # Check if producer finished
                producer_stopped = self._is_producer_stopped()
                
                # Start EMBEDDING phase when first batch arrives (lazy start)
                if not embedding_phase_started and self.phase_tracker:
                    if self.phase_tracker.should_run_phase(IngestionPhase.EMBEDDING):
                        # Require upstream dependency readiness and actual input
                        queue_stats = self.repository.get_queue_stats(self.job_id)
                        has_input = (queue_stats['pending'] > 0 or queue_stats['processing'] > 0)
                        chunking_ready = (
                            self.phase_tracker.is_phase_completed(self.job_id, 'chunking') or 
                            self.phase_tracker.has_phase_started(self.job_id, 'chunking')
                        )
                        if has_input and chunking_ready:
                            logger.info(f"{self.log_prefix} Queue has items, starting EMBEDDING phase")
                            self.phase_tracker.start_phase(IngestionPhase.EMBEDDING)
                            self._persist_phase_tracker()
                            embedding_phase_started = True
                        elif producer_stopped and not has_input:
                            logger.info(f"{self.log_prefix} Producer finished with empty queue, skipping EMBEDDING start")
                            break
                
                # Dequeue and process batch
                if not self._process_next_batch(producer_stopped):
                    # No batch processed - check if we should exit
                    if self._should_exit_after_empty(producer_stopped):
                        break
            
            # Mark job as completed if successful
            self._finalize_job()
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Pipeline failed: {e}", exc_info=True)
            try:
                from app.ingestion.application.ingestion_service import IngestionService
                IngestionService.instance()._set_failed(self.state, error_message=str(e))
            except Exception:
                # TODO: Rebuild status logic after JobStatus deletion
                self.state.status = "failed"
                self.state.error = str(e)
            
            # Mark current phase as failed
            if self.phase_tracker:
                current_phase = self.phase_tracker.get_current_phase()
                if current_phase:
                    self.phase_tracker.fail_phase(current_phase, str(e))
                self._persist_phase_tracker()
            
            raise
        finally:
            logger.info(f"{self.log_prefix} Consumer pipeline finished")
    
    def _should_stop(self) -> bool:
        """Check if stop was requested (producer finished or external stop)."""
        if self.stop_event.is_set():
            logger.info(f"{self.log_prefix} Stop event set - finishing up")
            return False  # Let normal queue draining complete
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
        """Embed and index documents (two separate phases)."""
        try:
            # === PHASE 1: EMBEDDING ===
            # Check if we need to start EMBEDDING phase
            if self.phase_tracker:
                queue_stats = self.repository.get_queue_stats(self.job_id)
                embedding_done = queue_stats['done']
                
                # Update EMBEDDING phase progress
                if not self.phase_tracker.is_phase_completed(IngestionPhase.EMBEDDING):
                    total_items = queue_stats['pending'] + queue_stats['processing'] + queue_stats['done'] + queue_stats['error']
                    if total_items > 0:
                        embed_progress = int((embedding_done / total_items) * 100)
                        self.phase_tracker.update_phase_progress(
                            IngestionPhase.EMBEDDING,
                            embed_progress,
                            items_processed=embedding_done,
                            items_total=total_items
                        )
            
            # Progress callback for embedding
            def embedding_progress_cb(phase, prog, msg, metrics=None):
                if self.phase_tracker:
                    self.phase_tracker.update_phase_progress(
                        phase,
                        prog,
                        message=msg
                    )
            
            # Generate embeddings
            logger.info(f"{self.log_prefix} Generating embeddings for {len(docs)} documents")
            embedded_docs = self.embedder.embed_documents(docs, progress_callback=embedding_progress_cb)
            
            # Track embedding progress
            self.total_embedded += len(embedded_docs)
            
            # Check if embedding phase is complete
            if self.phase_tracker:
                queue_stats = self.repository.get_queue_stats(self.job_id)
                all_embedded = queue_stats['pending'] == 0 and queue_stats['processing'] == 0
                
                if all_embedded and not self.phase_tracker.is_phase_completed(IngestionPhase.EMBEDDING):
                    self.phase_tracker.complete_phase(IngestionPhase.EMBEDDING, queue_stats['done'])
                    self._persist_phase_tracker()
            
            # === PHASE 2: INDEXING ===
            # Start INDEXING phase only if embedding completed and there are embedded docs
            if self.phase_tracker:
                if self.phase_tracker.is_phase_completed(IngestionPhase.EMBEDDING):
                    queue_stats = self.repository.get_queue_stats(self.job_id)
                    embedded_total = queue_stats['done']
                    if embedded_total > 0 and self.phase_tracker.should_run_phase(IngestionPhase.INDEXING):
                        self.phase_tracker.start_phase(IngestionPhase.INDEXING)
                        self._persist_phase_tracker()
            
            # Progress callback for indexing
            def indexing_progress_cb(phase, prog, msg, metrics=None):
                if self.phase_tracker:
                    self.phase_tracker.update_phase_progress(
                        phase,
                        prog,
                        message=msg
                    )
            
            # Build index from pre-embedded documents
            logger.info(f"{self.log_prefix} Indexing {len(embedded_docs)} embedded documents")
            self.index_builder.build_index(embedded_docs, progress_callback=indexing_progress_cb, state=self.state)
            
            # Track indexing progress
            self.total_indexed += len(embedded_docs)
            
            # Update INDEXING phase progress only when totals are non-zero
            if self.phase_tracker and self.phase_tracker.is_phase_completed(IngestionPhase.EMBEDDING):
                queue_stats = self.repository.get_queue_stats(self.job_id)
                total_to_index = queue_stats['done']
                if total_to_index > 0:
                    index_progress = int((self.total_indexed / total_to_index) * 100)
                    self.phase_tracker.update_phase_progress(
                        IngestionPhase.INDEXING,
                        index_progress,
                        items_processed=self.total_indexed,
                        items_total=total_to_index
                    )
                    if index_progress % 10 == 0:  # Persist every 10%
                        self._persist_phase_tracker()
            
            # Commit success
            self.repository.commit_batch_success(self.job_id, ids)
            
            # Update metrics
            self._update_metrics()
            
        except Exception as exc:
            logger.error(f"{self.log_prefix} Embed/Index error: {exc}", exc_info=True)
            
            # Mark phase as failed
            if self.phase_tracker:
                current_phase = self.phase_tracker.get_current_phase()
                if current_phase:
                    self.phase_tracker.fail_phase(current_phase, str(exc))
                    self._persist_phase_tracker()
            
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
        except Exception as e:
            logger.warning(f"{self.log_prefix} Failed to update metrics: {e}")
    
    def _finalize_job(self) -> None:
        """Mark job as completed after successful processing."""
        # Only mark completed if not failed
        if self.state.status == "failed":
            return
        
        logger.info(f"{self.log_prefix} All queue items processed - marking job as completed")
        
        # Complete INDEXING phase
        if self.phase_tracker:
            if not self.phase_tracker.is_phase_completed(IngestionPhase.INDEXING):
                self.phase_tracker.complete_phase(IngestionPhase.INDEXING, self.total_indexed)
            self._persist_phase_tracker()
        
        try:
            from app.ingestion.application.ingestion_service import IngestionService
            IngestionService.instance()._set_completed(self.state, message="Ingestion completed successfully")
            self.state.phase = "completed"
            self.state.progress = 100
            self.state.completed_at = datetime.utcnow()
        except Exception:
            # TODO: Rebuild status logic after JobStatus deletion
            self.state.status = "completed"
            self.state.phase = "completed"
            self.state.progress = 100
            self.state.message = "Ingestion completed successfully"
            self.state.completed_at = datetime.utcnow()
        
        # Update repository
        try:
            # TODO: Rebuild status logic after JobStatus deletion
            self.repository.update_job_status(self.job_id, "completed")
            # Optional invariant check before saving
            # Status check removed - no longer tracking paused state
            logger.info(f"{self.log_prefix} Job marked as completed in DB")
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to update job status: {e}")
    
    
    def _create_embedder(self):
        """Create embedder from runtime configuration."""
        kb_config = self._extract_kb_config()
        from config import get_kb_defaults
        defaults = get_kb_defaults()
        merged = defaults.merge_with_kb_config(kb_config)
        
        embedding_model = merged['embedding_model']
        embedder_type = merged['embedder_type']
        
        return EmbedderFactory.create_embedder(
            embedder_type=embedder_type,
            model_name=embedding_model,
        )
    
    def _create_index_builder(self):
        """Create index builder from runtime configuration."""
        kb_config = self._extract_kb_config()
        from config import get_kb_defaults
        defaults = get_kb_defaults()
        merged = defaults.merge_with_kb_config(kb_config)
        
        backend_root = Path(__file__).parent.parent.parent.parent
        if 'paths' in kb_config and 'index' in kb_config['paths']:
            index_path = kb_config['paths']['index']
            storage_dir = str(index_path) if Path(index_path).is_absolute() else str(backend_root / index_path)
        else:
            storage_dir = str(backend_root / "data" / "knowledge_bases" / self.kb_id / "index")
        
        embedding_model = merged['embedding_model']
        generation_model = merged['generation_model']
        index_type = merged['index_type']
        
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
    
    def _persist_phase_tracker(self) -> None:
        """Persist phase tracker to database and state."""
        if not self.phase_tracker or not self.state or not self.state.job_id:
            return
        
        try:
            # Update state with phase info
            phase_data = self.phase_tracker.to_dict()
            # Keep state.phases in sync for other components expecting domain phases
            self.state.phases = phase_data
            
            current_phase = self.phase_tracker.get_current_phase()
            if current_phase:
                self.state.phase = current_phase.value
            
            # Calculate overall progress
            self.state.progress = self.phase_tracker.get_overall_progress(self.job_id)
            
            # Aggregate overall job status from per-phase statuses
            try:
                overall = aggregate_job_status({
                    k: {"status": v.get("status", CorePhaseStatus.IDLE.value)}
                    for k, v in phase_data.items()
                })
                self.state.status = overall
            except Exception:
                pass

            # Persist to database
            self.repository.update_phase_progress(
                self.state.job_id,
                current_phase.value if current_phase else "unknown",
                phase_data
            )
            
        except Exception as e:
            logger.warning(f"Failed to persist phase tracker: {e}")
