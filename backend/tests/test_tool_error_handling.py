"""TDD tests for Slice 4: Tool error handling improvements.

Tool wrappers must surface errors to the agent instead of silently swallowing them.
Only signature-shape TypeErrors should trigger a fallback retry.
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Run an async coroutine in a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# 1. Signature-shape TypeError still retries via fallback
# ---------------------------------------------------------------------------

class TestSignatureTypeErrorRetry:
    """When _call_function raises TypeError (signature mismatch), fallback is used."""

    def test_fallback_on_type_error_returns_result(self) -> None:
        from app.agents_system.tools.tool_wrappers import make_single_input_wrapper

        call_count = 0

        async def my_tool(payload):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TypeError("missing 1 required positional argument")
            return "success"

        _sync, _async = make_single_input_wrapper("test_tool", my_tool, my_tool)
        result = _run(_async({"key": "value"}))
        assert result == "success"

    def test_fallback_on_type_error_calls_function_again(self) -> None:
        from app.agents_system.tools.tool_wrappers import make_single_input_wrapper

        calls = []

        async def my_tool(payload):
            calls.append(payload)
            if len(calls) == 1:
                raise TypeError("unexpected keyword argument")
            return "ok"

        _sync, _async = make_single_input_wrapper("test_tool", my_tool, my_tool)
        _run(_async("test"))
        assert len(calls) == 2


# ---------------------------------------------------------------------------
# 2. Non-TypeError exceptions surface as error string, no retry
# ---------------------------------------------------------------------------

class TestNonTypeErrorSurfaced:
    """Non-TypeError exceptions must NOT retry and must return error string."""

    def test_value_error_returns_error_string(self) -> None:
        from app.agents_system.tools.tool_wrappers import make_single_input_wrapper

        async def my_tool(payload):
            raise ValueError("invalid data format")

        _sync, _async = make_single_input_wrapper("test_tool", my_tool, my_tool)
        result = _run(_async({"key": "value"}))
        assert isinstance(result, str)
        assert "ERROR" in result
        assert "test_tool" in result
        assert "invalid data format" in result

    def test_runtime_error_returns_error_string(self) -> None:
        from app.agents_system.tools.tool_wrappers import make_single_input_wrapper

        async def my_tool(payload):
            raise RuntimeError("connection refused")

        _sync, _async = make_single_input_wrapper("test_tool", my_tool, my_tool)
        result = _run(_async({"key": "value"}))
        assert "ERROR" in result
        assert "connection refused" in result

    def test_non_type_error_does_not_retry(self) -> None:
        from app.agents_system.tools.tool_wrappers import make_single_input_wrapper

        call_count = 0

        async def my_tool(payload):
            nonlocal call_count
            call_count += 1
            raise ValueError("bad input")

        _sync, _async = make_single_input_wrapper("test_tool", my_tool, my_tool)
        _run(_async("test"))
        # Should only be called once (in _call_function), NOT retried in fallback
        assert call_count == 1

    def test_key_error_surfaces_not_retried(self) -> None:
        from app.agents_system.tools.tool_wrappers import make_single_input_wrapper

        call_count = 0

        async def my_tool(payload):
            nonlocal call_count
            call_count += 1
            raise KeyError("missing_field")

        _sync, _async = make_single_input_wrapper("test_tool", my_tool, my_tool)
        result = _run(_async({"x": 1}))
        assert call_count == 1
        assert "ERROR" in result


# ---------------------------------------------------------------------------
# 3. Error string format is structured for agent consumption
# ---------------------------------------------------------------------------

class TestErrorFormat:
    """Error messages must include tool name and error details."""

    def test_error_includes_tool_name(self) -> None:
        from app.agents_system.tools.tool_wrappers import make_single_input_wrapper

        async def my_tool(payload):
            raise Exception("something broke")

        _sync, _async = make_single_input_wrapper("aaa_manage_artifacts", my_tool, my_tool)
        result = _run(_async("test"))
        assert "aaa_manage_artifacts" in result

    def test_error_includes_exception_type(self) -> None:
        from app.agents_system.tools.tool_wrappers import make_single_input_wrapper

        async def my_tool(payload):
            raise ConnectionError("timeout")

        _sync, _async = make_single_input_wrapper("my_tool", my_tool, my_tool)
        result = _run(_async("test"))
        assert "ConnectionError" in result

    def test_error_includes_exception_message(self) -> None:
        from app.agents_system.tools.tool_wrappers import make_single_input_wrapper

        async def my_tool(payload):
            raise ValueError("field 'name' is required")

        _sync, _async = make_single_input_wrapper("my_tool", my_tool, my_tool)
        result = _run(_async("test"))
        assert "field 'name' is required" in result


# ---------------------------------------------------------------------------
# 4. _call_function internal TypeError handling (signature shape)
# ---------------------------------------------------------------------------

class TestCallFunctionSignatureRetry:
    """_call_function should retry with **kwargs on TypeError from positional call."""

    def test_dict_payload_retries_as_kwargs(self) -> None:
        from app.agents_system.tools.tool_wrappers import _call_function

        async def my_tool(*, key: str):
            return f"got {key}"

        result = _run(_call_function(my_tool, {"key": "hello"}))
        assert result == "got hello"

    def test_non_dict_payload_does_not_use_kwargs(self) -> None:
        from app.agents_system.tools.tool_wrappers import _call_function

        async def my_tool(value):
            return f"got {value}"

        result = _run(_call_function(my_tool, "hello"))
        assert result == "got hello"


# ---------------------------------------------------------------------------
# 5. Fallback TypeError also surfaces if it fails
# ---------------------------------------------------------------------------

class TestFallbackTypeErrorAlsoSurfaces:
    """If fallback itself raises TypeError (both signatures fail), surface error."""

    def test_double_type_error_surfaces(self) -> None:
        from app.agents_system.tools.tool_wrappers import make_single_input_wrapper

        async def my_tool():  # takes no args at all
            return "unreachable"

        _sync, _async = make_single_input_wrapper("bad_sig_tool", my_tool, my_tool)
        result = _run(_async({"key": "value"}))
        assert isinstance(result, str)
        assert "ERROR" in result
        assert "bad_sig_tool" in result
