from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.features.ingestion.application.chunk_processor import ChunkProcessor
from app.features.ingestion.application.job_lifecycle import JobLifecycleManager
from app.features.ingestion.application.phase_tracking import (
    start_phase_noncritical,
    update_progress_noncritical,
)
from app.features.ingestion.application.pipeline_stage import PipelineContext, PipelineStage
from app.features.ingestion.application.policies import RetryPolicy, StepName
from app.features.ingestion.application.tasks import ProcessingTask
from app.features.ingestion.domain.embedding import Embedder
from app.features.ingestion.domain.indexing import Indexer
from app.features.ingestion.infrastructure.phase_repository import PhaseRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmbeddingProcessingDeps:
    retry_policy: RetryPolicy
    embedder: Embedder
    indexer: Indexer
    gate_check: Callable[[str, str, Indexer], Awaitable[bool]]
    is_shutdown_requested: Callable[[], bool]


class EmbeddingIndexingStage(PipelineStage):
    def __init__(
        self,
        phase_repo: PhaseRepository,
        lifecycle: JobLifecycleManager,
        processing_deps: EmbeddingProcessingDeps,
    ) -> None:
        self._phase_repo = phase_repo
        self._lifecycle = lifecycle
        self._chunk_processor = ChunkProcessor(
            retry_policy=processing_deps.retry_policy,
            embedder=processing_deps.embedder,
            indexer=processing_deps.indexer,
        )
        self._indexer = processing_deps.indexer
        self._gate_check = processing_deps.gate_check
        self._is_shutdown_requested = processing_deps.is_shutdown_requested

    def get_stage_name(self) -> str:
        return 'embedding_indexing'

    async def execute(self, context: PipelineContext) -> None:
        chunks = context.require_chunks()
        phases_started = context.phases_started()

        if not phases_started.get('embedding'):
            start_phase_noncritical(self._phase_repo, context.job_id, 'embedding')
            phases_started['embedding'] = True
        if not phases_started.get('indexing'):
            start_phase_noncritical(self._phase_repo, context.job_id, 'indexing')
            phases_started['indexing'] = True

        batch_id = context.get_batch_id()
        resume_chunk_index = context.get_resume_chunk_index()

        for chunk_idx, chunk in enumerate(chunks):
            if chunk_idx <= resume_chunk_index:
                continue

            if self._is_shutdown_requested():
                self._lifecycle.pause(context.job_id, context.checkpoint, context.counters)
                context.mark_should_continue(False)
                return

            if not await self._gate_check(context.job_id, context.kb_id, self._indexer):
                self._lifecycle.persist_progress(context.job_id, context.checkpoint, context.counters)
                context.mark_should_continue(False)
                return

            task = ProcessingTask(
                job_id=context.job_id,
                kb_id=context.kb_id,
                step=StepName.EMBED,
                payload={'chunk': chunk},
                batch_id=batch_id,
                chunk_index=chunk_idx,
            )

            result = await self._chunk_processor.process_chunk(task, chunk)

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
            self._lifecycle.record_chunk_progress(
                context.job_id,
                context.checkpoint,
                context.counters,
                batch_id=batch_id,
                chunk_index=chunk_idx,
            )

        context.mark_should_continue(True)

