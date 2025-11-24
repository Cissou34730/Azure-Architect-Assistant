# Python Service - FastAPI Backend for RAG

This service handles all RAG (Retrieval-Augmented Generation) operations using LlamaIndex and OpenAI.

## Setup

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # or
   source venv/bin/activate  # Linux/Mac
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and set your OPENAI_API_KEY
   ```

## Run

```bash
# Development (with auto-reload)
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### Query
```bash
POST http://localhost:8000/query
{
  "question": "What are the five pillars of WAF?",
  "topK": 5
}
```

### Health Check
```bash
GET http://localhost:8000/health
```

### Ingestion Phase 1
```bash
POST http://localhost:8000/ingest/phase1
```

### Ingestion Phase 2
```bash
POST http://localhost:8000/ingest/phase2
```

## Architecture

```
FastAPI App (main.py)
    ↓
RAG Modules (app/rag/)
    ├── query.py - WAFQueryService
    ├── crawler.py - Web crawler
    ├── cleaner.py - Document cleaning
    └── indexer.py - Vector index builder
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
