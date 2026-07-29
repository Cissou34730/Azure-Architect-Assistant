"""Tests for MicrosoftLearnMCPClient auto-reconnect behaviour."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.shared.mcp.exceptions import MCPUnexpectedResponseError
from app.shared.mcp.learn_mcp_client import MicrosoftLearnMCPClient


def _make_client(*, auto_reconnect: bool = True, max_retries: int = 1) -> MicrosoftLearnMCPClient:
    return MicrosoftLearnMCPClient(
        {
            "endpoint": "https://learn.microsoft.com/api/mcp",
            "timeout": 10,
            "auto_reconnect": auto_reconnect,
            "max_retries": max_retries,
        }
    )


def _prime_session(client: MicrosoftLearnMCPClient, *, fail_times: int) -> None:
    """Give the client a mocked session whose call_tool fails fail_times then succeeds."""
    client._initialized = True
    client._session = Mock()
    client._tools_cache = {
        "microsoft_docs_search": {"name": "microsoft_docs_search", "inputSchema": {}}
    }

    mock_result = Mock()
    block = Mock()
    block.type = "text"
    block.text = '{"ok": true}'
    mock_result.content = [block]

    state = {"calls": 0}

    async def _call_tool(name, arguments):  # noqa: ANN001
        state["calls"] += 1
        if state["calls"] <= fail_times:
            raise ConnectionError("session dropped")
        return mock_result

    client._session.call_tool = _call_tool
    client._state = state


class TestAutoReconnect:
    @pytest.mark.asyncio
    async def test_reconnects_once_on_connection_failure(self, monkeypatch: pytest.MonkeyPatch):
        client = _make_client(auto_reconnect=True, max_retries=1)
        _prime_session(client, fail_times=1)

        reconnect_calls = 0

        async def _fake_initialize() -> None:
            nonlocal reconnect_calls
            reconnect_calls += 1
            # After "reconnect", the session works again
            client._initialized = True

        monkeypatch.setattr(client, "_reinitialize", _fake_initialize)

        result = await client.call_tool("microsoft_docs_search", {"query": "x"})
        assert isinstance(result, dict)
        assert reconnect_calls == 1

    @pytest.mark.asyncio
    async def test_no_reconnect_when_disabled(self, monkeypatch: pytest.MonkeyPatch):
        client = _make_client(auto_reconnect=False, max_retries=1)
        _prime_session(client, fail_times=99)

        async def _fake_initialize() -> None:  # pragma: no cover
            raise AssertionError("should not reconnect")

        monkeypatch.setattr(client, "_reinitialize", _fake_initialize)

        with pytest.raises(MCPUnexpectedResponseError):
            await client.call_tool("microsoft_docs_search", {"query": "x"})

    @pytest.mark.asyncio
    async def test_reconnect_only_attempted_once_per_call(self, monkeypatch: pytest.MonkeyPatch):
        client = _make_client(auto_reconnect=True, max_retries=1)
        _prime_session(client, fail_times=99)  # keeps failing even after reconnect

        reconnect_calls = 0

        async def _fake_initialize() -> None:
            nonlocal reconnect_calls
            reconnect_calls += 1
            client._initialized = True

        monkeypatch.setattr(client, "_reinitialize", _fake_initialize)

        with pytest.raises(MCPUnexpectedResponseError):
            await client.call_tool("microsoft_docs_search", {"query": "x"})
        assert reconnect_calls == 1
