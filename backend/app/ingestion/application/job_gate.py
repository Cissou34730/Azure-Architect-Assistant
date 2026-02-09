from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.ingestion.domain.indexing import Indexer
from app.ingestion.infrastructure.job_repository import JobRepository

logger = logging.getLogger(__name__)


class JobGate:
    def __init__(self, repo: JobRepository) -> None:
        self._repo = repo

    async def check(self, job_id: str, kb_id: str, indexer: Indexer) -> bool:
        while True:
            status = self._repo.get_job_status(job_id)

            if status == 'running':
                return True
            if status == 'paused':
                logger.info('Job paused, waiting', extra={'job_id': job_id})
                await asyncio.sleep(1)
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
            indexer.delete_by_job(job_id, kb_id)
            logger.info('Deleted indexed data for canceled job', extra={'job_id': job_id})

            self._repo.set_job_status(
                job_id,
                status='not_started',
                finished_at=datetime.now(timezone.utc),
                last_error='Canceled by user',
            )
            self._repo.update_job(job_id, checkpoint=None, counters=None)
        except Exception as exc:  # noqa: BLE001
            logger.error('Cleanup failed for canceled job', extra={'job_id': job_id}, exc_info=True)
