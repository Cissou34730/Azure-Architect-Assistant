import signal
import asyncio
import logging

logger = logging.getLogger(__name__)


def install_ingestion_signal_handlers():
    """
    Ensure SIGINT/SIGTERM immediately request ingestion shutdown so CTRL-C
    pauses jobs instead of continuing to run embeds/indexing, while still
    letting uvicorn exit normally.
    """
    from app.routers import ingestion
    from app.ingestion.application.orchestrator import IngestionOrchestrator

    loop = None
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        pass  # no running loop yet

    prev_handlers = {}

    def _handler(sig, frame):
        logger.warning(f"Signal {sig} received - requesting ingestion shutdown")
        IngestionOrchestrator.request_shutdown()
        # Mark jobs paused and cancel running tasks promptly
        try:
            for job_id, task in list(ingestion._running_tasks.items()):
                ingestion.repo.set_job_status(job_id, status="paused")
                if loop and not task.done():
                    loop.call_soon_threadsafe(task.cancel)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"Failed to cancel running ingestion tasks on signal: {exc}")

        # Chain to the previous handler so uvicorn still stops
        prev = prev_handlers.get(sig)
        if prev in (None, signal.SIG_IGN):
            return
        if prev == signal.SIG_DFL:
            if sig == signal.SIGINT:
                raise KeyboardInterrupt()
            return
        if prev is _handler:
            return
        try:
            prev(sig, frame)
        except KeyboardInterrupt:
            raise
        except Exception:  # pragma: no cover - avoid masking shutdown
            logger.debug(
                "Previous signal handler raised; continuing shutdown", exc_info=True
            )

    signals_to_install = [signal.SIGINT]
    if hasattr(signal, "SIGTERM"):
        signals_to_install.append(signal.SIGTERM)

    for sig in signals_to_install:
        try:
            prev_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, _handler)
        except Exception as exc:  # pragma: no cover - Windows/host limitations
            logger.debug(f"Could not register signal handler for {sig}: {exc}")
