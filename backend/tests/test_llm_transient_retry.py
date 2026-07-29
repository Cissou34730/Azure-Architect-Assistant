"""Tests for the shared transient-fault retry helper used by LLM providers."""

from __future__ import annotations

import pytest
from openai import APIConnectionError, APITimeoutError, BadRequestError, RateLimitError

from app.shared.ai.transient_retry import (
    call_with_transient_retry,
    is_transient_llm_error,
)


def _make_rate_limit_error() -> RateLimitError:
    import httpx

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(429, request=request)
    return RateLimitError("rate limited", response=response, body=None)


def _make_bad_request_error() -> BadRequestError:
    import httpx

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(400, request=request)
    return BadRequestError("bad request", response=response, body=None)


class TestIsTransientLlmError:
    def test_rate_limit_is_transient(self) -> None:
        assert is_transient_llm_error(_make_rate_limit_error()) is True

    def test_timeout_is_transient(self) -> None:
        import httpx

        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        assert is_transient_llm_error(APITimeoutError(request)) is True

    def test_connection_error_is_transient(self) -> None:
        import httpx

        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        assert is_transient_llm_error(APIConnectionError(request=request)) is True

    def test_bad_request_is_not_transient(self) -> None:
        assert is_transient_llm_error(_make_bad_request_error()) is False

    def test_value_error_is_not_transient(self) -> None:
        assert is_transient_llm_error(ValueError("nope")) is False


class TestCallWithTransientRetry:
    @pytest.mark.asyncio
    async def test_succeeds_first_try(self) -> None:
        calls = 0

        async def fn() -> str:
            nonlocal calls
            calls += 1
            return "ok"

        result = await call_with_transient_retry(fn, max_attempts=3, base_delay=0.0)
        assert result == "ok"
        assert calls == 1

    @pytest.mark.asyncio
    async def test_retries_on_transient_then_succeeds(self) -> None:
        calls = 0

        async def fn() -> str:
            nonlocal calls
            calls += 1
            if calls < 3:
                raise _make_rate_limit_error()
            return "recovered"

        result = await call_with_transient_retry(fn, max_attempts=3, base_delay=0.0)
        assert result == "recovered"
        assert calls == 3

    @pytest.mark.asyncio
    async def test_does_not_retry_non_transient(self) -> None:
        calls = 0

        async def fn() -> str:
            nonlocal calls
            calls += 1
            raise _make_bad_request_error()

        with pytest.raises(BadRequestError):
            await call_with_transient_retry(fn, max_attempts=3, base_delay=0.0)
        assert calls == 1

    @pytest.mark.asyncio
    async def test_exhausts_attempts_and_raises(self) -> None:
        calls = 0

        async def fn() -> str:
            nonlocal calls
            calls += 1
            raise _make_rate_limit_error()

        with pytest.raises(RateLimitError):
            await call_with_transient_retry(fn, max_attempts=2, base_delay=0.0)
        assert calls == 2
