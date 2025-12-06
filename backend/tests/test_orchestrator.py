import asyncio
import pytest

from app.ingestion.core.orchestrator import IngestionOrchestrator
from app.ingestion.core.signals import Signal


@pytest.mark.asyncio
async def test_orchestrator_desired_state_updates():
    orch = IngestionOrchestrator.instance()
    job_id = "test-job"

    assert orch.get_desired_state(job_id) == "idle"

    await orch.publish(job_id, Signal.START)
    assert orch.get_desired_state(job_id) == "running"

    await orch.publish(job_id, Signal.PAUSE)
    assert orch.get_desired_state(job_id) == "paused"

    await orch.publish(job_id, Signal.RESUME)
    assert orch.get_desired_state(job_id) == "running"

    await orch.publish(job_id, Signal.CANCEL)
    assert orch.get_desired_state(job_id) == "canceled"


@pytest.mark.asyncio
async def test_orchestrator_queue_delivers_signals():
    orch = IngestionOrchestrator.instance()
    job_id = "test-queue"

    await orch.publish(job_id, Signal.START)
    await orch.publish(job_id, Signal.PAUSE)

    s1 = await orch.next_signal(job_id)
    s2 = await orch.next_signal(job_id)

    assert s1 == Signal.START
    assert s2 == Signal.PAUSE
