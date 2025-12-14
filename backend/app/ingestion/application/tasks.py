"""
Dataclasses and task metadata for orchestrator steps.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .policies import StepName


@dataclass
class ProcessingTask:
    """
    Task metadata for logging and observability.

    Attributes:
        job_id: Job identifier
        kb_id: Knowledge base identifier
        step: Current pipeline step
        payload: Step-specific data
        batch_id: Optional batch number
        chunk_index: Optional chunk index within batch
    """

    job_id: str
    kb_id: str
    step: StepName
    payload: Dict[str, Any]
    batch_id: Optional[int] = None
    chunk_index: Optional[int] = None
