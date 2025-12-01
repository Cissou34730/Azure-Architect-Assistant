Here is the comprehensive technical specification document. You can copy the content below and save it as `IngestionNewSpec.md`.

-----

````markdown
# Technical Specification: Resilient RAG Ingestion Engine

**Version:** 1.0
**Date:** 2025-11-23
**Status:** Draft

## 1. Executive Summary

This document defines the architecture for a background ingestion system designed to process Web, PDF, Markdown, and YouTube data into a Vector Knowledge Base (RAG). 

The system prioritizes **reliability** and **resumability**. It employs a **Staged Producer-Consumer Architecture** to decouple fast extraction processes (crawling, parsing) from slower embedding processes (API calls). This ensures zero data loss during crashes and allows for granular Pause/Resume/Cancel operations.

## 2. System Architecture

### 2.1 High-Level Design
The backend (FastAPI) spawns a **Singleton Ingestion Manager** which orchestrates two decoupled background threads per job. State is persisted in a relational database (SQLite/PostgreSQL) acting as a priority queue.

```mermaid
graph LR
    User[Frontend] -- HTTP --> API[FastAPI Backend]
    API -- Controls --> Manager[Ingestion Manager]
    Manager -- Spawns --> Producer[Thread 1: Producer]
    Manager -- Spawns --> Consumer[Thread 2: Consumer]
    
    subgraph "Stage 1: Extraction"
    Producer -- Crawl/Parse --> RawData
    RawData -- Hash & Chunk --> Queue[(DB Queue)]
    end
    
    subgraph "Stage 2: Embedding"
    Queue -- Poll Pending --> Consumer
    Consumer -- OpenAI API --> Embeddings
    Embeddings --> VectorStore[LlamaIndex Vector Store]
    end
````

### 2.2 Core Components

1.  **Ingestion Manager (Singleton):**

      * Manages lifecycle of threads.
      * Handles `threading.Event` flags (`stop_event`, `pause_event`).
      * **Crash Recovery:** On startup, resets any `PROCESSING` items in the Queue back to `PENDING`.

2.  **The Producer (Extraction Thread):**

      * **Role:** Extract text, clean, chunk, and hash.
      * **Behavior:** Fast, CPU-bound.
      * **Output:** Writes normalized chunks to the `IngestionQueue` table.

3.  **The Consumer (Embedding Thread):**

      * **Role:** Generate embeddings and index.
      * **Behavior:** Slow, I/O-bound (API latency).
      * **Input:** Reads `PENDING` items from `IngestionQueue`.
      * **Output:** Updates Vector Database.

-----

## 3\. Data Model (Persistence)

### 3.1 Table: `ingestion_jobs`

Tracks the high-level lifecycle of a user request.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Unique Job ID. |
| `status` | ENUM | `PENDING`, `RUNNING`, `PAUSED`, `COMPLETED`, `FAILED`, `CANCELED`. |
| `source_type` | ENUM | `WEB`, `PDF`, `MARKDOWN`, `YOUTUBE`. |
| `source_config` | JSON | Configuration (Target URLs, file paths, recursion depth). |
| `created_at` | DATETIME | Timestamp. |
| `total_items` | INT | Estimated total items (updated by Producer). |
| `processed_items`| INT | Items successfully indexed (updated by Consumer). |

### 3.2 Table: `ingestion_queue`

Acts as the buffer and granular checkpoint.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | INT (PK) | Auto-increment ID. |
| `job_id` | UUID (FK) | Reference to `ingestion_jobs`. |
| `doc_hash` | VARCHAR | SHA256(content + metadata). **Unique Constraint** for deduplication. |
| `content` | TEXT | The actual text chunk. |
| `metadata` | JSON | Origin info (URL, page number, timestamp). |
| `status` | ENUM | `PENDING`, `PROCESSING`, `DONE`, `ERROR`. |
| `attempts` | INT | Retry counter (for robustness). |
| `error_log` | TEXT | Stack trace if failed. |

-----

## 4\. Functional Specifications

### 4.1 Ingestion Sources

  * **Web:** \* **Tool:** `BeautifulSoup4` + `requests`.
      * **Logic:** Non-recursive (or single-depth) fetch. Parse specific DOM elements (e.g., `<article>`, `<main>`) to exclude navbars/footers.
      * **Tracking:** One-time crawl. No periodic monitoring.
  * **PDF:** `LlamaIndex` (`PDFReader`).
  * **Markdown:** `LlamaIndex` (`UnstructuredMarkdownReader` or native).
  * **YouTube:** \* **Tool:** `youtube_transcript_api`.
      * **Robustness:** Must handle timeouts for long videos (retry logic in Producer).

### 4.2 Text Processing (Producer)

  * **Cleaning:** Remove excessive whitespace, HTML tags.
  * **Chunking:** `SentenceSplitter` (Target: 512 or 1024 tokens).
  * **Hashing:** Calculate SHA256 of the chunk text. If `doc_hash` exists in DB, skip (Deduplication).

### 4.3 Vectorization (Consumer)

  * **Model:** OpenAI `text-embedding-3-small`.
  * **Store:** `SimpleVectorStore` (initially) with `StorageContext` abstraction for easy swap to Qdrant/PGVector.
  * **Logic:** 1. Fetch batch (e.g., 10 items).
    2\. Embed.
    3\. Insert into Index.
    4\. Commit DB transaction (`status='DONE'`).

### 4.4 Control Flow

  * **Pause:**
      * API sets `pause_event`.
      * Threads check event before processing next item.
      * State in DB updates to `PAUSED`.
  * **Resume:**
      * API clears `pause_event`.
      * Threads resume loop.
  * **Cancel/Delete:**
      * **Soft Stop:** Threads stop processing.
      * **Cleanup:** 1. Delete rows from `ingestion_queue`.
        2\. Delete row from `ingestion_jobs`.
        3\. **Vector Cleanup:** Iterate over processed `doc_hash` IDs for this job and remove corresponding nodes from the `VectorStore`.

-----

## 5\. Technical Stack

  * **Language:** Python 3.10+
  * **Framework:** FastAPI
  * **Database:** SQLite (dev) / PostgreSQL (prod) via SQLAlchemy (Async not strictly required for background threads, sync is safer for `threading`).
  * **RAG Framework:** LlamaIndex v0.10+
      * `llama-index-core`
      * `llama-index-readers-web`
      * `llama-index-readers-file`
      * `llama-index-readers-youtube-transcript`
      * `llama-index-embeddings-openai`

## 6\. Implementation Guidelines

### 6.1 Crash Recovery Logic

On application startup (`lifespan` event in FastAPI):

```python
def recover_state():
    # Reset items that were mid-flight when the server crashed
    db.execute("UPDATE ingestion_queue SET status='PENDING' WHERE status='PROCESSING'")
    # Reset jobs that thought they were running
    db.execute("UPDATE ingestion_jobs SET status='PAUSED' WHERE status='RUNNING'")
```

### 6.2 Deletion Logic (Vector Store)

Since `SimpleVectorStore` does not support complex filtering, we rely on `ref_doc_id` or metadata filtering.

  * **Requirement:** When creating LlamaIndex `Document` objects in the Consumer, set `doc.id_` to the `ingestion_queue.doc_hash`.
  * **Deletion:** \`\`\`python
    # Pseudo-code
    ids\_to\_delete = db.query(IngestionQueue.doc\_hash).filter\_by(job\_id=job\_id).all()
    vector\_index.delete\_nodes(ids\_to\_delete)
    ```
    
    ```

### 6.3 Thread Safety

  * Use `threading.Lock()` if multiple threads access the same `SimpleVectorStore` instance in memory (though the architecture suggests one Consumer per job, if multiple jobs run globally, lock the Index write).

<!-- end list -->

```
```