from __future__ import annotations

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from app.agents_system.langgraph import adapter as adapter_module
from app.agents_system.langgraph import graph_factory


class _ProjectChatGraphStub:
    def __init__(self) -> None:
        self.calls: list[tuple[dict[str, object], dict[str, object] | None]] = []

    async def ainvoke(
        self,
        state: dict[str, object],
        config: dict[str, object] | None = None,
    ) -> dict[str, object]:
        self.calls.append((state, config))
        return {
            'final_answer': 'Thread-aware answer',
            'success': True,
            'updated_project_state': {'projectId': 'proj-1'},
            'intermediate_steps': [],
            'error': None,
        }


@asynccontextmanager
async def _graph_context(graph: _ProjectChatGraphStub):
    yield graph


def _parse_sse_event(event: str) -> tuple[str, dict[str, object]]:
    lines = event.strip().splitlines()
    event_name = lines[0].split(':', maxsplit=1)[1].strip()
    payload = json.loads(lines[1].split(':', maxsplit=1)[1].strip())
    return event_name, payload


def test_thread_checkpointer_database_path_uses_data_root(tmp_path) -> None:
    settings = SimpleNamespace(data_root=tmp_path)

    assert graph_factory._thread_checkpointer_database_path(settings) == tmp_path / 'checkpoints.db'


@pytest.mark.asyncio
async def test_build_thread_checkpointer_opens_async_sqlite_saver(tmp_path) -> None:
    settings = SimpleNamespace(data_root=tmp_path)

    async with graph_factory._build_thread_checkpointer(settings) as checkpointer:
        assert type(checkpointer).__module__ == 'langgraph.checkpoint.sqlite.aio'
        assert graph_factory._thread_checkpointer_database_path(settings).exists()


@pytest.mark.asyncio
async def test_build_project_chat_graph_uses_sqlite_checkpointer_when_enabled(
    monkeypatch, tmp_path
) -> None:
    settings = SimpleNamespace(
        aaa_thread_memory_enabled=True,
        data_root=tmp_path,
    )
    sentinel_checkpointer = object()

    @asynccontextmanager
    async def _stub_checkpointer(*_args, **_kwargs):
        yield sentinel_checkpointer

    monkeypatch.setattr(graph_factory, 'get_app_settings', lambda: settings)
    monkeypatch.setattr(graph_factory, '_build_thread_checkpointer', _stub_checkpointer)

    async with graph_factory.build_project_chat_graph(db=object()) as graph:
        assert graph.checkpointer is sentinel_checkpointer


@pytest.mark.asyncio
async def test_build_project_chat_graph_disables_checkpointer_when_thread_memory_disabled(
    monkeypatch, tmp_path
) -> None:
    settings = SimpleNamespace(
        aaa_thread_memory_enabled=False,
        data_root=tmp_path,
    )

    monkeypatch.setattr(graph_factory, 'get_app_settings', lambda: settings)

    async with graph_factory.build_project_chat_graph(db=object()) as graph:
        assert graph.checkpointer is None


@pytest.mark.asyncio
async def test_execute_project_chat_generates_thread_id_when_missing(monkeypatch) -> None:
    graph = _ProjectChatGraphStub()
    monkeypatch.setattr(
        adapter_module, 'build_project_chat_graph', lambda *_args: _graph_context(graph)
    )

    payload = await adapter_module.execute_project_chat(
        'proj-1',
        'Help me design this system',
        db=object(),  # type: ignore[arg-type]
        thread_id=None,
    )

    assert payload['success'] is True
    assert isinstance(payload['thread_id'], str)
    assert payload['thread_id'] != ''
    assert graph.calls == [
        (
            {
                'project_id': 'proj-1',
                'user_message': 'Help me design this system',
                'thread_id': payload['thread_id'],
                'success': False,
                'retry_count': 0,
            },
            {'configurable': {'thread_id': payload['thread_id']}},
        )
    ]


@pytest.mark.asyncio
async def test_execute_project_chat_stream_generates_thread_id_when_missing(monkeypatch) -> None:
    graph = _ProjectChatGraphStub()
    monkeypatch.setattr(
        adapter_module, 'build_project_chat_graph', lambda *_args: _graph_context(graph)
    )

    events = [
        chunk
        async for chunk in adapter_module.execute_project_chat_stream(
            'proj-1',
            'Stream a response',
            db=object(),  # type: ignore[arg-type]
            thread_id=None,
        )
    ]

    final_event_name, final_payload = _parse_sse_event(events[-1])

    assert final_event_name == 'final'
    assert final_payload['success'] is True
    assert isinstance(final_payload['thread_id'], str)
    assert final_payload['thread_id'] != ''
    assert graph.calls == [
        (
            {
                'project_id': 'proj-1',
                'user_message': 'Stream a response',
                'thread_id': final_payload['thread_id'],
                'success': False,
                'retry_count': 0,
            },
            {
                'configurable': {
                    'thread_id': final_payload['thread_id'],
                    'event_callback': graph.calls[0][1]['configurable']['event_callback'],
                }
            },
        )
    ]
