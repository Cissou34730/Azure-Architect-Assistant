import asyncio
import contextlib
import logging
import signal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.routers import ingestion

logger = logging.getLogger(__name__)


def _get_loop() -> asyncio.AbstractEventLoop | None:
    """Safe retrieval of the current event loop."""
    with contextlib.suppress(RuntimeError):
        return asyncio.get_event_loop()
    return None


def _cancel_running_tasks(ingestion_router, loop) -> None:
    """Cancel all tasks currently managed by the ingestion router."""
    running_tasks = getattr(ingestion_router, "_running_tasks", {})
    for job_id, task in list(running_tasks.items()):
        # Note: repository access might be through the router or orchestrator
        if hasattr(ingestion_router, "repo"):
            ingestion_router.repo.set_job_status(job_id, status="paused")
        if loop and not task.done():
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
    loop: asyncio.AbstractEventLoop | None,
    ingestion_router: "ingestion",
    prev_handlers: dict[int, Any],
) -> None:
    """Internal signal handler logic."""
    logger.warning(f"Signal {sig} received - requesting ingestion shutdown")
    ingestion_router.shutdown_manager.request_shutdown()

    # Mark jobs paused and cancel running tasks promptly
    try:
        _cancel_running_tasks(ingestion_router, loop)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Failed to cancel running ingestion tasks on signal: {exc}")

    # Chain to the previous handler so uvicorn still stops
    _chain_signal_handler(sig, frame, prev_handlers, _handle_ingestion_shutdown)


def install_ingestion_signal_handlers():
    """
    Ensure SIGINT/SIGTERM immediately request ingestion shutdown so CTRL-C
    pauses jobs instead of continuing to run embeds/indexing.
    """
    from app.routers import ingestion  # noqa: PLC0415

    loop = _get_loop()
    prev_handlers = {}

    def _handler(sig, frame):
        _handle_ingestion_shutdown(sig, frame, loop, ingestion, prev_handlers)

    signals_to_install = [signal.SIGINT]
    if hasattr(signal, "SIGTERM"):
        signals_to_install.append(signal.SIGTERM)

    for sig in signals_to_install:
        try:
            prev_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, _handler)
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"Could not register signal handler for {sig}: {exc}")


