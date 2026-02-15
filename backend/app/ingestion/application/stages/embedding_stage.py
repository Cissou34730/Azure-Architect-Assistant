from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from app.ingestion.application.chunk_processor import ChunkProcessor
from app.ingestion.application.phase_tracking import (
    start_phase_noncritical,
    update_progress_noncritical,
)
from app.ingestion.application.pipeline_control import pause_job_at_batch_chunk, stop_job_at_gate
from app.ingestion.application.pipeline_stage import PipelineContext, PipelineStage
from app.ingestion.application.policies import RetryPolicy, StepName
from app.ingestion.application.tasks import ProcessingTask
from app.ingestion.domain.embedding import Embedder
from app.ingestion.domain.indexing import Indexer
from app.ingestion.infrastructure.job_repository import JobRepository
from app.ingestion.infrastructure.phase_repository import PhaseRepository

logger = logging.getLogger(__name__)

class EmbeddingStage(PipelineStage):
    def __init__(
        self,
        repo: JobRepository,
        phase_repo: PhaseRepository,
        retry_policy: RetryPolicy,
        embedder: Embedder,
        indexer: Indexer,
        gate_check: Callable[[str, str, Indexer], Awaitable[bool]],
        is_shutdown_requested: Callable[[], bool],
    ) -> None:
        self._repo = repo
        self._phase_repo = phase_repo
        self._chunk_processor = ChunkProcessor(retry_policy=retry_policy, embedder=embedder, indexer=indexer)
        self._indexer = indexer
        self._gate_check = gate_check
        self._is_shutdown_requested = is_shutdown_requested

    def get_stage_name(self) -> str:
        return 'embedding_indexing'

    async def execute(self, context: PipelineContext) -> None:
        chunks = context.results.get('chunks')
        if not isinstance(chunks, list):
            raise TypeError('EmbeddingStage requires context.results["chunks"] to be a list')

        phases_started = context.results.get('phases_started')
        if not isinstance(phases_started, dict):
            phases_started = {'chunking': False, 'embedding': False, 'indexing': False}
            context.results['phases_started'] = phases_started

        if not phases_started.get('embedding'):
            start_phase_noncritical(self._phase_repo, context.job_id, 'embedding')
            phases_started['embedding'] = True
        if not phases_started.get('indexing'):
            start_phase_noncritical(self._phase_repo, context.job_id, 'indexing')
            phases_started['indexing'] = True

        batch_id = int(context.results.get('batch_id', 0) or 0)

        for chunk_idx, chunk in enumerate(chunks):
            if self._is_shutdown_requested():
                pause_job_at_batch_chunk(self._repo, context, batch_id, chunk_idx)
                return

            if not await self._gate_check(context.job_id, context.kb_id, self._indexer):
                stop_job_at_gate(self._repo, context, batch_id)
                return

            task = ProcessingTask(
                job_id=context.job_id,
                kb_id=context.kb_id,
                step=StepName.EMBED,
                payload={'chunk': chunk},
                batch_id=batch_id,
                chunk_index=chunk_idx,
            )

            result = await self._chunk_processor.process(task, chunk)

            if result['skipped']:
                context.counters['chunks_skipped'] = int(context.counters.get('chunks_skipped', 0)) + 1
            elif result['success']:
                context.counters['chunks_processed'] = int(context.counters.get('chunks_processed', 0)) + 1
            else:
                context.counters['chunks_error'] = int(context.counters.get('chunks_error', 0)) + 1
                logger.error('Chunk processing failed', extra={'error': result.get('error')})

            update_progress_noncritical(
                self._phase_repo,
                context.job_id,
                'embedding',
                items_processed=context.counters['chunks_processed'],
            )
            update_progress_noncritical(
                self._phase_repo,
                context.job_id,
                'indexing',
                items_processed=context.counters['chunks_processed'],
            )

        context.results['continue'] = True
