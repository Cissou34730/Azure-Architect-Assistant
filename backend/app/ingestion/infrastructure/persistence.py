"""Local disk persistence store implementation."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import time
import shutil

from app.ingestion.domain.models import IngestionState
from app.ingestion.domain.errors import PersistenceError

logger = logging.getLogger(__name__)


class LocalDiskPersistenceStore:
    """File-based persistence store for ingestion state."""

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize persistence store.
        
        Args:
            base_path: Root directory for state files. Defaults to backend/data/knowledge_bases.
        """
        if base_path is None:
            # Default: backend/data/knowledge_bases
            backend_root = Path(__file__).resolve().parents[3]
            base_path = backend_root / "data" / "knowledge_bases"
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_state(self, state: IngestionState) -> None:
        """Persist ingestion state to disk."""
        state_path = self._get_state_path(state.kb_id)
        state_path.parent.mkdir(parents=True, exist_ok=True)

        existing: Dict[str, object] = {}
        if state_path.exists():
            try:
                with open(state_path, "r", encoding="utf-8") as handle:
                    existing = json.load(handle)
            except Exception:
                existing = {}

        existing.update({
            "kb_id": state.kb_id,
            "job_id": state.job_id,
            "version": 1,
            "updated_at": datetime.utcnow().isoformat(),
            "job": {
                "status": state.status,
                "phase": state.phase,
                "progress": state.progress,
                "message": state.message,
                "error": state.error,
                "created_at": state.created_at.isoformat() if state.created_at else None,
                "started_at": state.started_at.isoformat() if state.started_at else None,
                "completed_at": state.completed_at.isoformat() if state.completed_at else None,
                "paused": state.paused,
                "cancel_requested": state.cancel_requested,
            },
            "metrics": state.metrics,
            "phase_status": state.phase_status,
        })

        tmp_fd, tmp_name = tempfile.mkstemp(dir=str(state_path.parent), suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
                json.dump(existing, handle, indent=2)
        except Exception as exc:
            try:
                os.close(tmp_fd)
            except Exception:
                pass
            raise PersistenceError(state.kb_id, f"Failed to write temp file: {exc}")

        # Atomic replace with retries for Windows/OneDrive
        attempts = 0
        max_attempts = 3
        delay_sec = 0.3
        while attempts < max_attempts:
            try:
                os.replace(tmp_name, state_path)
                return
            except Exception:
                attempts += 1
                time.sleep(delay_sec)
        
        # Fallback to shutil.move
        try:
            shutil.move(tmp_name, str(state_path))
        except Exception as exc:
            raise PersistenceError(state.kb_id, f"Failed to persist state: {exc}")

    def save(self, state: IngestionState) -> None:
        """Alias for save_state() to match interface expectations."""
        return self.save_state(state)

    def load_state(self, kb_id: str) -> Optional[IngestionState]:
        """Load state for a specific knowledge base."""
        state_path = self._get_state_path(kb_id)
        if not state_path.exists():
            return None

        try:
            with open(state_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return self._parse_state(data, kb_id)
        except Exception as exc:
            logger.warning(f"Failed to load state for KB {kb_id}: {exc}")
            return None

    def load(self, kb_id: str) -> Optional[IngestionState]:
        """Alias for load_state() to match interface expectations."""
        return self.load_state(kb_id)

    def load_all_states(self) -> Dict[str, IngestionState]:
        """Load all persisted states from storage."""
        states: Dict[str, IngestionState] = {}
        if not self.base_path.exists():
            return states

        for kb_dir in self.base_path.iterdir():
            if not kb_dir.is_dir():
                continue
            state_file = kb_dir / "state.json"
            if not state_file.exists():
                continue
            
            kb_id = kb_dir.name
            try:
                with open(state_file, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                state = self._parse_state(data, kb_id)
                if state:
                    states[kb_id] = state
            except Exception as exc:
                logger.warning(f"Failed to load state for KB {kb_id}: {exc}")
        
        return states

    def delete_state(self, kb_id: str) -> None:
        """Remove persisted state for a knowledge base."""
        state_path = self._get_state_path(kb_id)
        try:
            if state_path.exists():
                state_path.unlink()
        except Exception as exc:
            logger.warning(f"Failed to delete state for KB {kb_id}: {exc}")

    def _get_state_path(self, kb_id: str) -> Path:
        """Get path to state file for a KB."""
        return self.base_path / kb_id / "state.json"

    def _parse_state(self, data: Dict, kb_id: str) -> Optional[IngestionState]:
        """Parse state dict to IngestionState object."""
        try:
            job = data.get("job", {})
            state = IngestionState(
                kb_id=kb_id,
                job_id=data.get("job_id", f"{kb_id}-legacy"),
                status=job.get("status", "pending"),
                phase=job.get("phase", "crawling"),
                progress=int(job.get("progress", 0)),
                message=job.get("message", ""),
                error=job.get("error"),
                metrics=data.get("metrics", {}),
                paused=job.get("paused", False),
                cancel_requested=job.get("cancel_requested", False),
                created_at=self._parse_dt(job.get("created_at")),
                started_at=self._parse_dt(job.get("started_at")),
                completed_at=self._parse_dt(job.get("completed_at")),
            )
            # Load phase_status if available
            if "phase_status" in data:
                state.phase_status = data["phase_status"]
            return state
        except Exception:
            return None

    @staticmethod
    def _parse_dt(value: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


# Factory function
def create_local_disk_persistence_store(base_path: Optional[Path] = None) -> LocalDiskPersistenceStore:
    """Factory to create local disk persistence store."""
    return LocalDiskPersistenceStore(base_path)
