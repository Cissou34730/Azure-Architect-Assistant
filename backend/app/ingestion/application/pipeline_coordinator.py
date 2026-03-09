from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.ingestion.application.job_gate import JobGate
from app.ingestion.application.job_lifecycle import BatchProgress, JobLifecycleManager
from app.ingestion.application.pipeline_components import PipelineComponents
from app.ingestion.application.pipeline_stage import PipelineContext
from app.ingestion.application.policies import RetryPolicy
from app.ingestion.application.stages.chunking_stage import ChunkingStage
from app.ingestion.application.stages.embedding_stage import (
    EmbeddingIndexingStage,
    EmbeddingProcessingDeps,
)
from app.ingestion.application.stages.loading_stage import LoadingStage
from app.ingestion.domain.errors import PhaseNotFoundError, PhaseRepositoryError
from app.ingestion.domain.indexing import Indexer
from app.ingestion.infrastructure.phase_repository import PhaseRepository

logger = logging.getLogger(__name__)

_END_OF_LOADER = object()


@dataclass(frozen=True)
class PipelineRunRequest:
    job_id: str
    kb_id: str
    kb_config: dict[str, Any]
    components: PipelineComponents
    checkpoint: dict[str, Any]
    counters: dict[str, int]


def _next_or_end(iterator: Any) -> Any:
    try:
        return next(iterator)
    except StopIteration:
        return _END_OF_LOADER


class PipelineCoordinator:
    def __init__(
        self,
        phase_repo: PhaseRepository,
        job_gate: JobGate,
        lifecycle: JobLifecycleManager,
        is_shutdown_requested: Callable[[], bool],
        retry_policy: RetryPolicy,
    ) -> None:
        self._phase_repo = phase_repo
        self._job_gate = job_gate
        self._lifecycle = lifecycle
        self._is_shutdown_requested = is_shutdown_requested
        self._retry_policy = retry_policy

    async def run(
        self,
        request: PipelineRunRequest,
    ) -> None:
        start_batch_id = int(request.checkpoint.get('last_batch_id', -1)) + 1

        phases_started: dict[str, bool] = {'chunking': False, 'embedding': False, 'indexing': False}
        pipeline_context = PipelineContext(
            kb_id=request.kb_id,
            job_id=request.job_id,
            config=request.kb_config,
            checkpoint=request.checkpoint,
            counters=request.counters,
            results={'phases_started': phases_started},
        )

        loading_stage = LoadingStage(self._phase_repo)
        chunking_stage = ChunkingStage(self._phase_repo, request.components.chunker)
        embedding_stage = EmbeddingIndexingStage(
            phase_repo=self._phase_repo,
            lifecycle=self._lifecycle,
            processing_deps=EmbeddingProcessingDeps(
                retry_policy=self._retry_policy,
                embedder=request.components.embedder,
                indexer=request.components.indexer,
                gate_check=self._job_gate.check,
                is_shutdown_requested=self._is_shutdown_requested,
            ),
        )

        batch_id = start_batch_id
        while True:
            batch = await asyncio.to_thread(_next_or_end, request.components.loader)
            if batch is _END_OF_LOADER:
                logger.info('Loader exhausted', extra={'kb_id': request.kb_id, 'job_id': request.job_id, 'last_batch_id': batch_id - 1})
                break

            pipeline_context.set_batch_state(
                batch=batch,
                batch_id=batch_id,
                resume_active_batch=self._lifecycle.is_resuming_batch(request.checkpoint, batch_id),
                resume_chunk_index=self._lifecycle.get_resume_chunk_index(request.checkpoint, batch_id),
            )

            if self._is_shutdown_requested():
                logger.warning('Shutdown requested - pausing job at batch', extra={'job_id': request.job_id, 'batch_id': batch_id})
                self._lifecycle.pause(request.job_id, request.checkpoint, request.counters)
                return

            if not await self._job_gate.check(request.job_id, request.kb_id, request.components.indexer):
                logger.info('Pipeline stopped at gate check', extra={'job_id': request.job_id, 'batch_id': batch_id})
                return

            await loading_stage.execute(pipeline_context)
            await chunking_stage.execute(pipeline_context)

            if not pipeline_context.is_resuming_batch():
                chunks = pipeline_context.require_chunks()
                self._lifecycle.mark_batch_started(
                    request.job_id,
                    request.checkpoint,
                    request.counters,
                    batch=BatchProgress(
                        batch_id=batch_id,
                        document_count=len(pipeline_context.require_batch()),
                        chunk_count=len(chunks),
                    ),
                )

            await embedding_stage.execute(pipeline_context)
            if not pipeline_context.should_continue():
                return

            await asyncio.to_thread(request.components.indexer.persist)

            self._lifecycle.mark_batch_completed(
                request.job_id,
                request.checkpoint,
                request.counters,
                batch_id=batch_id,
                heartbeat=True,
            )
            batch_id += 1

        await self._mark_job_complete(
            request.job_id,
            phases_started,
            request.counters,
            request.components.indexer,
        )

    async def _mark_job_complete(
        self,
        job_id: str,
        phases_started: dict[str, bool],
        counters: dict[str, int],
        indexer: Indexer | None = None,
    ) -> None:
        if indexer:
            try:
                await asyncio.to_thread(indexer.persist)
            except Exception:
                logger.error('Failed to persist index on job completion', extra={'job_id': job_id}, exc_info=True)

        docs_seen = int(counters.get('docs_seen', 0) or 0)
        chunks_seen = int(counters.get('chunks_seen', 0) or 0)
        chunks_processed = int(counters.get('chunks_processed', 0) or 0)

        if docs_seen == 0 and chunks_seen == 0 and chunks_processed == 0:
            message = 'No documents were loaded from the configured source.'
            try:
                self._phase_repo.fail_phase(job_id, 'loading', error_message=message)
            except (PhaseNotFoundError, PhaseRepositoryError):
                logger.warning('Failed to mark loading phase failed (non-critical)', extra={'job_id': job_id})

            self._lifecycle.mark_failed(job_id, message)
            return

        for phase_name in ('loading', 'chunking', 'embedding', 'indexing'):
            should_complete = phase_name == 'loading' or bool(phases_started.get(phase_name))
            if should_complete:
                try:
                    self._phase_repo.complete_phase(job_id, phase_name)
                except (PhaseNotFoundError, PhaseRepositoryError):
                    logger.warning('Failed to complete phase (non-critical)', extra={'job_id': job_id, 'phase_name': phase_name})

        self._lifecycle.mark_completed(job_id)
