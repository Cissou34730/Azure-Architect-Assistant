# Ingestion Module Extension Guide

## Overview

The ingestion module is designed for extensibility through well-defined interfaces and dependency injection. This guide covers common extension scenarios.

## Extension Points

### 1. Custom Persistence Store

Add support for alternative state persistence backends (Azure Blob, S3, etc.).

#### Interface

```python
from app.ingestion.domain.interfaces import PersistenceStoreProtocol
from app.ingestion.domain.models import IngestionState
from typing import Dict

class PersistenceStoreProtocol(Protocol):
    def save_state(self, state: IngestionState) -> None: ...
    def load_state(self, kb_id: str) -> IngestionState | None: ...
    def load_all_states(self) -> Dict[str, IngestionState]: ...
    def delete_state(self, kb_id: str) -> None: ...
```

#### Example: Azure Blob Storage

```python
from azure.storage.blob import BlobServiceClient
import json
from app.ingestion.domain.models import IngestionState
from app.ingestion.domain.errors import PersistenceError

class AzureBlobPersistenceStore:
    """Azure Blob Storage persistence implementation."""
    
    def __init__(self, connection_string: str, container: str = "ingestion-states"):
        self.client = BlobServiceClient.from_connection_string(connection_string)
        self.container = container
        self._ensure_container()
    
    def _ensure_container(self):
        try:
            self.client.create_container(self.container)
        except Exception:
            pass  # Container may already exist
    
    def save_state(self, state: IngestionState) -> None:
        blob_name = f"{state.kb_id}/state.json"
        blob_client = self.client.get_blob_client(self.container, blob_name)
        
        data = {
            "kb_id": state.kb_id,
            "job_id": state.job_id,
            "status": state.status,
            # ... serialize all fields
        }
        
        try:
            blob_client.upload_blob(
                json.dumps(data),
                overwrite=True,
            )
        except Exception as exc:
            raise PersistenceError(state.kb_id, f"Blob upload failed: {exc}")
    
    def load_state(self, kb_id: str) -> IngestionState | None:
        blob_name = f"{kb_id}/state.json"
        blob_client = self.client.get_blob_client(self.container, blob_name)
        
        try:
            data = json.loads(blob_client.download_blob().readall())
            return self._parse_state(data)
        except Exception:
            return None
    
    # Implement other methods...
```

#### Registration

```python
from app.ingestion.application.ingestion_service import IngestionService

# Create custom persistence store
persistence = AzureBlobPersistenceStore(connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"))

# Inject into service
service = IngestionService(persistence=persistence)
```

### 2. Custom Repository

Implement alternative database backends (CosmosDB, MongoDB, etc.).

#### Interface

```python
from app.ingestion.domain.interfaces import RepositoryProtocol

class RepositoryProtocol(Protocol):
    def create_job(self, kb_id: str, source_type: str, source_config: Dict, priority: int) -> str: ...
    def get_latest_job(self, kb_id: str) -> Optional[IngestionState]: ...
    def update_job_status(self, job_id: str, status: str) -> None: ...
    def enqueue_chunks(self, job_id: str, chunks: List[Dict]) -> int: ...
    def dequeue_batch(self, job_id: str, limit: int) -> List[Dict]: ...
    def commit_batch_success(self, job_id: str, item_ids: List[int]) -> None: ...
    def commit_batch_error(self, item_id: int, error_message: str) -> None: ...
    def get_queue_stats(self, job_id: str) -> Dict[str, int]: ...
    def recover_inflight_jobs(self) -> None: ...
```

#### Example: CosmosDB Repository

```python
from azure.cosmos import CosmosClient
from app.ingestion.domain.models import IngestionState

class CosmosDBRepository:
    """CosmosDB repository implementation."""
    
    def __init__(self, endpoint: str, key: str, database: str = "ingestion"):
        self.client = CosmosClient(endpoint, key)
        self.database = self.client.get_database_client(database)
        self.jobs_container = self.database.get_container_client("jobs")
        self.queue_container = self.database.get_container_client("queue")
    
    def create_job(self, kb_id: str, source_type: str, source_config: Dict, priority: int) -> str:
        job_id = str(uuid.uuid4())
        job = {
            "id": job_id,
            "kb_id": kb_id,
            "source_type": source_type,
            "source_config": source_config,
            "priority": priority,
            "status": "running",
            "created_at": datetime.utcnow().isoformat(),
        }
        self.jobs_container.create_item(job)
        return job_id
    
    # Implement other methods...
```

### 3. Custom Metrics Backend

Add support for alternative metrics systems (OTLP, DataDog, etc.).

#### Example: OTLP Exporter

```python
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

class OTLPMetricsCollector:
    """OpenTelemetry Protocol metrics collector."""
    
    def __init__(self, endpoint: str):
        exporter = OTLPMetricExporter(endpoint=endpoint)
        reader = PeriodicExportingMetricReader(exporter, export_interval_millis=5000)
        provider = MeterProvider(metric_readers=[reader])
        metrics.set_meter_provider(provider)
        
        self.meter = metrics.get_meter("ingestion")
        self.job_counter = self.meter.create_counter("ingestion.jobs.total")
        self.chunk_counter = self.meter.create_counter("ingestion.chunks.processed")
        self.queue_gauge = self.meter.create_up_down_counter("ingestion.queue.depth")
    
    def record_job_started(self, kb_id: str, job_id: str):
        self.job_counter.add(1, {"kb_id": kb_id, "status": "started"})
    
    def record_chunks_processed(self, kb_id: str, count: int):
        self.chunk_counter.add(count, {"kb_id": kb_id})
    
    # Implement other metrics...
```

### 4. Custom Worker Strategy

Implement alternative processing strategies (batch processing, streaming, etc.).

#### Example: Batch Processor Worker

```python
from app.ingestion.domain.models import JobRuntime

class BatchProcessorWorker:
    """Process chunks in large batches with retry logic."""
    
    @staticmethod
    def run(runtime: JobRuntime) -> None:
        settings = get_settings()
        repository = DatabaseRepository()
        
        while not runtime.stop_event.is_set():
            # Dequeue larger batch
            batch = repository.dequeue_batch(runtime.job_id, limit=500)
            
            if not batch:
                runtime.stop_event.wait(timeout=1.0)
                continue
            
            # Process entire batch with retry
            for attempt in range(settings.max_retries):
                try:
                    process_batch(batch)
                    repository.commit_batch_success(runtime.job_id, [b['id'] for b in batch])
                    break
                except Exception as exc:
                    if attempt == settings.max_retries - 1:
                        for item in batch:
                            repository.commit_batch_error(item['id'], str(exc))
                    time.sleep(settings.retry_delay * (attempt + 1))
```

### 5. Custom Lifecycle Manager

Implement alternative thread management strategies.

#### Example: Process Pool Lifecycle Manager

```python
from multiprocessing import Process, Queue, Event

class ProcessPoolLifecycleManager:
    """Manage workers as separate processes instead of threads."""
    
    def start_threads(self, runtime: JobRuntime, producer_fn, consumer_fn):
        # Use processes instead of threads
        stop_queue = Queue()
        
        producer_process = Process(
            target=producer_fn,
            args=(runtime, stop_queue),
            name=f"producer-{runtime.kb_id}",
        )
        consumer_process = Process(
            target=consumer_fn,
            args=(runtime, stop_queue),
            name=f"consumer-{runtime.kb_id}",
        )
        
        runtime.producer_thread = producer_process
        runtime.consumer_thread = consumer_process
        
        producer_process.start()
        consumer_process.start()
    
    def stop_threads(self, runtime: JobRuntime, timeout: float):
        if runtime.producer_thread:
            runtime.producer_thread.terminate()
            runtime.producer_thread.join(timeout=timeout)
        if runtime.consumer_thread:
            runtime.consumer_thread.terminate()
            runtime.consumer_thread.join(timeout=timeout)
```

## Testing Extensions

### Unit Testing Custom Implementations

```python
import pytest
from app.ingestion.domain.models import IngestionState

def test_custom_persistence_store():
    """Test custom persistence store."""
    store = AzureBlobPersistenceStore(connection_string="...")
    
    state = IngestionState(kb_id="test", job_id="job-1", status="running")
    store.save_state(state)
    
    loaded = store.load_state("test")
    assert loaded.kb_id == "test"
    assert loaded.status == "running"
```

### Integration Testing

```python
@pytest.mark.integration
def test_end_to_end_with_custom_backend():
    """Test complete flow with custom backends."""
    persistence = AzureBlobPersistenceStore(...)
    repository = CosmosDBRepository(...)
    
    service = IngestionService(
        repository=repository,
        persistence=persistence,
    )
    
    # Test start/pause/resume cycle
    state = await service.start(kb_id, callable)
    assert state.status == "running"
    
    await service.pause(kb_id)
    state = service.status(kb_id)
    assert state.status == "paused"
```

## Best Practices

1. **Interface Compliance**: Always implement full protocol interface
2. **Error Handling**: Wrap external service errors in domain exceptions
3. **Resource Cleanup**: Implement proper cleanup in `__del__` or context managers
4. **Configuration**: Add configuration options to `IngestionSettings`
5. **Logging**: Use correlation logging for traceability
6. **Testing**: Provide unit and integration tests for custom implementations
7. **Documentation**: Document configuration and usage in extension

## Common Patterns

### Factory Pattern

```python
def create_persistence_store(backend: str) -> PersistenceStoreProtocol:
    """Factory to create persistence store based on configuration."""
    if backend == "local_disk":
        return LocalDiskPersistenceStore()
    elif backend == "azure_blob":
        return AzureBlobPersistenceStore(...)
    elif backend == "s3":
        return S3PersistenceStore(...)
    else:
        raise ValueError(f"Unknown backend: {backend}")
```

### Dependency Injection

```python
# Configure dependencies
persistence = create_persistence_store(settings.persistence_backend)
repository = DatabaseRepository()
lifecycle = LifecycleManager()

# Inject into service
service = IngestionService(
    repository=repository,
    persistence=persistence,
    lifecycle=lifecycle,
)
```

## Migration Checklist

When adding a new extension:

- [ ] Implement protocol interface completely
- [ ] Add configuration options to `IngestionSettings`
- [ ] Add factory function for dependency injection
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Update documentation
- [ ] Add example usage
- [ ] Test with existing service
- [ ] Benchmark performance
- [ ] Add monitoring/metrics

## Support

For questions or issues with extensions:

1. Check interface definitions in `domain/interfaces/`
2. Review existing implementations in `infrastructure/`
3. Consult test examples in `tests/`
4. See architecture documentation in `docs/ingestion/ARCHITECTURE.md`
