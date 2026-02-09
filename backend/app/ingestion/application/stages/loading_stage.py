from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.ingestion.application.phase_tracking import update_progress_noncritical
from app.ingestion.application.pipeline_stage import PipelineContext, PipelineStage
from app.ingestion.application.storage import save_documents_to_disk
from app.ingestion.infrastructure.phase_repository import PhaseRepository

logger = logging.getLogger(__name__)


class LoadingStage(PipelineStage):
    def __init__(self, phase_repo: PhaseRepository):
        self._phase_repo = phase_repo

    def get_stage_name(self) -> str:
        return 'loading'

    async def execute(self, context: PipelineContext) -> None:
        batch = context.results.get('batch')
        if not isinstance(batch, list):
            raise TypeError('LoadingStage requires context.results["batch"] to be a list')

        await asyncio.to_thread(save_documents_to_disk, context.kb_id, batch)

        context.counters['docs_seen'] = int(context.counters.get('docs_seen', 0)) + len(batch)
        update_progress_noncritical(
            self._phase_repo,
            context.job_id,
            'loading',
            items_processed=context.counters['docs_seen'],
        )
