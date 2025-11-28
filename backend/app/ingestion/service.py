import asyncio
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class IngestionState:
    kb_id: str
    status: str = "pending"  # pending | running | paused | completed | failed | cancelled
    phase: str = "crawling"
    progress: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    error: Optional[str] = None
    paused: bool = False
    cancel_requested: bool = False


class IngestionService:
    _instance: Optional["IngestionService"] = None

    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._states: Dict[str, IngestionState] = {}
        self._lock = asyncio.Lock()
        # Filesystem storage root
        import os
        from pathlib import Path
        self._root = Path(__file__).parent.parent / "data" / "ingestion" / "jobs"
        try:
            self._root.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    @classmethod
    def instance(cls) -> "IngestionService":
        if not cls._instance:
            cls._instance = IngestionService()
        return cls._instance

    def _get_state(self, kb_id: str) -> Optional[IngestionState]:
        return self._states.get(kb_id)

    async def start(self, kb_id: str, run_callable, *args, **kwargs) -> IngestionState:
        async with self._lock:
            if kb_id in self._tasks and not self._tasks[kb_id].done():
                return self._states[kb_id]

            state = IngestionState(kb_id=kb_id, status="running", phase="crawling", progress=0)
            self._states[kb_id] = state
            # Persist initial state and update index
            self._persist_state(state)
            self._update_index(kb_id)

            async def worker():
                try:
                    # Run blocking pipeline in a thread, passing state for cooperative checks
                    await asyncio.to_thread(run_callable, *args, **kwargs)
                    if not state.cancel_requested:
                        state.status = "COMPLETED"
                        state.phase = "DONE"
                        state.message = "Ingestion completed"
                    state.error = None
                    self._persist_state(state)
                except asyncio.CancelledError:
                    state.status = "cancelled"
                    state.message = "Ingestion cancelled"
                    self._persist_state(state)
                    raise
                except Exception as e:
                    logger.error(f"Ingestion failed for {kb_id}: {e}", exc_info=True)
                    state.status = "failed"
                    state.error = str(e)
                    state.message = "Ingestion failed"
                    self._persist_state(state)
                finally:
                    # Task is finished; leave state for inspection
                    pass

            task = asyncio.create_task(worker(), name=f"ingest:{kb_id}")
            self._tasks[kb_id] = task
            return state

    async def pause(self, kb_id: str) -> bool:
        state = self._get_state(kb_id)
        if not state:
            return False
        
        # Only allow pausing if job is currently running
        if state.status != "running":
            return False
        
        state.paused = True
        state.status = "paused"
        state.message = "Paused by user"
        self._persist_state(state)
        return True

    async def resume(self, kb_id: str) -> bool:
        state = self._get_state(kb_id)
        if not state:
            return False
        
        # Only allow resuming if job is currently paused
        if state.status != "paused":
            return False
        
        state.paused = False
        state.status = "running"
        state.message = "Resumed by user"
        self._persist_state(state)
        return True

    async def cancel(self, kb_id: str) -> bool:
        state = self._get_state(kb_id)
        if not state:
            return False
        
        # Only allow cancellation if job is running, pending, or paused
        if state.status not in ("running", "pending", "paused"):
            return False
        
        state.cancel_requested = True
        
        # Cancel the task if it exists
        task = self._tasks.get(kb_id)
        if task and not task.done():
            try:
                task.cancel()
            except Exception:
                pass
        
        state.status = "cancelled"
        state.message = "Cancellation requested"
        self._persist_state(state)
        return True

    def status(self, kb_id: str) -> Optional[IngestionState]:
        return self._states.get(kb_id)

    def list_kb_states(self) -> Dict[str, IngestionState]:
        return self._states.copy()

    async def cancel_all(self):
        for job_id, state in self._states.items():
            state.cancel_requested = True
            self._persist_state(state)
        for job_id, task in list(self._tasks.items()):
            if task and not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=2.0)
                except Exception:
                    pass

    # ------------------------
    # Filesystem persistence
    # ------------------------
    def _state_path(self, kb_id: str):
        from pathlib import Path
        return self._root / f"{kb_id}.json"

    def _index_path(self):
        return self._root / "index.json"

    def _persist_state(self, state: IngestionState):
        import json, tempfile, os
        path = self._state_path(state.kb_id)
        snapshot = {
            "kb_id": state.kb_id,
            "status": state.status,
            "phase": state.phase,
            "progress": state.progress,
            "message": state.message,
            "error": state.error,
            "metrics": state.metrics,
        }
        try:
            tmp_fd, tmp_name = tempfile.mkstemp(dir=str(self._root), prefix=f"{state.kb_id}.", suffix=".tmp")
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(snapshot, f)
            os.replace(tmp_name, str(path))
        except Exception as e:
            logger.warning(f"Failed to persist state {state.kb_id}: {e}")

    async def resume_or_start(self, kb_id: str, run_callable, *args, **kwargs) -> bool:
        """If a task exists and is paused, resume it; otherwise, start a new task.
        Returns True on success, False if unable to resume/start.
        """
        async with self._lock:
            state = self._get_state(kb_id)
            task = self._tasks.get(kb_id)
            # If task exists and is paused, flip flags
            if state and state.status == "paused" and task and not task.done():
                state.paused = False
                state.status = "running"
                state.message = "Resumed by user"
                self._persist_state(state)
                return True
            # If no active task, (re)start from checkpoint
            started_state = await self.start(kb_id, run_callable, *args, **kwargs)
            return started_state is not None

    def _update_index(self, kb_id: str):
        import json
        idx_path = self._index_path()
        data = {}
        try:
            if idx_path.exists():
                data = json.loads(idx_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        data[kb_id] = kb_id
        try:
            idx_path.write_text(json.dumps(data), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to update index for {kb_id}: {e}")

    def load_all_states(self):
        import json
        from pathlib import Path
        try:
            for p in self._root.glob("*.json"):
                if p.name == "index.json":
                    continue
                try:
                    snapshot = json.loads(p.read_text(encoding="utf-8"))
                    state = IngestionState(
                        kb_id=snapshot.get("kb_id") or p.stem,
                        status=snapshot.get("status", "pending"),
                        phase=snapshot.get("phase", "crawling"),
                        progress=int(snapshot.get("progress", 0)),
                        message=snapshot.get("message", ""),
                        error=snapshot.get("error"),
                        metrics=snapshot.get("metrics", {}),
                    )
                    # Mark paused/cancel flags false on load
                    state.paused = False
                    state.cancel_requested = False
                    
                    # Enrich metrics from KB checkpoints (single source of truth)
                    try:
                        kb_root = Path(__file__).parent.parent / "data" / "knowledge_bases" / state.kb_id
                        
                        # Load crawl checkpoint
                        crawl_cp = kb_root / "crawl_checkpoint.json"
                        if crawl_cp.exists():
                            crawl_data = json.loads(crawl_cp.read_text(encoding="utf-8"))
                            state.metrics["pages_total"] = crawl_data.get("pages_total", 0)
                            state.metrics["pages_crawled"] = crawl_data.get("pages_crawled", 0)
                            state.metrics["crawl_last_id"] = crawl_data.get("last_id", 0)
                        
                        # Count cleaned documents from filesystem
                        doc_dir = kb_root / "documents"
                        if doc_dir.exists():
                            doc_files = list(doc_dir.glob("*.txt")) + list(doc_dir.glob("*.md"))
                            state.metrics["documents_cleaned"] = len(doc_files)
                        
                        # Load index checkpoint
                        idx_cp = kb_root / "index_checkpoint.json"
                        if idx_cp.exists():
                            idx_data = json.loads(idx_cp.read_text(encoding="utf-8"))
                            state.metrics["chunked_last_id"] = idx_data.get("last_chunked_id", 0)
                            state.metrics["indexed_last_id"] = idx_data.get("last_indexed_id", 0)
                            state.metrics["chunks_created"] = idx_data.get("total_chunks", 0)
                            state.metrics["chunks_embedded"] = idx_data.get("total_chunks", 0)
                    except Exception as e:
                        logger.warning(f"Failed to enrich metrics for {state.kb_id}: {e}")
                    
                    self._states[state.kb_id] = state
                except Exception as e:
                    logger.warning(f"Failed to load state from {p}: {e}")
        except Exception as e:
            logger.warning(f"Failed scanning states: {e}")

    def backfill_from_job_manager(self):
        """Create filesystem snapshots from existing in-memory JobManager history."""
        try:
            from app.kb.ingestion.job_manager import get_job_manager
            jm = get_job_manager()
            jobs = jm.get_all_jobs()
            for job in jobs:
                try:
                    state = IngestionState(
                        kb_id=job.kb_id,
                        status=job.status.value if hasattr(job.status, 'value') else str(job.status),
                        phase=str(getattr(job, 'phase', 'crawling')),
                        progress=int(getattr(job, 'progress', 0)),
                        message=str(getattr(job, 'message', '')),
                        error=getattr(job, 'error', None),
                        metrics=getattr(job, 'metrics', {}) or {},
                    )
                    self._states[state.kb_id] = state
                    self._persist_state(state)
                    self._update_index(state.kb_id)
                except Exception as e:
                    logger.warning(f"Failed to backfill snapshot for job {getattr(job, 'job_id', '?')}: {e}")
            logger.info(f"Backfilled {len(jobs)} job snapshots to filesystem")
        except Exception as e:
            logger.warning(f"Backfill from JobManager failed: {e}")
