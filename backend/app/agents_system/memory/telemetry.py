"""Telemetry service for writing ProjectTraceEvent records.

Provides a simple async interface for emitting structured trace events
that are persisted to the project_trace_events table.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectTraceEvent

logger = logging.getLogger(__name__)


async def emit_trace_event(
    db: AsyncSession,
    *,
    project_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    thread_id: str | None = None,
) -> str:
    """Write a single trace event row.

    Returns the event id.
    """
    event_id = str(uuid.uuid4())
    event = ProjectTraceEvent(
        id=event_id,
        project_id=project_id,
        thread_id=thread_id,
        event_type=event_type,
        payload=json.dumps(payload or {}),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(event)
    await db.flush()
    logger.debug("Trace event %s (%s) for project %s", event_id, event_type, project_id)
    return event_id
