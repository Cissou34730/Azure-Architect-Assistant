from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.ingestion.application.policies import RetryPolicy
from app.ingestion.application.tasks import ProcessingTask
from app.ingestion.domain.embedding import Embedder
from app.ingestion.domain.indexing import Indexer

logger = logging.getLogger(__name__)


class ChunkProcessor:
    def __init__(self, retry_policy: RetryPolicy, embedder: Embedder, indexer: Indexer) -> None:
        self._retry_policy = retry_policy
        self._embedder = embedder
        self._indexer = indexer

    async def process(self, task: ProcessingTask, chunk: Any) -> dict[str, Any]:
        exists = await asyncio.to_thread(self._indexer.exists, task.kb_id, chunk.content_hash)
        if exists:
            logger.debug('Chunk already indexed, skipping', extra={'content_hash': chunk.content_hash[:8]})
            return {'success': True, 'skipped': True}

        attempt = 0
        while True:
            attempt += 1
            try:
                embedding = await self._embedder.embed(chunk)
                await asyncio.to_thread(self._indexer.index, task.kb_id, embedding)
                return {'success': True, 'skipped': False}
            except Exception as exc:
                if self._retry_policy.should_retry(attempt, exc):
                    delay = self._retry_policy.get_backoff_delay(attempt)
                    logger.warning(
                        'Chunk attempt failed; retrying',
                        extra={
                            'content_hash': getattr(chunk, 'content_hash', '')[:8],
                            'attempt': attempt,
                            'delay_s': delay,
                            'error_type': type(exc).__name__,
                        },
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        'Chunk failed after retries',
                        extra={
                            'content_hash': getattr(chunk, 'content_hash', '')[:8],
                            'attempts': attempt,
                            'error_type': type(exc).__name__,
                        },
                        exc_info=True,
                    )
                    return {'success': False, 'skipped': False, 'error': str(exc)}
