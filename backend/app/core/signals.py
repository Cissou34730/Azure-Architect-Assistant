import asyncio
import logging
import signal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.ingestion_runtime import IngestionRuntimeService

logger = logging.getLogger(__name__)


def _cancel_running_tasks(runtime_service: "IngestionRuntimeService") -> None:
    """Cancel all tasks currently managed by the ingestion runtime.

    Resolves the running event loop at call time (inside the signal handler)
    so we always target uvicorn's loop, not a stale one captured at startup.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return  # No running loop — nothing to cancel

    running_tasks = getattr(runtime_service, "_running_tasks", {})
    for job_id, task in list(running_tasks.items()):
        if hasattr(runtime_service, "repo"):
            runtime_service.repo.set_job_status(job_id, status="paused")
        if not task.done():
            loop.call_soon_threadsafe(task.cancel)


def _chain_signal_handler(sig, frame, prev_handlers, current_handler) -> None:
    """Chain to the previous signal handler."""
    prev = prev_handlers.get(sig)
    if prev in (None, signal.SIG_IGN):
        return
    if prev == signal.SIG_DFL:
        if sig == signal.SIGINT:
            raise KeyboardInterrupt()
        return
    if prev == current_handler:
        return

    try:
        if callable(prev):
            prev(sig, frame)
    except KeyboardInterrupt:
        raise
    except Exception:  # noqa: BLE001
        logger.debug("Previous signal handler raised; continuing shutdown", exc_info=True)


def _handle_ingestion_shutdown(
    sig: int,
    frame: Any,
    runtime_service: "IngestionRuntimeService",
    prev_handlers: dict[int, Any],
) -> None:
    """Internal signal handler logic."""
    logger.warning(f"Signal {sig} received - requesting ingestion shutdown")
    runtime_service.shutdown_manager.request_shutdown()

    # Mark jobs paused and cancel running tasks promptly
    try:
        _cancel_running_tasks(runtime_service)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Failed to cancel running ingestion tasks on signal: {exc}")

    # Chain to the previous handler so uvicorn still stops
    _chain_signal_handler(sig, frame, prev_handlers, _handle_ingestion_shutdown)


def install_ingestion_signal_handlers():
    """
    Ensure SIGINT/SIGTERM immediately request ingestion shutdown so CTRL-C
    pauses jobs instead of continuing to run embeds/indexing.
    """
    from app.dependencies import get_ingestion_runtime_service_dependency  # noqa: PLC0415

    prev_handlers = {}
    runtime_service = get_ingestion_runtime_service_dependency()

    def _handler(sig, frame):
        _handle_ingestion_shutdown(sig, frame, runtime_service, prev_handlers)

    signals_to_install = [signal.SIGINT]
    if hasattr(signal, "SIGTERM"):
        signals_to_install.append(signal.SIGTERM)

    for sig in signals_to_install:
        try:
            prev_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, _handler)
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"Could not register signal handler for {sig}: {exc}")


