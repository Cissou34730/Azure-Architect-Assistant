"""Runtime metadata structures for ingestion jobs."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .state import IngestionState


@dataclass
class JobRuntime:
    """Runtime metadata for a producer/consumer job."""

    job_id: str
    kb_id: str
    state: IngestionState
    stop_event: threading.Event = field(default_factory=threading.Event)
    pause_event: threading.Event = field(default_factory=threading.Event)
    canceled: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)
    producer_thread: threading.Thread | None = None
    consumer_thread: threading.Thread | None = None
    producer_target: Callable[..., Any] | None = None
    consumer_target: Callable[..., Any] | None = None
    producer_args: tuple[Any, ...] = field(default_factory=tuple)
    producer_kwargs: dict[str, Any] = field(default_factory=dict)
