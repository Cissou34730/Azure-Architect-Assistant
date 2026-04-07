from __future__ import annotations

import asyncio
import logging
from typing import Any, cast

from app.features.ingestion.application.phase_tracking import (
    start_phase_noncritical,
    update_progress_noncritical,
)
from app.features.ingestion.application.pipeline_stage import PipelineContext, PipelineStage
from app.features.ingestion.domain.chunking.adapter import chunk_documents_to_chunks
from app.features.ingestion.infrastructure.phase_repository import PhaseRepository

logger = logging.getLogger(__name__)


class ChunkingStage(PipelineStage):
    def __init__(self, phase_repo: PhaseRepository, chunker: Any):
        self._phase_repo = phase_repo
        self._chunker = chunker

    def get_stage_name(self) -> str:
        return 'chunking'

    async def execute(self, context: PipelineContext) -> None:
        batch = context.require_batch()
        phases_started = context.phases_started()

        chunks = await asyncio.to_thread(chunk_documents_to_chunks, batch, self._chunker, context.kb_id)
        chunks_list = cast(list[Any], chunks)

        if not context.is_resuming_batch():
            context.counters['chunks_seen'] = int(context.counters.get('chunks_seen', 0)) + len(chunks_list)
        context.set_chunks(chunks_list)

        start_phase_noncritical(self._phase_repo, context.job_id, 'chunking')
        phases_started['chunking'] = True
        update_progress_noncritical(
            self._phase_repo,
            context.job_id,
            'chunking',
            items_processed=context.counters['chunks_seen'],
        )

