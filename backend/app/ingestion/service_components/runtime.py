"""Runtime metadata structures for ingestion jobs."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple

from .state import IngestionState


@dataclass
class JobRuntime:
    """Runtime metadata for a producer/consumer job."""

    job_id: str
    kb_id: str
    state: IngestionState
    stop_event: threading.Event = field(default_factory=threading.Event)
    lock: threading.Lock = field(default_factory=threading.Lock)
    producer_thread: Optional[threading.Thread] = None
    consumer_thread: Optional[threading.Thread] = None
    producer_target: Optional[Callable[..., Any]] = None
    consumer_target: Optional[Callable[..., Any]] = None
    producer_args: Tuple[Any, ...] = field(default_factory=tuple)
    producer_kwargs: Dict[str, Any] = field(default_factory=dict)
