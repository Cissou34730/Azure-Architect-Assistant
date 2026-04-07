from __future__ import annotations

import asyncio
import threading


class ShutdownManager:
    """Manages graceful shutdown events for ingestion jobs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._shutdown_events: dict[str, asyncio.Event] = {}

    def register_job(self, job_id: str) -> asyncio.Event:
        """Register a job and return its shutdown event."""
        event = asyncio.Event()
        with self._lock:
            self._shutdown_events[job_id] = event
        return event

    def request_shutdown(self, job_id: str | None = None) -> None:
        """Request shutdown for a specific job or all registered jobs."""
        with self._lock:
            if job_id is None:
                events = list(self._shutdown_events.values())
            else:
                event = self._shutdown_events.get(job_id)
                events = [event] if event is not None else []

        for event in events:
            event.set()

    def unregister_job(self, job_id: str) -> None:
        """Remove a job from tracking after completion."""
        with self._lock:
            self._shutdown_events.pop(job_id, None)
