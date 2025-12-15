"""
Ingestion Orchestrator
Sequential orchestrator implementing load → chunk → embed → index pipeline.
Per backend/docs/ingestion/OrchestratorSpec.md
"""

import asyncio
import logging
import signal
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from llama_index.core import Document

from app.ingestion.domain.loading import fetch_batches
from app.ingestion.domain.chunking.adapter import (
    create_chunker_from_config,
    chunk_documents_to_chunks
)
from app.ingestion.domain.embedding import Embedder
from app.ingestion.domain.indexing import Indexer
from app.ingestion.infrastructure.phase_repository import create_phase_repository
from app.ingestion.infrastructure.job_repository import create_job_repository
from app.ingestion.application.policies import WorkflowDefinition, RetryPolicy, StepName
from app.ingestion.application.tasks import ProcessingTask
from app.ingestion.application.storage import save_documents_to_disk

logger = logging.getLogger(__name__)

# Global shutdown event for graceful interrupt handling
_shutdown_event = asyncio.Event()


class IngestionOrchestrator:
    """
    Sequential orchestrator for ingestion pipeline.
    Implements load → chunk → embed → index with gates, checkpoints, and cleanup.
    """
    
    def __init__(self, repo=None, workflow: WorkflowDefinition = None, retry_policy: RetryPolicy = None):
        """
        Initialize orchestrator.
        
        Args:
            repo: Repository for job persistence
            workflow: Workflow definition (defaults to standard)
            retry_policy: Retry policy (defaults to 3 attempts)
        """
        self.repo = repo or create_job_repository()
        self.phase_repo = create_phase_repository()
        self.workflow = workflow or WorkflowDefinition()
        self.retry_policy = retry_policy or RetryPolicy()
        self._interrupted = False
        logger.info("IngestionOrchestrator initialized")
    
    @staticmethod
    def is_shutdown_requested() -> bool:
        """Check if shutdown has been requested (CTRL-C)."""
        is_set = _shutdown_event.is_set()
        if is_set:
            logger.warning("⚠️  SHUTDOWN FLAG DETECTED - Orchestrator should pause")
        return is_set
    
    @staticmethod
    def request_shutdown():
        """Request graceful shutdown (called by signal handler)."""
        logger.warning("=" * 70)
        logger.warning("SHUTDOWN REQUESTED - Setting global shutdown flag")
        logger.warning("All running orchestrators will pause at next checkpoint")
        logger.warning("=" * 70)
        _shutdown_event.set()
    
    @staticmethod
    def clear_shutdown_flag():
        """Clear the shutdown flag when starting/resuming a job."""
        _shutdown_event.clear()
        logger.info("✅ Shutdown flag cleared - orchestrator ready to run")
    
    async def run(self, job_id: str, kb_id: str, kb_config: Dict[str, Any]):
        """
        Run ingestion pipeline for a job.
        
        Args:
            job_id: Job identifier
            kb_id: Knowledge base identifier
            kb_config: KB configuration dict
            
        Raises:
            Exception: On unrecoverable errors
        """
        logger.info(f"Starting ingestion: job_id={job_id}, kb_id={kb_id}")
        
        # Load job state
        job = self.repo.get_job(job_id)
        checkpoint = job.checkpoint or {}
        counters = job.counters or {
            "docs_seen": 0,
            "chunks_seen": 0,
            "chunks_processed": 0,
            "chunks_skipped": 0,
            "chunks_error": 0
        }
        
        # Initialize components
        try:
            loader = fetch_batches(kb_config, checkpoint)
            chunker = create_chunker_from_config(kb_config)
            embedder = Embedder(model_name=kb_config.get('embedding_model', 'text-embedding-3-small'))
            indexer = Indexer(kb_id=kb_id)
        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            self.repo.set_job_status(
                job_id,
                status='failed',
                finished_at=datetime.utcnow(),
                last_error=f"Initialization failed: {e}"
            )
            raise
        
        try:
            # Main processing loop: batches
            start_batch_id = checkpoint.get('last_batch_id', -1) + 1
            
            batch_iter = iter(loader)
            batch_id = start_batch_id
            while True:
                try:
                    batch = await asyncio.to_thread(lambda: next(batch_iter))
                except StopIteration:
                    break

                # Mark phase loading/chunking as running
                self.phase_repo.start_phase(job_id, "loading")
                # Check for shutdown request (CTRL-C)
                if self.is_shutdown_requested():
                    logger.warning(f"Shutdown requested - pausing job {job_id} at batch {batch_id}")
                    self.repo.set_job_status(job_id, status='paused')
                    self.repo.update_job(job_id, checkpoint=checkpoint, counters=counters)
                    return
                
                # Gate check before batch
                if not await self._check_gate(job_id, kb_id, indexer):
                    logger.info(f"Pipeline stopped at gate check (batch {batch_id})")
                    return
                
                logger.info(f"Processing batch {batch_id}: {len(batch)} documents")
                
                # Save documents to disk
                await asyncio.to_thread(save_documents_to_disk, kb_id, batch)
                
                # Step 1: Chunk batch
                chunks = await asyncio.to_thread(chunk_documents_to_chunks, batch, chunker, kb_id)
                counters['docs_seen'] += len(batch)
                counters['chunks_seen'] += len(chunks)
                self.phase_repo.complete_phase(job_id, "loading")
                self.phase_repo.start_phase(job_id, "chunking")
                self.phase_repo.complete_phase(job_id, "chunking")
                
                logger.info(f"Batch {batch_id}: Generated {len(chunks)} chunks, starting embed+index...")
                
                # Track batch metrics
                batch_start_processed = counters['chunks_processed']
                batch_start_skipped = counters['chunks_skipped']
                # Start embedding/indexing phases
                self.phase_repo.start_phase(job_id, "embedding")
                self.phase_repo.start_phase(job_id, "indexing")
                
                # Step 2: Process each chunk (embed + index)
                for chunk_idx, chunk in enumerate(chunks):
                    # Check for shutdown request (CTRL-C)
                    if self.is_shutdown_requested():
                        logger.warning(f"Shutdown requested - pausing job {job_id} at batch {batch_id}, chunk {chunk_idx}")
                        checkpoint['last_batch_id'] = batch_id - 1  # Don't count current incomplete batch
                        self.repo.set_job_status(job_id, status='paused')
                        self.repo.update_job(job_id, checkpoint=checkpoint, counters=counters)
                        return
                    
                    # Gate check before chunk
                    if not await self._check_gate(job_id, kb_id, indexer):
                        logger.info(f"Pipeline stopped at gate check (batch {batch_id}, chunk {chunk_idx})")
                        # Save progress before stopping
                        checkpoint['last_batch_id'] = batch_id - 1  # Don't count current incomplete batch
                        self.repo.update_job(job_id, checkpoint=checkpoint, counters=counters)
                        return
                    
                    # Create task for logging
                    task = ProcessingTask(
                        job_id=job_id,
                        kb_id=kb_id,
                        step=StepName.EMBED,
                        payload={"chunk": chunk},
                        batch_id=batch_id,
                        chunk_index=chunk_idx
                    )
                    
                    # Process with retry
                    result = await self._process_chunk_with_retry(task, chunk, embedder, indexer)
                    
                    if result["skipped"]:
                        counters['chunks_skipped'] += 1
                    elif result["success"]:
                        counters['chunks_processed'] += 1
                    else:
                        counters['chunks_error'] += 1
                        logger.error(f"Chunk processing failed: {result.get('error')}")
                    # Update phase progress optimistic
                    try:
                        self.phase_repo.complete_phase(job_id, "embedding")
                        self.phase_repo.complete_phase(job_id, "indexing")
                    except Exception:
                        pass
                
                # Persist checkpoint and counters after batch
                checkpoint['last_batch_id'] = batch_id
                self.repo.update_job(job_id, checkpoint=checkpoint, counters=counters)
                self.repo.update_heartbeat(job_id)
                
                # Log batch summary
                batch_processed = counters['chunks_processed'] - batch_start_processed
                batch_skipped = counters['chunks_skipped'] - batch_start_skipped
                logger.info(f"Batch {batch_id} complete: {batch_processed} embedded+indexed, {batch_skipped} skipped (already indexed)")
                logger.info(f"Total progress: {counters}")
            
            # All batches complete
            self.repo.set_job_status(
                job_id,
                status='completed',
                finished_at=datetime.utcnow(),
                last_error=None
            )
            logger.info(f"Ingestion completed: job_id={job_id}, counters={counters}")
            
        except Exception as e:
            logger.exception(f"Ingestion failed: job_id={job_id}")
            self.repo.set_job_status(
                job_id,
                status='failed',
                finished_at=datetime.utcnow(),
                last_error=str(e)
            )
            raise
    
    async def _process_chunk_with_retry(
        self,
        task: ProcessingTask,
        chunk,
        embedder: Embedder,
        indexer: Indexer
    ) -> Dict[str, Any]:
        """
        Process chunk with embed + index and retry logic.
        
        Args:
            task: Processing task metadata
            chunk: Chunk dataclass
            embedder: Embedder instance
            indexer: Indexer instance
            
        Returns:
            Result dict with keys: success, skipped, error
        """
        # Check idempotency first
        exists = await asyncio.to_thread(indexer.exists, task.kb_id, chunk.content_hash)
        if exists:
            logger.debug(f"Chunk {chunk.content_hash[:8]} already indexed, skipping")
            return {"success": True, "skipped": True}
        
        # Try embed + index with retry
        attempt = 0
        while True:
            attempt += 1
            try:
                # Embed
                embedding = await embedder.embed(chunk)
                
                # Index
                await asyncio.to_thread(indexer.index, task.kb_id, embedding)
                
                return {"success": True, "skipped": False}
                
            except Exception as e:
                if self.retry_policy.should_retry(attempt, e):
                    delay = self.retry_policy.get_backoff_delay(attempt)
                    logger.warning(
                        f"Chunk {chunk.content_hash[:8]} attempt {attempt} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Chunk {chunk.content_hash[:8]} failed after {attempt} attempts: {e}"
                    )
                    return {"success": False, "skipped": False, "error": str(e)}
    
    async def _check_gate(self, job_id: str, kb_id: str, indexer: Indexer) -> bool:
        """
        Check job status gate for pause/resume/cancel.
        
        Args:
            job_id: Job identifier
            kb_id: Knowledge base identifier
            indexer: Indexer for cleanup on cancel
            
        Returns:
            True to continue, False to stop
        """
        while True:
            status = self.repo.get_job_status(job_id)
            
            if status == 'running':
                return True
            elif status == 'paused':
                logger.info(f"Job {job_id} paused, waiting...")
                await asyncio.sleep(1)  # Backoff and re-check
            elif status == 'canceled':
                logger.info(f"Job {job_id} canceled, running cleanup...")
                await self._cleanup_job(job_id, kb_id, indexer)
                return False
            elif status in ('failed', 'completed'):
                logger.info(f"Job {job_id} already {status}, stopping")
                return False
            else:
                logger.warning(f"Unknown job status '{status}', treating as failed")
                return False
    
    async def _cleanup_job(self, job_id: str, kb_id: str, indexer: Indexer):
        """
        Cleanup workflow for canceled jobs.
        
        Args:
            job_id: Job identifier
            kb_id: Knowledge base identifier
            indexer: Indexer for vector store cleanup
        """
        try:
            # Delete all indexed data for this KB
            indexer.delete_by_job(job_id, kb_id)
            logger.info(f"Deleted indexed data for job {job_id}")
            
            # Reset job state
            self.repo.update_job(
                job_id,
                status='not_started',
                checkpoint=None,
                counters=None,
                finished_at=datetime.utcnow(),
                last_error='Canceled by user'
            )
            logger.info(f"Reset job {job_id} to not_started")
            
        except Exception as e:
            # Log but don't crash
            logger.error(f"Cleanup failed for job {job_id}: {e}", exc_info=True)
