"""Domain interfaces and protocols for ingestion components."""

from .repository import RepositoryProtocol
from .lifecycle import LifecycleManagerProtocol
from .worker import ProducerWorkerProtocol, ConsumerWorkerProtocol

__all__ = [
    "RepositoryProtocol",
    "LifecycleManagerProtocol",
    "ProducerWorkerProtocol",
    "ConsumerWorkerProtocol",
]
