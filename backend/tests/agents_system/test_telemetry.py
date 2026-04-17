"""Tests for telemetry service."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents_system.memory.telemetry import emit_trace_event


@pytest.fixture()
def mock_db() -> AsyncMock:
    """Async DB session mock that tracks added objects."""
    db = AsyncMock()
    db.added: list = []

    def _add(obj: object) -> None:
        db.added.append(obj)

    db.add = MagicMock(side_effect=_add)
    return db


class TestEmitTraceEvent:
    """Tests for the emit_trace_event function."""

    @pytest.mark.asyncio()
    async def test_creates_event_with_all_fields(self, mock_db: AsyncMock) -> None:
        event_id = await emit_trace_event(
            mock_db,
            project_id="proj-1",
            event_type="test_event",
            payload={"key": "value"},
            thread_id="thread-1",
        )
        assert isinstance(event_id, str)
        assert len(event_id) == 36  # UUID

        assert len(mock_db.added) == 1
        event = mock_db.added[0]
        assert event.project_id == "proj-1"
        assert event.thread_id == "thread-1"
        assert event.event_type == "test_event"
        assert json.loads(event.payload) == {"key": "value"}
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_defaults_to_empty_payload(self, mock_db: AsyncMock) -> None:
        await emit_trace_event(
            mock_db,
            project_id="proj-1",
            event_type="minimal",
        )
        event = mock_db.added[0]
        assert json.loads(event.payload) == {}
        assert event.thread_id is None

    @pytest.mark.asyncio()
    async def test_returns_unique_ids(self, mock_db: AsyncMock) -> None:
        id1 = await emit_trace_event(mock_db, project_id="p", event_type="a")
        id2 = await emit_trace_event(mock_db, project_id="p", event_type="b")
        assert id1 != id2

    @pytest.mark.asyncio()
    async def test_event_has_created_at(self, mock_db: AsyncMock) -> None:
        await emit_trace_event(mock_db, project_id="p", event_type="ts")
        event = mock_db.added[0]
        assert event.created_at is not None
        assert "T" in event.created_at  # ISO format
