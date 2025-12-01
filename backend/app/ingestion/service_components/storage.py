"""Filesystem-based persistence helpers for ingestion state."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .state import IngestionState

logger = logging.getLogger(__name__)


def persist_state(state: IngestionState) -> None:
    """Persist state to unified state.json under the KB directory."""

    backend_root = Path(__file__).resolve().parent.parent
    state_path = backend_root / "data" / "knowledge_bases" / state.kb_id / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)

    existing: Dict[str, object] = {}
    if state_path.exists():
        try:
            with open(state_path, "r", encoding="utf-8") as handle:
                existing = json.load(handle)
        except Exception:
            existing = {}

    existing.update(
        {
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
        }
    )

    tmp_fd, tmp_name = tempfile.mkstemp(dir=str(state_path.parent), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
            json.dump(existing, handle, indent=2)
        os.replace(tmp_name, state_path)
    except Exception as exc:
        logger.warning("Failed to persist state for KB %s: %s", state.kb_id, exc)


def load_states_from_disk() -> Dict[str, IngestionState]:
    """Load any previously persisted states from disk."""

    backend_root = Path(__file__).resolve().parent.parent
    kb_root = backend_root / "data" / "knowledge_bases"
    if not kb_root.exists():
        return {}

    states: Dict[str, IngestionState] = {}
    for kb_dir in kb_root.iterdir():
        if not kb_dir.is_dir():
            continue
        state_file = kb_dir / "state.json"
        if not state_file.exists():
            continue
        try:
            with open(state_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            job = data.get("job", {})
            kb_id = data.get("kb_id", kb_dir.name)
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
                created_at=_parse_dt(job.get("created_at")),
                started_at=_parse_dt(job.get("started_at")),
                completed_at=_parse_dt(job.get("completed_at")),
            )
            states[kb_id] = state
        except Exception as exc:
            logger.warning("Failed to load legacy state for %s: %s", state_file, exc)
    return states


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
