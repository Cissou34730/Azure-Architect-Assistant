"""Runtime orchestration for ingestion jobs."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.features.ingestion.application.job_lifecycle import JobLifecycleManager
from app.features.ingestion.application.orchestrator import (
    IngestionOrchestrator,
    RetryPolicy,
    WorkflowDefinition,
)
from app.features.ingestion.application.shutdown_manager import ShutdownManager
from app.features.ingestion.domain.indexing.indexer import Indexer
from app.features.ingestion.infrastructure import create_job_repository
from app.features.knowledge.infrastructure import KBManager
from app.shared.config.app_settings import get_app_settings

logger = logging.getLogger(__name__)


class IngestionRuntimeService:
    """Manages ingestion task lifecycle and graceful shutdown behavior."""

    def __init__(self, *, repo: Any | None = None) -> None:
        self.repo = repo if repo is not None else create_job_repository()
        self._lifecycle = JobLifecycleManager(self.repo)
        self.shutdown_manager = ShutdownManager()
        self._running_tasks: dict[str, asyncio.Task[Any]] = {}

    async def run_orchestrator_background(
        self, job_id: str, kb_id: str, kb_config: dict[str, Any]
    ) -> None:
        orchestrator = IngestionOrchestrator(
            repo=self.repo,
            workflow=WorkflowDefinition(),
            retry_policy=RetryPolicy(max_attempts=3),
            shutdown_manager=self.shutdown_manager,
            lifecycle_manager=self._lifecycle,
        )
        try:
            await orchestrator.run(job_id, kb_id, kb_config)
        except asyncio.CancelledError:
            logger.warning("Orchestrator task cancelled for job %s - pausing", job_id)
            self._lifecycle.pause(job_id)
            raise
        except Exception as exc:
            logger.exception("Orchestrator failed for job %s: %s", job_id, exc)
        finally:
            self._running_tasks.pop(job_id, None)

    async def start_ingestion(self, kb_id: str, kb_manager: KBManager) -> dict[str, Any]:
        if not kb_manager.kb_exists(kb_id):
            raise HTTPException(
                status_code=404, detail=f"Knowledge base '{kb_id}' not found"
            )

        kb_config = kb_manager.get_kb_config(kb_id)
        kb_config["kb_id"] = kb_id
        source_type = kb_config.get("source_type", "unknown")
        source_config = kb_config.get("source_config", {})

        job_id = self.repo.create_job(
            kb_id=kb_id,
            source_type=source_type,
            source_config=source_config,
            priority=0,
        )

        task = asyncio.create_task(self.run_orchestrator_background(job_id, kb_id, kb_config))
        task.set_name(f"ingestion-{kb_id}-{job_id}")
        self._running_tasks[job_id] = task

        logger.info("Started ingestion job %s for KB %s", job_id, kb_id)
        return {
            "job_id": job_id,
            "kb_id": kb_id,
            "status": "running",
            "started_at": datetime.now(timezone.utc),
        }

    async def pause_ingestion(self, kb_id: str) -> dict[str, Any]:
        job_id = self.repo.get_latest_job_id(kb_id)
        if not job_id:
            raise HTTPException(status_code=404, detail=f"No job found for KB '{kb_id}'")

        task = self._running_tasks.get(job_id)
        if not task:
            self._lifecycle.pause(job_id)
            return {"status": "paused", "job_id": job_id, "message": "Job was not running"}

        self.shutdown_manager.request_shutdown(job_id)
        try:
            await asyncio.wait_for(task, timeout=get_app_settings().ingestion_shutdown_timeout)
        except asyncio.TimeoutError:
            logger.warning("Task for job %s did not stop within 5 seconds", job_id)
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        except asyncio.CancelledError:
            pass

        return {
            "status": "paused",
            "job_id": job_id,
            "kb_id": kb_id,
            "message": "Job paused successfully",
        }

    async def resume_ingestion(self, kb_id: str, kb_manager: KBManager) -> dict[str, str]:
        job_id = self.repo.get_latest_job_id(kb_id)
        if not job_id:
            raise HTTPException(status_code=404, detail=f"No job found for KB '{kb_id}'")

        status = self.repo.get_job_status(job_id)
        if status != "paused":
            return {
                "status": status,
                "job_id": job_id,
                "kb_id": kb_id,
                "message": f"Job is {status}, not paused",
            }

        if job_id in self._running_tasks:
            return {
                "status": "running",
                "job_id": job_id,
                "kb_id": kb_id,
                "message": "Job already running",
            }

        if not kb_manager.kb_exists(kb_id):
            raise HTTPException(
                status_code=404, detail=f"Knowledge base '{kb_id}' not found"
            )

        kb_config = kb_manager.get_kb_config(kb_id)
        kb_config["kb_id"] = kb_id
        self._lifecycle.mark_running(job_id)

        task = asyncio.create_task(self.run_orchestrator_background(job_id, kb_id, kb_config))
        task.set_name(f"ingestion-{kb_id}-{job_id}-resumed")
        self._running_tasks[job_id] = task

        return {
            "status": "running",
            "job_id": job_id,
            "kb_id": kb_id,
            "message": "Job resumed successfully",
        }

    async def cancel_ingestion(self, kb_id: str) -> dict[str, str]:
        job_id = self.repo.get_latest_job_id(kb_id)
        if not job_id:
            raise HTTPException(status_code=404, detail=f"No job found for KB '{kb_id}'")

        self._lifecycle.request_cancel(job_id)

        try:
            task = self._running_tasks.get(job_id)
            if task and not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError, asyncio.TimeoutError):
                    await asyncio.wait_for(task, timeout=get_app_settings().ingestion_cancel_timeout)

            indexer = Indexer(kb_id=kb_id)
            self._lifecycle.cleanup_canceled_job(job_id, kb_id, indexer)
        except Exception as cleanup_error:
            logger.error("Cleanup failed for job %s: %s", job_id, cleanup_error, exc_info=True)

        return {"status": "canceled", "job_id": job_id, "kb_id": kb_id}

    async def cleanup_running_tasks(self) -> None:
        logger.warning("=" * 80)
        logger.warning("cleanup_running_tasks: %d active", len(self._running_tasks))
        logger.warning("=" * 80)

        if not self._running_tasks:
            logger.warning("No running tasks to clean up")
            return

        tasks_snapshot = list(self._running_tasks.items())
        self.shutdown_manager.request_shutdown()

        for job_id, _ in tasks_snapshot:
            try:
                self._lifecycle.pause(job_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not mark job %s as paused: %s", job_id, exc)

        await asyncio.sleep(get_app_settings().ingestion_drain_sleep)

        pending: list[tuple[str, asyncio.Task[Any]]] = []
        for job_id, task in tasks_snapshot:
            if task.done():
                self._running_tasks.pop(job_id, None)
                continue
            task.cancel()
            pending.append((job_id, task))

        if pending:
            done, _ = await asyncio.wait(
                [task for _, task in pending],
                timeout=5.0,
                return_when=asyncio.ALL_COMPLETED,
            )
            for job_id, task in pending:
                if task in done:
                    self._running_tasks.pop(job_id, None)

        logger.warning("cleanup_running_tasks COMPLETE")

