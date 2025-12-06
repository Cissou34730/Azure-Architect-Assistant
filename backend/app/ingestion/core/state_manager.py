from typing import Dict, Any

from .phase import PhaseStatus


def aggregate_job_status(phase_statuses: Dict[str, Dict[str, Any]]) -> str:
    """
    Compute overall job status from per-phase statuses.
    phase_statuses: {phase_name: {"status": <PhaseStatus.value>, ...}}
    """
    if not phase_statuses:
        return "idle"

    statuses = {info.get("status", "idle") for info in phase_statuses.values()}

    if PhaseStatus.FAILED.value in statuses:
        return "failed"
    if PhaseStatus.CANCELED.value in statuses:
        return "canceled"
    if statuses == {PhaseStatus.COMPLETED.value}:
        return "completed"
    if PhaseStatus.RUNNING.value in statuses:
        return "running"
    if PhaseStatus.PAUSED.value in statuses and PhaseStatus.RUNNING.value not in statuses:
        return "paused"
    return "idle"
