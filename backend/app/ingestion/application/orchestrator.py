"""
Ingestion Orchestrator
Sequential orchestrator implementing load -> chunk -> embed -> index pipeline.
See docs/SYSTEM_ARCHITECTURE.md for a pipeline overview.
"""

import asyncio
import contextlib
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, cast

from app.ingestion.application.policies import RetryPolicy, StepName, WorkflowDefinition
from app.ingestion.application.storage import save_documents_to_disk
from app.ingestion.application.tasks import ProcessingTask
from app.ingestion.domain.chunking.adapter import (
    chunk_documents_to_chunks,
    create_chunker_from_config,
)
from app.ingestion.domain.embedding import Embedder
from app.ingestion.domain.indexing import Indexer
from app.ingestion.domain.loading import fetch_batches
from app.ingestion.infrastructure.job_repository import JobRepository, create_job_repository
from app.ingestion.infrastructure.phase_repository import PhaseRepository, create_phase_repository

logger = logging.getLogger(__name__)


@dataclass
class PipelineBatchContext:
    """Context object for a pipeline batch to reduce function argument counts."""

    job_id: str
    kb_id: str
    batch_id: int
    checkpoint: dict[str, Any]
    counters: dict[str, int]
    phases_started: dict[str, bool] = field(
        default_factory=lambda: {'chunking': False, 'embedding': False, 'indexing': False}
    )


@dataclass
class PipelineComponents:
    """Groups pipeline component instances."""

    loader: Iterator[Any]
    chunker: Any
    embedder: Embedder
    indexer: Indexer


# Global shutdown event for graceful interrupt handling
_shutdown_event = asyncio.Event()


class IngestionOrchestrator:
    """
    Sequential orchestrator for ingestion pipeline.
    Implements load → chunk → embed → index with gates, checkpoints, and cleanup.
    """

    def __init__(
        self,
        repo: JobRepository | None = None,
        workflow: WorkflowDefinition | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        """
        Initialize orchestrator.

        Args:
            repo: Repository for job persistence
            workflow: Workflow definition (defaults to standard)
            retry_policy: Retry policy (defaults to 3 attempts)
        """
        self.repo = repo or create_job_repository()
        self.phase_repo: PhaseRepository = create_phase_repository()
        self.workflow = workflow or WorkflowDefinition()
        self.retry_policy = retry_policy or RetryPolicy()
        self._interrupted = False
        logger.info('IngestionOrchestrator initialized')

    @staticmethod
    def is_shutdown_requested() -> bool:
        """Check if shutdown has been requested (CTRL-C)."""
        is_set = _shutdown_event.is_set()
        if is_set:
            logger.warning('⚠️  SHUTDOWN FLAG DETECTED - Orchestrator should pause')
        return is_set

    @staticmethod
    def request_shutdown() -> None:
        """Request graceful shutdown (called by signal handler)."""
        logger.warning('=' * 70)
        logger.warning('SHUTDOWN REQUESTED - Setting global shutdown flag')
        logger.warning('All running orchestrators will pause at next checkpoint')
        logger.warning('=' * 70)
        _shutdown_event.set()

    @staticmethod
    def clear_shutdown_flag() -> None:
        """Clear the shutdown flag when starting/resuming a job."""
        _shutdown_event.clear()
        logger.info('✅ Shutdown flag cleared - orchestrator ready to run')

    async def run(self, job_id: str, kb_id: str, kb_config: dict[str, Any]) -> None:
        """
        Run ingestion pipeline for a job.

        Args:
            job_id: Job identifier
            kb_id: Knowledge base identifier
            kb_config: KB configuration dict

        Raises:
            Exception: On unrecoverable errors
        """
        logger.info(f'Starting ingestion: job_id={job_id}, kb_id={kb_id}')

        # 1. Load job state
        checkpoint, counters = self._prepare_job_state(job_id)

        # 2. Initialize components
        try:
            components = self._initialize_components(kb_id, kb_config, checkpoint)
        except Exception as e:
            self.repo.set_job_status(
                job_id,
                status='failed',
                finished_at=datetime.now(timezone.utc),
                last_error=f'Initialization failed: {e}',
            )
            raise

        # 3. Process pipeline
        try:
            # We keep the loop logic in a dedicated method but orchestrate here
            await self._run_pipeline_loop(job_id, kb_id, components, checkpoint, counters)
        except Exception as e:
            logger.exception(f'Ingestion failed: job_id={job_id}')
            self.repo.set_job_status(
                job_id,
                status='failed',
                finished_at=datetime.now(timezone.utc),
                last_error=str(e),
            )
            raise

    def _prepare_job_state(self, job_id: str) -> tuple[dict[str, Any], dict[str, int]]:
        """Load and initialize job state."""
        job = self.repo.get_job(job_id)
        checkpoint = job.checkpoint or {}
        counters = job.counters or {
            'docs_seen': 0,
            'chunks_seen': 0,
            'chunks_processed': 0,
            'chunks_skipped': 0,
            'chunks_error': 0,
        }
        return checkpoint, counters

    def _initialize_components(
        self, kb_id: str, kb_config: dict[str, Any], checkpoint: dict[str, Any]
    ) -> PipelineComponents:
        """Initialize pipeline components."""
        loader = fetch_batches(kb_config, checkpoint)
        chunker = create_chunker_from_config(kb_config)
        embedder = Embedder(model_name=kb_config.get('embedding_model', 'text-embedding-3-small'))
        indexer = Indexer(kb_id=kb_id)
        return PipelineComponents(
            loader=loader, chunker=chunker, embedder=embedder, indexer=indexer
        )

    async def _run_pipeline_loop(
        self,
        job_id: str,
        kb_id: str,
        components: PipelineComponents,
        checkpoint: dict[str, Any],
        counters: dict[str, int],
    ) -> None:
        """Main processing loop through batches."""
        start_batch_id = int(checkpoint.get('last_batch_id', -1)) + 1
        self.phase_repo.start_phase(job_id, 'loading')

        phases_started = {'chunking': False, 'embedding': False, 'indexing': False}
        batch_id = start_batch_id

        while True:
            try:
                batch = await asyncio.to_thread(next, components.loader)
            except StopIteration:
                break

            ctx = PipelineBatchContext(
                job_id=job_id,
                kb_id=kb_id,
                batch_id=batch_id,
                checkpoint=checkpoint,
                counters=counters,
                phases_started=phases_started,
            )

            # Mark loading phase as running
            self.phase_repo.start_phase(job_id, 'loading')

            # Check for shutdown request (CTRL-C)
            if self.is_shutdown_requested():
                logger.warning(f'Shutdown requested - pausing job {job_id} at batch {batch_id}')
                self.repo.set_job_status(job_id, status='paused')
                self.repo.update_job(job_id, checkpoint=checkpoint, counters=counters)
                return

            # Gate check before batch
            if not await self._check_gate(job_id, kb_id, components.indexer):
                logger.info(f'Pipeline stopped at gate check (batch {batch_id})')
                return

            logger.info(f'Processing batch {batch_id}: {len(batch)} documents')

            # Phase 1: Load batch
            await self._run_load_phase(ctx, batch)

            # Phase 2: Chunk batch
            chunks = await self._run_chunk_phase(ctx, batch, components.chunker)

            # Phase 3: Process chunks (Embed + Index)
            logger.info(
                f'Batch {batch_id}: Generated {len(chunks)} chunks, starting embed+index...'
            )

            continue_pipeline = await self._run_embed_and_index_phase(
                ctx,
                chunks,
                components.embedder,
                components.indexer,
            )

            if not continue_pipeline:
                return

            # Persist checkpoint and counters after batch
            checkpoint['last_batch_id'] = batch_id
            self.repo.update_job(job_id, checkpoint=checkpoint, counters=counters)
            self.repo.update_heartbeat(job_id)

            logger.info(f'Batch {batch_id} complete. Total progress: {counters}')
            batch_id += 1

        # Pipeline finished successfully
        await self._mark_job_complete(job_id, phases_started, counters)

    async def _run_load_phase(self, ctx: PipelineBatchContext, batch: list[Any]) -> None:
        """Execute loading phase for a batch."""
        await asyncio.to_thread(save_documents_to_disk, ctx.kb_id, batch)
        with contextlib.suppress(Exception):
            self.phase_repo.update_progress(
                ctx.job_id, 'loading', items_processed=ctx.counters['docs_seen']
            )

    async def _run_chunk_phase(
        self, ctx: PipelineBatchContext, batch: list[Any], chunker: Any
    ) -> list[Any]:
        """Execute chunking phase for a batch."""
        chunks = await asyncio.to_thread(chunk_documents_to_chunks, batch, chunker, ctx.kb_id)
        ctx.counters['docs_seen'] += len(batch)
        ctx.counters['chunks_seen'] += len(chunks)
        with contextlib.suppress(Exception):
            self.phase_repo.update_progress(
                ctx.job_id, 'loading', items_processed=ctx.counters['docs_seen']
            )
            self.phase_repo.start_phase(ctx.job_id, 'chunking')
            ctx.phases_started['chunking'] = True
            self.phase_repo.update_progress(
                ctx.job_id, 'chunking', items_processed=ctx.counters['chunks_seen']
            )
        return cast(list[Any], chunks)

    async def _run_embed_and_index_phase(
        self,
        ctx: PipelineBatchContext,
        chunks: list[Any],
        embedder: Embedder,
        indexer: Indexer,
    ) -> bool:
        """Execute embedding and indexing phase for a list of chunks."""
        # Ensure embedding/indexing phases are started
        with contextlib.suppress(Exception):
            if not ctx.phases_started['embedding']:
                self.phase_repo.start_phase(ctx.job_id, 'embedding')
                ctx.phases_started['embedding'] = True
            if not ctx.phases_started['indexing']:
                self.phase_repo.start_phase(ctx.job_id, 'indexing')
                ctx.phases_started['indexing'] = True

        for chunk_idx, chunk in enumerate(chunks):
            # Check for shutdown request
            if self.is_shutdown_requested():
                logger.warning(
                    f'Shutdown requested - pausing job {ctx.job_id} at batch {ctx.batch_id}, chunk {chunk_idx}'
                )
                ctx.checkpoint['last_batch_id'] = ctx.batch_id - 1
                self.repo.set_job_status(ctx.job_id, status='paused')
                self.repo.update_job(ctx.job_id, checkpoint=ctx.checkpoint, counters=ctx.counters)
                return False

            # Gate check
            if not await self._check_gate(ctx.job_id, ctx.kb_id, indexer):
                ctx.checkpoint['last_batch_id'] = ctx.batch_id - 1
                self.repo.update_job(ctx.job_id, checkpoint=ctx.checkpoint, counters=ctx.counters)
                return False

            task = ProcessingTask(
                job_id=ctx.job_id,
                kb_id=ctx.kb_id,
                step=StepName.EMBED,
                payload={'chunk': chunk},
                batch_id=ctx.batch_id,
                chunk_index=chunk_idx,
            )

            result = await self._process_chunk_with_retry(task, chunk, embedder, indexer)

            if result['skipped']:
                ctx.counters['chunks_skipped'] += 1
            elif result['success']:
                ctx.counters['chunks_processed'] += 1
            else:
                ctx.counters['chunks_error'] += 1
                logger.error(f'Chunk processing failed: {result.get("error")}')

            # Update progress
            with contextlib.suppress(Exception):
                self.phase_repo.update_progress(
                    ctx.job_id, 'embedding', items_processed=ctx.counters['chunks_processed']
                )
                self.phase_repo.update_progress(
                    ctx.job_id, 'indexing', items_processed=ctx.counters['chunks_processed']
                )
        return True

    async def _mark_job_complete(
        self, job_id: str, phases_started: dict[str, bool], counters: dict[str, int]
    ) -> None:
        """Finishing job and marking all phases complete."""
        with contextlib.suppress(Exception):
            self.phase_repo.complete_phase(job_id, 'loading')
            if phases_started['chunking']:
                self.phase_repo.complete_phase(job_id, 'chunking')
            if phases_started['embedding']:
                self.phase_repo.complete_phase(job_id, 'embedding')
            if phases_started['indexing']:
                self.phase_repo.complete_phase(job_id, 'indexing')

        self.repo.set_job_status(
            job_id,
            status='completed',
            finished_at=datetime.now(timezone.utc),
            last_error=None,
        )
        logger.info(f'Ingestion completed: job_id={job_id}, counters={counters}')

    async def _process_chunk_with_retry(
        self, task: ProcessingTask, chunk: Any, embedder: Embedder, indexer: Indexer
    ) -> dict[str, Any]:
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
            logger.debug(f'Chunk {chunk.content_hash[:8]} already indexed, skipping')
            return {'success': True, 'skipped': True}

        # Try embed + index with retry
        attempt = 0
        while True:
            attempt += 1
            try:
                # Embed
                embedding = await embedder.embed(chunk)

                # Index
                await asyncio.to_thread(indexer.index, task.kb_id, embedding)

                return {'success': True, 'skipped': False}

            except Exception as e:  # noqa: BLE001
                if self.retry_policy.should_retry(attempt, e):
                    delay = self.retry_policy.get_backoff_delay(attempt)
                    logger.warning(
                        f'Chunk {chunk.content_hash[:8]} attempt {attempt} failed: {e}. '
                        f'Retrying in {delay}s...'
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f'Chunk {chunk.content_hash[:8]} failed after {attempt} attempts: {e}'
                    )
                    return {'success': False, 'skipped': False, 'error': str(e)}

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
            if status == 'paused':
                logger.info(f'Job {job_id} paused, waiting...')
                await asyncio.sleep(1)  # Backoff and re-check
            elif status == 'canceled':
                logger.info(f'Job {job_id} canceled, running cleanup...')
                await self._cleanup_job(job_id, kb_id, indexer)
                return False
            elif status in ('failed', 'completed'):
                logger.info(f'Job {job_id} already {status}, stopping')
                return False
            else:
                logger.warning(f"Unknown job status '{status}', treating as failed")
                return False

    async def _cleanup_job(self, job_id: str, kb_id: str, indexer: Indexer) -> None:
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
            logger.info(f'Deleted indexed data for job {job_id}')

            # Reset job state
            self.repo.update_job(
                job_id,
                status='not_started',
                checkpoint=None,
                counters=None,
                finished_at=datetime.now(timezone.utc),
                last_error='Canceled by user',
            )
            logger.info(f'Reset job {job_id} to not_started')

        except Exception as e:
            # Log but don't crash
            logger.error(f'Cleanup failed for job {job_id}: {e}', exc_info=True)
