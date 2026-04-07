from __future__ import annotations

import asyncio
import logging

from app.features.ingestion.application.job_lifecycle import JobLifecycleManager
from app.features.ingestion.domain.indexing import Indexer
from app.features.ingestion.infrastructure.job_repository import JobRepository
from app.shared.config.app_settings import get_app_settings

logger = logging.getLogger(__name__)


class JobGate:
    def __init__(self, repo: JobRepository, lifecycle: JobLifecycleManager) -> None:
        self._repo = repo
        self._lifecycle = lifecycle

    async def check(self, job_id: str, kb_id: str, indexer: Indexer) -> bool:
        while True:
            status = self._repo.get_job_status(job_id)

            if status == 'running':
                return True
            if status == 'paused':
                logger.info('Job paused, waiting', extra={'job_id': job_id})
                await asyncio.sleep(get_app_settings().job_gate_poll_interval)
            elif status == 'canceled':
                logger.info('Job canceled, running cleanup', extra={'job_id': job_id})
                await self._cleanup(job_id, kb_id, indexer)
                return False
            elif status in ('failed', 'completed'):
                logger.info('Job already terminal, stopping', extra={'job_id': job_id, 'status': status})
                return False
            else:
                logger.warning('Unknown job status; stopping', extra={'job_id': job_id, 'status': status})
                return False

    async def _cleanup(self, job_id: str, kb_id: str, indexer: Indexer) -> None:
        try:
            self._lifecycle.cleanup_canceled_job(job_id, kb_id, indexer)
        except Exception:
            logger.error('Cleanup failed for canceled job', extra={'job_id': job_id}, exc_info=True)

