# Ingestion Configuration Guide

## Overview

The ingestion module uses JSON-based typed configuration via `IngestionSettings`. Configuration is loaded from `backend/app/ingestion/config/ingestion.config.json`.

## Configuration File

**Location**: `backend/app/ingestion/config/ingestion.config.json`

**Format**: JSON

**Example**:
```json
{
  "data_root": "data/knowledge_bases",
  "batch_size": 50,
  "dequeue_timeout": 0.1,
  "consumer_poll_interval": 0.1,
  "thread_join_timeout": 5.0,
  "shutdown_grace_period": 30.0,
  "max_retries": 3,
  "retry_delay": 1.0,
  "persistence_backend": "local_disk",
  "state_file_name": "state.json",
  "log_level": "INFO",
  "enable_correlation_ids": true,
  "enable_metrics": true,
  "metrics_backend": "prometheus",
  "metrics_port": 9090
}
```

## Configuration Settings

### Paths

**`data_root`**
- **Type**: String (path)
- **Default**: `data/knowledge_bases`
- **Description**: Root directory for knowledge base data and state files

### Queue Configuration

**`batch_size`**
- **Type**: Integer
- **Default**: `50`
- **Description**: Number of chunks to dequeue and process in each batch
- **Tuning**: Increase for higher throughput, decrease for lower memory usage

**`dequeue_timeout`**
- **Type**: Float (seconds)
- **Default**: `0.1`
- **Description**: Wait time when queue is empty before retrying
- **Tuning**: Increase to reduce CPU usage, decrease for faster responsiveness

**`consumer_poll_interval`**
- **Type**: Float (seconds)
- **Default**: `0.1`
- **Description**: Sleep interval between dequeue attempts
- **Tuning**: Balance between responsiveness and CPU efficiency

### Thread Lifecycle

**`thread_join_timeout`**
- **Type**: Float (seconds)
- **Default**: `5.0`
- **Description**: Maximum time to wait for thread exit during shutdown
- **Tuning**: Increase for long-running operations, decrease for faster shutdown

**`shutdown_grace_period`**
- **Type**: Float (seconds)
- **Default**: `30.0`
- **Description**: Total maximum time for graceful shutdown
- **Tuning**: Must be longer than thread join timeout

### Retry Policy

**`max_retries`**
- **Type**: Integer
- **Default**: `3`
- **Description**: Maximum retry attempts for failed operations
- **Tuning**: Increase for transient errors, decrease for faster failure detection

**`retry_delay`**
- **Type**: Float (seconds)
- **Default**: `1.0`
- **Description**: Delay between retry attempts
- **Tuning**: Increase for rate-limited APIs

### Persistence

**`persistence_backend`**
- **Type**: String
- **Default**: `local_disk`
- **Options**: `local_disk`, `azure_files`, `azure_blob`
- **Description**: Backend for state persistence

**`state_file_name`**
- **Type**: String
- **Default**: `state.json`
- **Description**: Filename for state checkpoint files

### Logging

**`log_level`**
- **Type**: String
- **Default**: `INFO`
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description**: Logging level for ingestion module

**`enable_correlation_ids`**
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable correlation ID injection in logs
- **Tuning**: Disable for simpler logs in development

### Metrics

**`enable_metrics`**
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable metrics collection
- **Tuning**: Disable for minimal overhead

**`metrics_backend`**
- **Type**: String
- **Default**: `prometheus`
- **Options**: `prometheus`, `otlp`, `none`
- **Description**: Metrics backend for export

**`metrics_port`**
- **Type**: Integer
- **Default**: `9090`
- **Description**: Port for metrics exposition (if applicable)

## Example Configurations

### Development

```json
{
  "data_root": "./dev-data",
  "batch_size": 10,
  "log_level": "DEBUG",
  "enable_metrics": false
}
```

### Production

```json
{
  "data_root": "/data/knowledge_bases",
  "batch_size": 100,
  "thread_join_timeout": 10.0,
  "max_retries": 5,
  "log_level": "INFO",
  "enable_metrics": true,
  "metrics_backend": "prometheus"
}
```

### Azure Cloud

```json
{
  "persistence_backend": "azure_blob",
  "data_root": "/tmp/ingestion-cache",
  "batch_size": 200,
  "enable_correlation_ids": true,
  "log_level": "INFO"
}
```

## Programmatic Configuration

For testing or custom scenarios:

```python
from app.ingestion.config import IngestionSettings, set_settings
from pathlib import Path

# Create custom settings
settings = IngestionSettings(
    data_root=Path("/custom/path"),
    batch_size=25,
    log_level="DEBUG",
    enable_metrics=False,
)

# Apply globally
set_settings(settings)

# Or load from custom JSON file
custom_settings = IngestionSettings.from_json(Path("path/to/custom.config.json"))
set_settings(custom_settings)
```

## Performance Tuning

### High Throughput

For maximum throughput with sufficient resources:

```json
{
  "batch_size": 200,
  "dequeue_timeout": 0.01,
  "consumer_poll_interval": 0.01,
  "max_retries": 1
}
```

### Low Resource

For resource-constrained environments:

```json
{
  "batch_size": 10,
  "dequeue_timeout": 0.5,
  "consumer_poll_interval": 0.5,
  "thread_join_timeout": 2.0
}
```

### Balanced (Recommended)

Balanced configuration for most scenarios (default values):

```json
{
  "batch_size": 50,
  "dequeue_timeout": 0.1,
  "consumer_poll_interval": 0.1,
  "thread_join_timeout": 5.0,
  "max_retries": 3
}
```

## Monitoring Configuration

### Enable Full Observability

```json
{
  "log_level": "INFO",
  "enable_correlation_ids": true,
  "enable_metrics": true,
  "metrics_backend": "prometheus",
  "metrics_port": 9090
}
```

### Minimal Overhead

```json
{
  "log_level": "WARNING",
  "enable_correlation_ids": false,
  "enable_metrics": false
}
```

## Configuration Validation

Settings are validated at runtime. Invalid values will raise errors:

```python
from app.ingestion.config import get_settings

settings = get_settings()
assert settings.batch_size > 0
assert settings.thread_join_timeout > 0
```

## Best Practices

1. **Environment-Specific**: Use separate env files per environment
2. **Secret Management**: Store Azure connection strings in key vaults
3. **Tuning**: Start with defaults, measure performance, then tune
4. **Logging**: Use INFO or WARNING in production to reduce noise
5. **Metrics**: Always enable metrics in production for observability
6. **Timeouts**: Set timeouts based on expected operation duration
7. **Retries**: Configure retries based on API rate limits
