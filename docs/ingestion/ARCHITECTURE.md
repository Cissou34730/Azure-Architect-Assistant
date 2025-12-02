# Ingestion Module Architecture

## Overview

The refactored ingestion module follows a layered architecture with clear separation of concerns:

- **Domain Layer**: Core business logic, models, enums, interfaces
- **Infrastructure Layer**: Persistence implementations (DB, filesystem)
- **Application Layer**: Orchestration services and utilities
- **Workers Layer**: Thread-based producer/consumer implementation

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    API / Routers                         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│          Application Layer                               │
│  ┌──────────────────────────────────────────────┐       │
│  │  IngestionService (Orchestrator)             │       │
│  │  - start/resume/pause/cancel/status          │       │
│  └──────────────────────────────────────────────┘       │
│  ┌──────────────────┐  ┌─────────────────────┐         │
│  │ LifecycleManager │  │  AsyncioExecutor     │         │
│  └──────────────────┘  └─────────────────────┘         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Workers Layer                               │
│  ┌──────────────────┐  ┌─────────────────────┐         │
│  │ ProducerWorker   │  │  ConsumerWorker     │         │
│  └──────────────────┘  └─────────────────────┘         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│          Infrastructure Layer                            │
│  ┌──────────────────┐  ┌─────────────────────┐         │
│  │  Repository       │  │  PersistenceStore   │         │
│  │  (Database)       │  │  (Disk/Azure)       │         │
│  └──────────────────┘  └─────────────────────┘         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│               Domain Layer                               │
│  ┌──────────────────────────────────────────────┐       │
│  │  Models: IngestionState, JobRuntime          │       │
│  │  Enums: JobStatus, JobPhase                  │       │
│  │  Errors: DomainExceptions                    │       │
│  │  Interfaces: Protocols                       │       │
│  └──────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────┘
```

## Module Structure

```
backend/app/ingestion/
├── domain/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── state.py           # IngestionState with pydantic schema
│   │   └── runtime.py         # JobRuntime metadata
│   ├── interfaces/
│   │   ├── __init__.py
│   │   ├── repository.py      # Repository protocol
│   │   ├── persistence.py     # PersistenceStore protocol
│   │   ├── lifecycle.py       # LifecycleManager protocol
│   │   └── worker.py          # Worker protocols
│   ├── enums.py               # JobStatus, JobPhase, state machine
│   └── errors.py              # Domain exceptions
├── infrastructure/
│   ├── __init__.py
│   ├── repository.py          # DatabaseRepository implementation
│   └── persistence.py         # LocalDiskPersistenceStore implementation
├── application/
│   ├── __init__.py
│   ├── ingestion_service.py   # Main orchestrator
│   ├── lifecycle.py           # Thread lifecycle manager
│   └── executor.py            # Asyncio utilities
├── workers/
│   ├── __init__.py
│   ├── producer.py            # Producer worker thread
│   └── consumer.py            # Consumer worker thread
├── config/
│   ├── __init__.py
│   └── settings.py            # Typed configuration
├── observability/
│   ├── __init__.py
│   ├── logging.py             # Correlation ID logging
│   └── metrics.py             # Prometheus-style metrics
└── tests/
    ├── __init__.py
    ├── conftest.py            # Test fixtures
    ├── test_state_machine.py
    ├── test_persistence.py
    └── test_lifecycle.py
```

## Key Components

### IngestionService

Central orchestrator managing job lifecycle:

```python
from app.ingestion.application.ingestion_service import IngestionService

service = IngestionService.instance()

# Start fresh ingestion
state = await service.start(kb_id, run_callable, kb_config, state=state)

# Pause running job
await service.pause(kb_id)

# Resume from checkpoint
await service.resume(kb_id, run_callable, kb_config, state=state)

# Cancel job
await service.cancel(kb_id)

# Get status
state = service.status(kb_id)
```

### State Machine

Job transitions are validated via state machine:

```python
from app.ingestion.domain.enums import JobStatus, transition_or_raise

# Valid transition
transition_or_raise(JobStatus.RUNNING, JobStatus.PAUSED)  # OK

# Invalid transition raises StateTransitionError
transition_or_raise(JobStatus.COMPLETED, JobStatus.RUNNING)  # Error!
```

### Configuration

Environment-based typed configuration:

```python
from app.ingestion.config import get_settings

settings = get_settings()
batch_size = settings.batch_size
data_root = settings.data_root
```

Environment variables:
- `INGESTION_BATCH_SIZE`: Queue batch size (default: 50)
- `INGESTION_DATA_ROOT`: Data directory (default: data/knowledge_bases)
- `INGESTION_THREAD_JOIN_TIMEOUT`: Thread join timeout (default: 5.0)
- `INGESTION_ENABLE_METRICS`: Enable metrics collection (default: true)

### Observability

Correlation ID logging:

```python
from app.ingestion.observability.logging import set_correlation_context, get_correlated_logger

set_correlation_context(job_id="job-123", kb_id="kb-456")
logger = get_correlated_logger(__name__)
logger.info("Processing chunk")  # Automatically includes job_id and kb_id
```

Metrics:

```python
from app.ingestion.observability.metrics import (
    record_job_started,
    record_chunks_processed,
    record_queue_depth,
)

record_job_started(kb_id, job_id)
record_chunks_processed(kb_id, count=100)
record_queue_depth(kb_id, job_id, depth=50)
```

## Design Principles

1. **Dependency Inversion**: Application layer depends on domain interfaces, not concrete implementations
2. **Single Responsibility**: Each layer has clear responsibilities
3. **Testability**: Interfaces enable dependency injection and mocking
4. **Extensibility**: New persistence backends can be added without changing service logic
5. **Observability**: Structured logging and metrics built-in

## Extension Points

### Custom Persistence Store

Implement `PersistenceStoreProtocol`:

```python
from app.ingestion.domain.interfaces import PersistenceStoreProtocol

class AzureBlobPersistenceStore:
    def save_state(self, state: IngestionState) -> None:
        # Upload to Azure Blob Storage
        pass
    
    def load_state(self, kb_id: str) -> IngestionState | None:
        # Download from Azure Blob Storage
        pass
```

### Custom Repository

Implement `RepositoryProtocol`:

```python
from app.ingestion.domain.interfaces import RepositoryProtocol

class CosmosDBRepository:
    def create_job(self, kb_id: str, ...) -> str:
        # Create job in CosmosDB
        pass
```

## Migration Guide

To migrate from old `service_components/manager.py`:

1. Replace imports:
   ```python
   # Old
   from app.ingestion.service_components.manager import IngestionService
   
   # New
   from app.ingestion.application.ingestion_service import IngestionService
   ```

2. Service API remains compatible - no changes to calling code needed

3. Configuration now via environment variables (see Configuration section)

## Testing

Run tests:

```bash
pytest backend/app/ingestion/tests/
```

Test with coverage:

```bash
pytest backend/app/ingestion/tests/ --cov=app.ingestion --cov-report=html
```

## Performance Considerations

- **Batch Size**: Tune `INGESTION_BATCH_SIZE` for optimal throughput (default 50)
- **Thread Timeouts**: Adjust `INGESTION_THREAD_JOIN_TIMEOUT` for graceful shutdown
- **Queue Polling**: Configure `INGESTION_CONSUMER_POLL_INTERVAL` for responsiveness vs CPU usage

## Future Enhancements

1. **Azure Files/Blob Persistence**: Add cloud-based state persistence
2. **Distributed Locking**: Support multi-instance deployments
3. **Priority Queues**: Process high-priority jobs first
4. **Retry Policies**: Configurable retry with exponential backoff
5. **Dead Letter Queue**: Handle permanently failed items
6. **Metrics Export**: Prometheus exporter endpoint
