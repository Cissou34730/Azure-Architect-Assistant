from __future__ import annotations

import logging

from app.ingestion.application.pipeline_stage import PipelineContext
from app.ingestion.infrastructure.job_repository import JobRepository

logger = logging.getLogger(__name__)


def pause_job_at_batch_chunk(
    repo: JobRepository, context: PipelineContext, batch_id: int, chunk_idx: int
) -> None:
    logger.warning(
        'Shutdown requested - pausing job at batch/chunk',
        extra={'job_id': context.job_id, 'batch_id': batch_id, 'chunk_idx': chunk_idx},
    )
    context.checkpoint['last_batch_id'] = batch_id - 1
    repo.set_job_status(context.job_id, status='paused')
    repo.update_job(context.job_id, checkpoint=context.checkpoint, counters=context.counters)
    context.results['continue'] = False


def stop_job_at_gate(repo: JobRepository, context: PipelineContext, batch_id: int) -> None:
    context.checkpoint['last_batch_id'] = batch_id - 1
    repo.update_job(context.job_id, checkpoint=context.checkpoint, counters=context.counters)
    context.results['continue'] = False
