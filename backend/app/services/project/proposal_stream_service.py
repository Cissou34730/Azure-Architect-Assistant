"""Streaming helpers for architecture proposal SSE endpoints."""

from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from .document_service import DocumentService


def _format_sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _progress_payload(stage: str, detail: str | None = None) -> dict[str, Any]:
    return {
        "stage": stage,
        "detail": detail,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def stream_architecture_proposal(
    *,
    document_service: DocumentService,
    project_id: str,
    db: Any,
) -> Any:
    """Yield SSE payloads as proposal generation progresses."""
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    done_token = {"stage": "__done__"}

    def on_progress(stage: str, detail: str | None = None) -> None:
        queue.put_nowait(_progress_payload(stage, detail))

    async def _run_generation() -> None:
        try:
            proposal = await document_service.generate_proposal(project_id, db, on_progress)
            await queue.put(_progress_payload("completed", "Proposal generated successfully"))
            await queue.put(
                {
                    "stage": "done",
                    "proposal": proposal,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        except ValueError as exc:
            await queue.put(
                {
                    "stage": "error",
                    "error": str(exc),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception as exc:  # noqa: BLE001
            await queue.put(
                {
                    "stage": "error",
                    "error": f"Internal server error: {exc!s}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        finally:
            await queue.put(done_token)

    task = asyncio.create_task(_run_generation())
    try:
        yield _format_sse(_progress_payload("started", "Initializing proposal generation"))
        while True:
            event = await queue.get()
            if event is done_token:
                break
            yield _format_sse(event)
    finally:
        if not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

