"""Domain interfaces and protocols for ingestion components."""

from .lifecycle import LifecycleManagerProtocol
from .repository import RepositoryProtocol
from .worker import ConsumerWorkerProtocol, ProducerWorkerProtocol

__all__ = [
    'ConsumerWorkerProtocol',
    'LifecycleManagerProtocol',
    'ProducerWorkerProtocol',
    'RepositoryProtocol',
]
