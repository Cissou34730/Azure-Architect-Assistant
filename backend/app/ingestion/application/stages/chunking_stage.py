from __future__ import annotations

import asyncio
import logging
from typing import Any, cast

from app.ingestion.application.phase_tracking import (
    start_phase_noncritical,
    update_progress_noncritical,
)
from app.ingestion.application.pipeline_stage import PipelineContext, PipelineStage
from app.ingestion.domain.chunking.adapter import chunk_documents_to_chunks
from app.ingestion.infrastructure.phase_repository import PhaseRepository

logger = logging.getLogger(__name__)


class ChunkingStage(PipelineStage):
    def __init__(self, phase_repo: PhaseRepository, chunker: Any):
        self._phase_repo = phase_repo
        self._chunker = chunker

    def get_stage_name(self) -> str:
        return 'chunking'

    async def execute(self, context: PipelineContext) -> None:
        batch = context.results.get('batch')
        if not isinstance(batch, list):
            raise TypeError('ChunkingStage requires context.results["batch"] to be a list')

        phases_started = context.results.get('phases_started')
        if not isinstance(phases_started, dict):
            phases_started = {'chunking': False, 'embedding': False, 'indexing': False}
            context.results['phases_started'] = phases_started

        chunks = await asyncio.to_thread(chunk_documents_to_chunks, batch, self._chunker, context.kb_id)
        chunks_list = cast(list[Any], chunks)

        context.counters['chunks_seen'] = int(context.counters.get('chunks_seen', 0)) + len(chunks_list)
        context.results['chunks'] = chunks_list

        start_phase_noncritical(self._phase_repo, context.job_id, 'chunking')
        phases_started['chunking'] = True
        update_progress_noncritical(
            self._phase_repo,
            context.job_id,
            'chunking',
            items_processed=context.counters['chunks_seen'],
        )
