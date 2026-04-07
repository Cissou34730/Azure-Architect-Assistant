"""Shared GitHub Copilot SDK runtime helpers."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType
from copilot.types import GetAuthStatusResponse, ModelInfo, PermissionRequestResult

from ..config import AIConfig

logger = logging.getLogger(__name__)


def _default_deny_permission(*_args: Any, **_kwargs: Any) -> PermissionRequestResult:
    return {"kind": "denied-by-rules", "rules": []}


def _extract_response_text(event: Any) -> str:
    if event is None:
        return ""
    data = getattr(event, "data", None)
    if data is None:
        return ""
    if getattr(data, "content", None):
        return str(data.content)
    if getattr(data, "delta_content", None):
        return str(data.delta_content)
    result = getattr(data, "result", None)
    if result is not None and getattr(result, "content", None):
        return str(result.content)
    return ""


@dataclass
class CopilotStatus:
    available: bool
    authenticated: bool
    state: str
    login: str | None
    auth_type: str | None
    host: str | None
    status_message: str | None
    cli_path: str | None


@dataclass
class _StreamState:
    queue: asyncio.Queue[str]
    idle_event: asyncio.Event
    saw_delta: bool = False
    error: Exception | None = None


@dataclass
class _RuntimeHolder:
    runtime: CopilotRuntime | None = None


class CopilotRuntime:
    """Manages a shared Python Copilot SDK client."""

    def __init__(self, config: AIConfig) -> None:
        self.config = config
        self._client: CopilotClient | None = None
        self._lock = asyncio.Lock()

    def _client_options(self) -> dict[str, Any]:
        return {
            "cwd": str(Path.cwd()),
            "log_level": "warning",
            "use_stdio": True,
            "use_logged_in_user": True,
            "auto_start": True,
        }

    async def _ensure_client(self) -> CopilotClient:
        if self._client is not None:
            return self._client

        async with self._lock:
            if self._client is None:
                client = CopilotClient(self._client_options())
                await asyncio.wait_for(client.start(), timeout=self.config.copilot_startup_timeout)
                self._client = client
            return self._client

    async def stop(self) -> None:
        if self._client is None:
            return
        async with self._lock:
            if self._client is not None:
                await self._client.stop()
                self._client = None

    async def get_auth_status(self) -> GetAuthStatusResponse:
        client = await self._ensure_client()
        return await client.get_auth_status()

    async def get_status(self) -> CopilotStatus:
        try:
            auth = await self.get_auth_status()
            cli_path = None
            if self._client is not None:
                cli_path = self._client.options.get("cli_path")
            state = "ready" if auth.isAuthenticated else "unauthenticated"
            return CopilotStatus(
                available=True,
                authenticated=auth.isAuthenticated,
                state=state,
                login=auth.login,
                auth_type=auth.authType,
                host=auth.host,
                status_message=auth.statusMessage,
                cli_path=cli_path,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Copilot status check failed: %s", exc)
            return CopilotStatus(
                available=False,
                authenticated=False,
                state="error",
                login=None,
                auth_type=None,
                host=None,
                status_message=str(exc),
                cli_path=None,
            )

    async def launch_login(self) -> dict[str, Any]:
        client = await self._ensure_client()
        cli_path = client.options.get("cli_path")
        if not cli_path:
            raise RuntimeError("Copilot CLI path is not available")

        resolved_cli_path = str(Path(str(cli_path)).resolve())
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        subprocess.Popen(  # noqa: S603 - launches trusted Copilot CLI path from SDK config.
            [resolved_cli_path, "login"],
            cwd=client.options.get("cwd") or str(Path.cwd()),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        return {
            "launched": True,
            "message": "Copilot login launched. Complete the official CLI login flow, then poll status.",
        }

    async def logout(self) -> dict[str, Any]:
        await self.stop()
        return {
            "success": True,
            "manual_logout_required": True,
            "message": "Copilot SDK session was disconnected. Run `copilot login` again if you want to reconnect, and use the Copilot CLI to fully remove stored auth if needed.",
        }

    async def list_models(self) -> list[ModelInfo]:
        auth = await self.get_auth_status()
        if not auth.isAuthenticated:
            raise RuntimeError(auth.statusMessage or "Copilot is not authenticated")
        client = await self._ensure_client()
        return await client.list_models()

    async def get_quota(self) -> dict[str, Any] | None:
        auth = await self.get_auth_status()
        if not auth.isAuthenticated:
            return None
        client = await self._ensure_client()
        result = await client.rpc.account.get_quota()
        return result.to_dict()

    async def send_message(
        self,
        *,
        prompt: str,
        model: str,
        system_message: str | None = None,
        timeout: float,
    ) -> str:
        auth = await self.get_auth_status()
        if not auth.isAuthenticated:
            raise RuntimeError(auth.statusMessage or "Copilot is not authenticated")

        client = await self._ensure_client()
        session = await client.create_session(
            {
                "model": model,
                "system_message": {"mode": "append", "content": system_message or ""},
                "on_permission_request": _default_deny_permission,
                "streaming": False,
            }
        )
        try:
            event = await session.send_and_wait({"prompt": prompt}, timeout=timeout)
            content = _extract_response_text(event)
            if content:
                return content

            # Fallback to full message history when the final event is not the assistant payload.
            events = await session.get_messages()
            for item in reversed(events):
                if item.type == SessionEventType.ASSISTANT_MESSAGE:
                    content = _extract_response_text(item)
                    if content:
                        return content
            return ""
        finally:
            await session.destroy()

    async def stream_message(
        self,
        *,
        prompt: str,
        model: str,
        system_message: str | None = None,
        timeout: float,
    ) -> AsyncIterator[str]:
        auth = await self.get_auth_status()
        if not auth.isAuthenticated:
            raise RuntimeError(auth.statusMessage or "Copilot is not authenticated")

        client = await self._ensure_client()
        session = await client.create_session(
            {
                "model": model,
                "system_message": {"mode": "append", "content": system_message or ""},
                "on_permission_request": _default_deny_permission,
                "streaming": True,
            }
        )
        stream_state = _StreamState(queue=asyncio.Queue(), idle_event=asyncio.Event())
        unsubscribe = session.on(lambda event: self._handle_stream_event(event, stream_state))
        try:
            await session.send({"prompt": prompt})
            async for chunk in self._consume_stream_chunks(
                stream_state=stream_state,
                timeout=timeout,
            ):
                yield chunk
        finally:
            unsubscribe()
            await session.destroy()

    def _handle_stream_event(self, event: Any, stream_state: _StreamState) -> None:
        event_type = event.type
        if event_type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            chunk = _extract_response_text(event)
            if chunk:
                stream_state.saw_delta = True
                stream_state.queue.put_nowait(chunk)
            return

        if event_type == SessionEventType.ASSISTANT_MESSAGE and not stream_state.saw_delta:
            content = _extract_response_text(event)
            if content:
                stream_state.queue.put_nowait(content)
            return

        if event_type == SessionEventType.SESSION_ERROR:
            stream_state.error = RuntimeError(
                getattr(getattr(event, "data", None), "message", "Copilot session error")
            )
            stream_state.idle_event.set()
            return

        if event_type == SessionEventType.SESSION_IDLE:
            stream_state.idle_event.set()

    async def _consume_stream_chunks(
        self,
        *,
        stream_state: _StreamState,
        timeout: float,
    ) -> AsyncIterator[str]:
        while True:
            if stream_state.idle_event.is_set() and stream_state.queue.empty():
                break
            try:
                chunk = await asyncio.wait_for(stream_state.queue.get(), timeout=timeout)
            except asyncio.TimeoutError as exc:
                raise asyncio.TimeoutError(
                    f"Timeout after {timeout}s waiting for streamed Copilot output"
                ) from exc
            yield chunk

        if stream_state.error is not None:
            raise stream_state.error


_runtime_holder = _RuntimeHolder()
_runtime_lock = asyncio.Lock()


async def get_copilot_runtime(config: AIConfig) -> CopilotRuntime:
    if _runtime_holder.runtime is not None:
        return _runtime_holder.runtime

    async with _runtime_lock:
        if _runtime_holder.runtime is None:
            _runtime_holder.runtime = CopilotRuntime(config)
        return _runtime_holder.runtime


async def reset_copilot_runtime() -> None:
    if _runtime_holder.runtime is None:
        return
    async with _runtime_lock:
        if _runtime_holder.runtime is not None:
            await _runtime_holder.runtime.stop()
            _runtime_holder.runtime = None
