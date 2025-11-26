# Generic Ingestion API Documentation

## Overview
The Generic Ingestion API provides endpoints for creating, managing, and monitoring knowledge base ingestion jobs. It supports multiple source types (web documentation, generic web, local files) with real-time progress tracking.

**Base URL**: `http://localhost:8000/api/ingestion`

---

## Endpoints

### 1. Create Knowledge Base
**POST** `/kb/create`

Create a new knowledge base configuration.

**Request Body**:
```json
{
  "kb_id": "azure-arch",
  "name": "Azure Architecture",
  "description": "Azure architecture patterns and best practices",
  "source_type": "web_documentation",
  "source_config": {
    "start_urls": ["https://learn.microsoft.com/en-us/azure/architecture/"],
    "allowed_domains": ["learn.microsoft.com"],
    "path_prefix": "/en-us/azure/architecture/",
    "follow_links": true,
    "max_pages": 1000
  },
  "embedding_model": "text-embedding-3-small",
  "chunk_size": 800,
  "chunk_overlap": 120,
  "profiles": ["chat", "kb-query"],
  "priority": 1
}
```

**Response** (200 OK):
```json
{
  "message": "Knowledge base 'Azure Architecture' created successfully",
  "kb_id": "azure-arch",
  "kb_name": "Azure Architecture"
}
```

**Errors**:
- `400` - KB already exists
- `500` - Server error

---

### 2. Start Ingestion
**POST** `/kb/{kb_id}/start`

Start an ingestion job for a knowledge base.

**Path Parameters**:
- `kb_id` (string): Knowledge base identifier

**Request Body**: Empty or `{}`

**Response** (200 OK):
```json
{
  "message": "Ingestion started for KB 'Azure Architecture'",
  "job_id": "job-20240115-143022-abc123",
  "kb_id": "azure-arch"
}
```

**Errors**:
- `404` - KB not found
- `500` - Server error

---

### 3. Get Job Status
**GET** `/kb/{kb_id}/status`

Get the latest job status for a knowledge base.

**Path Parameters**:
- `kb_id` (string): Knowledge base identifier

**Response** (200 OK):
```json
{
  "job_id": "job-20240115-143022-abc123",
  "kb_id": "azure-arch",
  "status": "RUNNING",
  "phase": "CRAWLING",
  "progress": 45.5,
  "message": "Crawled 455/1000 pages",
  "error": null,
  "metrics": {
    "pages_crawled": 455,
    "pages_total": 1000,
    "documents_cleaned": 0,
    "chunks_created": 0,
    "chunks_embedded": 0
  },
  "started_at": "2024-01-15T14:30:22.123Z",
  "completed_at": null
}
```

**Job Status Values**:
- `PENDING` - Job created but not started
- `RUNNING` - Job in progress
- `COMPLETED` - Job finished successfully
- `FAILED` - Job failed with error
- `CANCELLED` - Job cancelled by user

**Job Phase Values**:
- `PENDING` - Not started
- `CRAWLING` - Downloading documents
- `CLEANING` - Extracting text content
- `EMBEDDING` - Creating embeddings
- `INDEXING` - Building vector index
- `COMPLETED` - Finished
- `FAILED` - Error occurred

**Errors**:
- `404` - No job found for KB
- `500` - Server error

---

### 4. Cancel Job
**POST** `/kb/{kb_id}/cancel`

Cancel a running ingestion job.

**Path Parameters**:
- `kb_id` (string): Knowledge base identifier

**Response** (200 OK):
```json
{
  "message": "Ingestion job job-20240115-143022-abc123 cancelled",
  "job_id": "job-20240115-143022-abc123",
  "kb_id": "azure-arch"
}
```

**Errors**:
- `404` - No job found for KB
- `400` - Job is not running (already completed/failed/cancelled)
- `500` - Server error

---

### 5. List Jobs
**GET** `/jobs?kb_id={kb_id}&limit={limit}`

List all ingestion jobs, optionally filtered by KB.

**Query Parameters**:
- `kb_id` (string, optional): Filter by knowledge base
- `limit` (int, optional): Max results to return (default: 50)

**Response** (200 OK):
```json
{
  "jobs": [
    {
      "job_id": "job-20240115-143022-abc123",
      "kb_id": "azure-arch",
      "status": "RUNNING",
      "phase": "CRAWLING",
      "progress": 45.5,
      "message": "Crawled 455/1000 pages",
      "error": null,
      "metrics": { ... },
      "started_at": "2024-01-15T14:30:22.123Z",
      "completed_at": null
    },
    {
      "job_id": "job-20240115-120000-xyz789",
      "kb_id": "waf",
      "status": "COMPLETED",
      "phase": "COMPLETED",
      "progress": 100.0,
      "message": "Successfully ingested KB 'Well-Architected Framework'",
      "error": null,
      "metrics": {
        "pages_crawled": 342,
        "documents_cleaned": 342,
        "chunks_created": 4850,
        "chunks_embedded": 4850
      },
      "started_at": "2024-01-15T12:00:00.000Z",
      "completed_at": "2024-01-15T12:25:30.456Z"
    }
  ]
}
```

**Errors**:
- `500` - Server error

---

## Source Types

### 1. Web Documentation (`web_documentation`)
For structured documentation sites (e.g., Microsoft Learn, Read the Docs).

**Source Config**:
```json
{
  "start_urls": ["https://docs.example.com/guide/"],
  "allowed_domains": ["docs.example.com"],
  "path_prefix": "/guide/",
  "follow_links": true,
  "max_pages": 1000
}
```

### 2. Generic Web (`web_generic`)
For any website with unstructured content.

**Source Config**:
```json
{
  "urls": [
    "https://example.com/page1",
    "https://example.com/page2"
  ],
  "follow_links": false,
  "max_depth": 1,
  "same_domain_only": true
}
```

### 3. Local Files (`local_files`)
For local document ingestion (PDF, DOCX, TXT, etc.).

**Source Config**:
```json
{
  "file_paths": [
    "/path/to/document1.pdf",
    "/path/to/document2.docx"
  ],
  "recursive": true,
  "file_types": ["pdf", "docx", "txt", "md"]
}
```

---

## Progress Tracking

### Polling Pattern
To monitor job progress, poll the status endpoint every 2-3 seconds:

```javascript
async function monitorJob(kbId) {
  const pollInterval = 2000; // 2 seconds
  
  while (true) {
    const response = await fetch(`/api/ingestion/kb/${kbId}/status`);
    const job = await response.json();
    
    console.log(`${job.phase}: ${job.progress}% - ${job.message}`);
    
    if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(job.status)) {
      break;
    }
    
    await new Promise(resolve => setTimeout(resolve, pollInterval));
  }
}
```

### Progress Metrics
The `metrics` object contains real-time statistics:

```json
{
  "pages_crawled": 455,      // Documents downloaded
  "pages_total": 1000,       // Expected total (if known)
  "documents_cleaned": 342,  // Documents processed
  "chunks_created": 2850,    // Text chunks generated
  "chunks_embedded": 2850    // Chunks with embeddings
}
```

---

## Error Handling

### Common Errors

**KB Already Exists**:
```json
{
  "detail": "KB 'azure-arch' already exists"
}
```

**KB Not Found**:
```json
{
  "detail": "KB 'unknown-kb' not found"
}
```

**Job Not Running**:
```json
{
  "detail": "Job job-123 is not running (status: COMPLETED)"
}
```

**No Job Found**:
```json
{
  "detail": "No ingestion job found for KB 'azure-arch'"
}
```

---

## Testing

Use the provided test script:

```bash
cd backend
python test_ingestion_api.py
```

Or test manually with curl:

```bash
# Create KB
curl -X POST http://localhost:8000/api/ingestion/kb/create \
  -H "Content-Type: application/json" \
  -d '{
    "kb_id": "test-kb",
    "name": "Test Knowledge Base",
    "source_type": "web_generic",
    "source_config": {
      "urls": ["https://example.com"],
      "follow_links": false
    }
  }'

# Start ingestion
curl -X POST http://localhost:8000/api/ingestion/kb/test-kb/start

# Check status
curl http://localhost:8000/api/ingestion/kb/test-kb/status

# List jobs
curl http://localhost:8000/api/ingestion/jobs

# Cancel job
curl -X POST http://localhost:8000/api/ingestion/kb/test-kb/cancel
```

---

## Integration with Frontend

### React Hook Example

```typescript
// hooks/useIngestionJob.ts
import { useState, useEffect } from 'react';

export function useIngestionJob(kbId: string) {
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch(`/api/ingestion/kb/${kbId}/status`);
        const data = await res.json();
        setJob(data);
        setLoading(false);
      } catch (err) {
        setError(err);
        setLoading(false);
      }
    };
    
    // Poll every 2 seconds if job is running
    const interval = setInterval(fetchStatus, 2000);
    fetchStatus();
    
    return () => clearInterval(interval);
  }, [kbId]);
  
  return { job, loading, error };
}
```

### Component Example

```typescript
// components/IngestionProgress.tsx
function IngestionProgress({ kbId }: { kbId: string }) {
  const { job, loading, error } = useIngestionJob(kbId);
  
  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  
  return (
    <div>
      <h3>{job.phase}</h3>
      <ProgressBar value={job.progress} max={100} />
      <p>{job.message}</p>
      <pre>{JSON.stringify(job.metrics, null, 2)}</pre>
    </div>
  );
}
```
