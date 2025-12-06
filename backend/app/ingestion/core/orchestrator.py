import asyncio
from typing import Dict

from .signals import Signal, DesiredState


class IngestionOrchestrator:
    """
    In-process orchestrator that publishes signals and tracks desired state per job.
    Singleton accessed via `IngestionOrchestrator.instance()`.
    """

    _singleton = None

    def __init__(self) -> None:
        self._desired_state: Dict[str, DesiredState] = {}
        self._signal_queues: Dict[str, asyncio.Queue[Signal]] = {}

    @classmethod
    def instance(cls) -> "IngestionOrchestrator":
        if not cls._singleton:
            cls._singleton = IngestionOrchestrator()
        return cls._singleton

    def _ensure_job(self, job_id: str) -> None:
        if job_id not in self._signal_queues:
            self._signal_queues[job_id] = asyncio.Queue()
            self._desired_state[job_id] = "idle"

    async def publish(self, job_id: str, signal: Signal) -> None:
        self._ensure_job(job_id)
        # Update desired state
        if signal == Signal.START:
            self._desired_state[job_id] = "running"
        elif signal == Signal.PAUSE:
            self._desired_state[job_id] = "paused"
        elif signal == Signal.RESUME:
            self._desired_state[job_id] = "running"
        elif signal == Signal.CANCEL:
            self._desired_state[job_id] = "canceled"
        elif signal == Signal.SHUTDOWN:
            self._desired_state[job_id] = "shutdown"

        await self._signal_queues[job_id].put(signal)

    def get_desired_state(self, job_id: str) -> DesiredState:
        self._ensure_job(job_id)
        return self._desired_state[job_id]

    async def next_signal(self, job_id: str) -> Signal:
        self._ensure_job(job_id)
        return await self._signal_queues[job_id].get()
