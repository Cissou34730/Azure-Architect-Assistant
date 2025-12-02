# Ingestion Module

Resilient, layered ingestion system for knowledge base processing with producer-consumer architecture.

## Features

- **Layered Architecture**: Clean separation of domain, infrastructure, and application concerns
- **State Machine**: Validated job transitions with state checkpoints
- **Pause/Resume**: Graceful pause and resume from checkpoint
- **Thread Safety**: Coordinated producer/consumer threads with cooperative shutdown
- **Observability**: Correlation ID logging and Prometheus-style metrics
- **Extensible**: Protocol-based interfaces for custom backends
- **Type-Safe**: Fully typed with pydantic schemas for API responses
- **Tested**: Comprehensive unit and integration test coverage

## Quick Start

```python
from app.ingestion.application.ingestion_service import IngestionService

# Get service instance
service = IngestionService.instance()

# Start ingestion
state = await service.start(
    kb_id="my-kb",
    run_callable=my_ingestion_function,
    kb_config=config,
)

# Check status
status = service.status("my-kb")
print(f"Status: {status.status}, Progress: {status.progress}%")

# Pause if needed
await service.pause("my-kb")

# Resume from checkpoint
await service.resume("my-kb", my_ingestion_function, kb_config=config)
```

## Architecture

```
┌─────────────────────────────────────────┐
│     IngestionService (Orchestrator)     │
├─────────────────────────────────────────┤
│  LifecycleManager │ AsyncioExecutor     │
├─────────────────────────────────────────┤
│  ProducerWorker   │ ConsumerWorker      │
├─────────────────────────────────────────┤
│  Repository       │ PersistenceStore    │
├─────────────────────────────────────────┤
│  Domain Models    │ Interfaces          │
└─────────────────────────────────────────┘
```

See [ARCHITECTURE.md](../../../docs/ingestion/ARCHITECTURE.md) for details.

## Configuration

Settings are loaded from `config/ingestion.config.json`:

```json
{
  "batch_size": 50,
  "dequeue_timeout": 0.1,
  "thread_join_timeout": 5.0,
  "persistence_backend": "local_disk",
  "data_root": "data/knowledge_bases",
  "log_level": "INFO",
  "enable_metrics": true
}
```

See [CONFIGURATION.md](../../../docs/ingestion/CONFIGURATION.md) for all options.

## Module Structure

```
app/ingestion/
├── domain/              # Core business logic
│   ├── models/          # State, Runtime DTOs
│   ├── interfaces/      # Protocol definitions
│   ├── enums.py         # JobStatus, state machine
│   └── errors.py        # Domain exceptions
├── infrastructure/      # External adapters
│   ├── repository.py    # Database operations
│   └── persistence.py   # State checkpointing
├── application/         # Orchestration
│   ├── ingestion_service.py
│   ├── lifecycle.py     # Thread management
│   └── executor.py      # Asyncio utilities
├── workers/             # Thread workers
│   ├── producer.py      # Crawl, chunk, enqueue
│   └── consumer.py      # Dequeue, embed, index
├── config/              # Typed settings
├── observability/       # Logging, metrics
└── tests/               # Test suite
```

## Testing

Run tests:

```bash
pytest backend/app/ingestion/tests/ -v
```

With coverage:

```bash
pytest backend/app/ingestion/tests/ --cov=app.ingestion --cov-report=html
```

## Extension

Implement custom backends via protocols:

```python
from app.ingestion.domain.interfaces import PersistenceStoreProtocol

class AzureBlobPersistenceStore:
    def save_state(self, state: IngestionState) -> None:
        # Custom implementation
        pass
```

See [EXTENSION_GUIDE.md](../../../docs/ingestion/EXTENSION_GUIDE.md) for details.

## API

### IngestionService

**`start(kb_id, run_callable, *args, **kwargs) -> IngestionState`**
- Start fresh ingestion for a knowledge base

**`resume(kb_id, run_callable, *args, **kwargs) -> bool`**
- Resume paused ingestion from checkpoint

**`pause(kb_id) -> bool`**
- Gracefully pause running ingestion

**`cancel(kb_id) -> bool`**
- Cancel running ingestion

**`status(kb_id) -> IngestionState | None`**
- Get current status for knowledge base

**`list_kb_states() -> Dict[str, IngestionState]`**
- List all KB states

### State Machine

Valid transitions:
- `pending` → `running`, `cancelled`
- `running` → `paused`, `completed`, `failed`, `cancelled`
- `paused` → `running`, `cancelled`
- `completed`, `failed`, `cancelled` → (terminal)

## Observability

### Logging

```python
from app.ingestion.observability.logging import set_correlation_context

set_correlation_context(job_id="job-123", kb_id="kb-456")
# All logs will include correlation IDs
```

### Metrics

```python
from app.ingestion.observability.metrics import (
    record_job_started,
    record_chunks_processed,
    get_metrics_collector,
)

record_job_started(kb_id, job_id)
record_chunks_processed(kb_id, count=100)

# Export metrics
collector = get_metrics_collector()
metrics = collector.get_all_metrics()
```

## Performance

**Recommendations**:
- **High throughput**: `INGESTION_BATCH_SIZE=200`, `DEQUEUE_TIMEOUT=0.01`
- **Low resource**: `INGESTION_BATCH_SIZE=10`, `DEQUEUE_TIMEOUT=0.5`
- **Balanced**: Use defaults

## Migration

From old `service_components/manager.py`:

1. Update import:
   ```python
   # Old
   from app.ingestion.service_components.manager import IngestionService
   
   # New
   from app.ingestion.application.ingestion_service import IngestionService
   ```

2. API remains compatible - no code changes needed

## Documentation

- [Architecture Guide](../../../docs/ingestion/ARCHITECTURE.md)
- [Configuration Reference](../../../docs/ingestion/CONFIGURATION.md)
- [Extension Guide](../../../docs/ingestion/EXTENSION_GUIDE.md)

## License

Internal project - Avanade
