# Python Service - FastAPI Backend for RAG

This service handles all RAG (Retrieval-Augmented Generation) operations using LlamaIndex and OpenAI.

## Features

✅ **Multi-Source Knowledge Base Support** - Query multiple KBs with profile-based selection  
✅ **Startup Preloading** - Indices load into memory at startup for instant queries  
✅ **Modular Router Architecture** - Clean separation of query, KB management, and ingestion  
✅ **Generic KB Service** - Easily add new knowledge bases beyond WAF  

## Setup

1. **Create virtual environment** (from project root):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or
   source .venv/bin/activate  # Linux/Mac
   ```

2. **Install dependencies**:
   ```bash
   cd python-service
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   - The service uses the shared `.env` file in the project root
   - Ensure `OPENAI_API_KEY` is set

## Run

### From Project Root (Recommended)
```bash
npm run dev:python
# or start all services
npm run dev
```

### Direct Uvicorn
```bash
cd python-service
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

### Query Endpoints

#### Chat Query (Fast Profile)
```bash
POST http://localhost:8000/query/chat
{
  "question": "What security layers should we implement?",
  "project_id": "abc123"
}
```

#### Proposal Query (Comprehensive Profile)
```bash
POST http://localhost:8000/query/proposal
{
  "question": "Design a secure architecture",
  "project_id": "abc123"
}
```

#### Legacy Query (Backward Compatible)
```bash
POST http://localhost:8000/query
{
  "question": "What are the five pillars of WAF?",
  "topK": 5
}
```

### Knowledge Base Management

#### List Knowledge Bases
```bash
GET http://localhost:8000/kb/list
```

#### KB Health Check
```bash
GET http://localhost:8000/kb/health
```

### Ingestion (Legacy WAF)

#### Phase 1: Crawl and Clean
```bash
POST http://localhost:8000/ingest/phase1
```

#### Phase 2: Build Index
```bash
POST http://localhost:8000/ingest/phase2
```

### Health Check
```bash
GET http://localhost:8000/health
```

## Architecture

```
FastAPI App (app/main.py)
    ├── @startup event - Preloads all services
    ├── Routers (app/routers/)
    │   ├── query.py - Query endpoints (chat, proposal, legacy)
    │   ├── kb.py - KB management endpoints
    │   └── ingest.py - Document ingestion endpoints
    ├── Services (app/services.py)
    │   ├── get_query_service() - Legacy WAF service
    │   ├── get_kb_manager() - KB configuration manager
    │   └── get_multi_query_service() - Multi-source query service
    └── RAG Modules (app/rag/)
        ├── kb_query.py - Generic KnowledgeBaseQueryService
        ├── crawler.py - Web crawler
        ├── cleaner.py - Document cleaning
        └── indexer.py - Vector index builder
```

## Startup Sequence

1. **Uvicorn starts** - Loads FastAPI app
2. **Startup event fires** - Preloads services
3. **WAF Query Service** - Loads index into RAM (~5-10s)
4. **KB Manager** - Loads configurations
5. **Multi-Source Service** - Ready for queries
6. **Server ready** - First query is instant! ⚡

## Service Singleton Pattern

Services use singleton pattern with startup preloading:

```python
# services.py
_query_service: Optional[WAFQueryService] = None

def get_query_service() -> WAFQueryService:
    global _query_service
    if _query_service is None:
        _query_service = WAFQueryService(...)  # Preloads index
    return _query_service
```

Benefits:
- Index loads once at startup
- Subsequent requests are instant
- Memory efficient (single index instance)

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
