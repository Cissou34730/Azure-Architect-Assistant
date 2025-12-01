import asyncio
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime
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
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class IngestionService:
    _instance: Optional["IngestionService"] = None

    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._states: Dict[str, IngestionState] = {}
        self._lock = asyncio.Lock()

    @classmethod
    def instance(cls) -> "IngestionService":
        if not cls._instance:
            cls._instance = IngestionService()
        return cls._instance

    def _get_state(self, kb_id: str) -> Optional[IngestionState]:
        return self._states.get(kb_id)

    async def start(
        self,
        kb_id: str,
        run_callable,
        *args,
        state_override: Optional[IngestionState] = None,
        **kwargs,
    ) -> IngestionState:
        async with self._lock:
            existing_task = self._tasks.get(kb_id)
            if existing_task and not existing_task.done():
                return self._states[kb_id]

        # Reuse existing state when resuming, otherwise create a fresh one.
        state = state_override or IngestionState(
            kb_id=kb_id,
            status="running",
            phase="crawling",
            progress=0,
        )
        
        # Set timestamps
        if not state.created_at:
            state.created_at = datetime.now()
        state.started_at = datetime.now()
        
        state.status = "running"
        state.paused = False
        state.cancel_requested = False
        if not state.message:
            state.message = "Ingestion started"
        
        self._states[kb_id] = state
        # Persist initial state
        self._persist_state(state)

        kwargs_with_state = dict(kwargs)
        kwargs_with_state.setdefault("state", state)

        async def worker():
            try:
                # Run async pipeline with cooperative checks
                await run_callable(*args, **kwargs_with_state)
                if not state.cancel_requested:
                    state.status = "completed"
                    state.phase = "completed"
                    state.message = "Ingestion completed"
                    state.progress = 100
                    state.completed_at = datetime.now()
                state.error = None
                self._persist_state(state)
            except asyncio.CancelledError:
                state.status = "cancelled"
                state.message = "Ingestion cancelled"
                state.completed_at = datetime.now()
                self._persist_state(state)
                raise
            except Exception as e:
                logger.error(f"Ingestion failed for {kb_id}: {e}", exc_info=True)
                state.status = "failed"
                state.phase = "failed"
                state.error = str(e)
                state.message = "Ingestion failed"
                state.completed_at = datetime.now()
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
        
        # Set cooperative pause flag
        state.paused = True
        state.status = "paused"
        state.message = "Paused by user"
        self._persist_state(state)
        logger.info(f"Pause requested for {kb_id}")
        return True

    async def resume(self, kb_id: str) -> bool:
        state = self._get_state(kb_id)
        if not state:
            return False
        
        # Only allow resuming if job is currently paused
        if state.status != "paused":
            return False
        
        # Clear cooperative pause flag
        state.paused = False
        state.status = "running"
        state.message = "Resumed by user"
        self._persist_state(state)
        logger.info(f"Resume requested for {kb_id}")
        return True

    async def cancel(self, kb_id: str) -> bool:
        state = self._get_state(kb_id)
        if not state:
            return False
        
        # Only allow cancellation if job is running, pending, or paused
        if state.status not in ("running", "pending", "paused"):
            return False
        
        # Set cooperative cancel flag
        state.cancel_requested = True
        
        # Cancel the asyncio task as hard stop fallback
        task = self._tasks.get(kb_id)
        if task and not task.done():
            try:
                task.cancel()
            except Exception:
                pass
        
        state.status = "cancelled"
        state.phase = "cancelled"
        state.message = "Cancellation requested"
        self._persist_state(state)
        logger.info(f"Cancel requested for {kb_id}")
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
    def _persist_state(self, state: IngestionState):
        """Persist state to unified state.json in KB directory."""
        import json, tempfile, os
        from pathlib import Path
        
        # State file location: backend/data/knowledge_bases/{kb_id}/state.json
        backend_root = Path(__file__).parent.parent
        state_path = backend_root / "data" / "knowledge_bases" / state.kb_id / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing state (preserve crawl/processing sections)
        data = {}
        if state_path.exists():
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                data = {}
        
        # Update job section
        data['kb_id'] = state.kb_id
        data['version'] = 1
        data['updated_at'] = datetime.now().isoformat()
        data['job'] = {
            'status': state.status,
            'phase': state.phase,
            'progress': state.progress,
            'message': state.message,
            'error': state.error,
            'created_at': state.created_at.isoformat() if state.created_at else None,
            'started_at': state.started_at.isoformat() if state.started_at else None,
            'completed_at': state.completed_at.isoformat() if state.completed_at else None,
            'paused': state.paused,
            'cancel_requested': state.cancel_requested
        }
        
        # Copy metrics to state if present
        if state.metrics:
            if 'metrics' not in data:
                data['metrics'] = {}
            data['metrics'].update(state.metrics)
        
        # Atomic write
        try:
            tmp_fd, tmp_name = tempfile.mkstemp(dir=str(state_path.parent), suffix='.tmp')
            with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_name, str(state_path))
        except Exception as e:
            logger.warning(f"Failed to persist state {state.kb_id}: {e}")

    async def resume_or_start(self, kb_id: str, run_callable, *args, **kwargs) -> bool:
        """If a task exists and is paused, resume it; otherwise, start a new task.
        Returns True on success, False if unable to resume/start.
        """
        restart_with_state: Optional[IngestionState] = None

        async with self._lock:
            state = self._get_state(kb_id)
            task = self._tasks.get(kb_id)

            # If a task is already running, nothing else to do.
            if task and not task.done():
                if state and state.status == "paused":
                    state.paused = False
                    state.status = "running"
                    state.message = "Resumed by user"
                    self._persist_state(state)
                return True

            # Task missing or finished. If we have a paused state, restart from checkpoint.
            if state and state.status == "paused":
                state.paused = False
                state.cancel_requested = False
                state.status = "running"
                state.message = "Resumed by user"
                self._persist_state(state)
                restart_with_state = state
            else:
                restart_with_state = None

        started_state = await self.start(
            kb_id,
            run_callable,
            *args,
            state_override=restart_with_state,
            **kwargs,
        )
        return started_state is not None

    def load_all_states(self):
        """Load all persisted states from unified state.json files."""
        import json
        from pathlib import Path
        
        try:
            kb_root = Path(__file__).parent.parent / "data" / "knowledge_bases"
            if not kb_root.exists():
                return
            
            for kb_dir in kb_root.iterdir():
                if not kb_dir.is_dir():
                    continue
                
                state_file = kb_dir / "state.json"
                if not state_file.exists():
                    continue
                
                try:
                    with open(state_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    job = data.get('job', {})
                    crawl = data.get('crawl', {})
                    processing = data.get('processing', {})
                    metrics = data.get('metrics', {})
                    
                    # Build metrics from all sections
                    combined_metrics = {
                        'pages_crawled': crawl.get('pages_crawled', 0),
                        'pages_queued': crawl.get('pages_queued', 0),
                        'pages_failed': crawl.get('pages_failed', 0),
                        'last_doc_id': crawl.get('last_doc_id', 0),
                        'last_indexed_id': processing.get('last_indexed_id', 0),
                        'chunks_total': processing.get('chunks_total', 0),
                        'batches_processed': processing.get('batches_processed', 0)
                    }
                    combined_metrics.update(metrics)
                    
                    state = IngestionState(
                        kb_id=data.get('kb_id', kb_dir.name),
                        status=job.get('status', 'pending'),
                        phase=job.get('phase', 'crawling'),
                        progress=int(job.get('progress', 0)),
                        message=job.get('message', ''),
                        error=job.get('error'),
                        metrics=combined_metrics,
                        created_at=datetime.fromisoformat(job['created_at']) if job.get('created_at') else None,
                        started_at=datetime.fromisoformat(job['started_at']) if job.get('started_at') else None,
                        completed_at=datetime.fromisoformat(job['completed_at']) if job.get('completed_at') else None,
                    )
                    
                    # Mark flags false on load (intentional)
                    state.paused = False
                    state.cancel_requested = False
                    
                    self._states[state.kb_id] = state
                    logger.info(f"Loaded state for KB {state.kb_id}: {state.status} ({state.phase})")
                    
                except Exception as e:
                    logger.warning(f"Failed to load state from {state_file}: {e}")
        except Exception as e:
            logger.warning(f"Failed scanning states: {e}")


