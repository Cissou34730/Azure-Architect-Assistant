"""Domain interfaces and protocols for ingestion components."""

from .repository import RepositoryProtocol
from .persistence import PersistenceStoreProtocol
from .lifecycle import LifecycleManagerProtocol
from .worker import ProducerWorkerProtocol, ConsumerWorkerProtocol

__all__ = [
    "RepositoryProtocol",
    "PersistenceStoreProtocol",
    "LifecycleManagerProtocol",
    "ProducerWorkerProtocol",
    "ConsumerWorkerProtocol",
]
