# WAF Query System - Complete Guide

## Table of Contents
1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Two-Phase Ingestion](#two-phase-ingestion)
4. [API Reference](#api-reference)
5. [Architecture](#architecture)
6. [Customization](#customization)
7. [Performance](#performance)
8. [Troubleshooting](#troubleshooting)
9. [File Structure](#file-structure)

---

## Overview

The WAF Query System is a RAG (Retrieval-Augmented Generation) system that enables natural language querying of Azure Well-Architected Framework documentation. It provides accurate, source-grounded answers backed by official Microsoft documentation.

### Key Features
- **Source-Grounded Answers**: Every answer includes citations with relevance scores
- **Two-Phase Ingestion**: Manual document validation before indexing
- **Follow-up Suggestions**: Helps users explore related topics
- **Progress Tracking**: Real-time ingestion status monitoring
- **API-Driven**: Full REST API for headless operation
- **Local-First**: No external databases required

### Technical Stack
| Layer | Technology |
|-------|-----------|
| Crawling | Python requests + BeautifulSoup |
| Content Extraction | readability-lxml |
| Embeddings | OpenAI text-embedding-3-small |
| Vector Store | LlamaIndex Local Storage |
| Generation | OpenAI gpt-4o-mini |
| Backend API | Express + TypeScript |
| Frontend | React + TypeScript + Tailwind |

---

## Quick Start

### Prerequisites
- Node.js 18+
- Python 3.9+
- OpenAI API key

### 1. Install Dependencies

```bash
# Node.js dependencies
npm run install:all

# Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create `backend/.env`:
```bash
OPENAI_API_KEY=your-key-here
PORT=3000
```

### 3. Run Ingestion (One-Time, ~20 minutes)

**Option A: Full auto-approval (quick)**
```bash
python run_waf_ingestion.py
```

**Option B: With manual validation (recommended)**
```bash
# Phase 1: Crawl and clean
python run_waf_phase1.py

# Review cleaned_documents/ and edit validation_manifest.json

# Phase 2: Build index
python run_waf_phase2.py
```

### 4. Start the Application

Terminal 1 (Backend):
```bash
cd backend
npm run dev
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

### 5. Use the System

1. Open http://localhost:5173
2. Click "WAF Query" tab
3. Ask questions like:
   - "What are the security best practices for Azure Storage?"
   - "How do I design a highly available architecture?"
   - "What are the cost optimization recommendations?"

---

## Two-Phase Ingestion

The system implements a two-phase workflow for quality control and cost optimization.

### Phase 1: Document Cleaning & Export

**Purpose**: Crawl, clean, and export documents for manual review

**Script**: `run_waf_phase1.py`

**What it does**:
1. Crawls WAF documentation (BFS, max depth 3, max 500 pages)
2. Extracts main content using readability-lxml
3. Cleans HTML and converts to Markdown
4. Exports cleaned documents to `cleaned_documents/`
5. Creates `validation_manifest.json` with status: `PENDING_REVIEW`

**Output**:
```
cleaned_documents/
├── doc_0001.md
├── doc_0002.md
└── ...
validation_manifest.json
```

### Phase 2: Chunking, Embeddings, Indexing

**Purpose**: Build vector index from approved documents only

**Script**: `run_waf_phase2.py`

**What it does**:
1. Loads `validation_manifest.json`
2. Filters documents with status: `APPROVED`
3. Chunks documents (800 tokens, 120 overlap)
4. Generates embeddings (text-embedding-3-small)
5. Builds vector index in `data/knowledge_bases/waf/index/`

**Output**:
```
data/knowledge_bases/waf/
└── index/
    ├── docstore.json
    ├── index_store.json
    └── vector_store.json
```

### Validation Manifest Format

```json
[
  {
    "document_id": "doc_0001",
    "url": "https://learn.microsoft.com/azure/well-architected/...",
    "title": "Azure Well-Architected Framework pillars",
    "section": "pillar",
    "file_path": "cleaned_documents/doc_0001.md",
    "char_count": 5234,
    "status": "PENDING_REVIEW"
  }
]
```

**Status Values**:
- `PENDING_REVIEW` - Default after Phase 1
- `APPROVED` - Include in index
- `REJECTED` - Exclude from index

### Validation Workflows

#### Workflow 1: Manual Validation (Recommended)
```bash
# Phase 1
python run_waf_phase1.py

# Review documents manually
# Edit validation_manifest.json - change status to APPROVED/REJECTED

# Phase 2
python run_waf_phase2.py
```

#### Workflow 2: Auto-Approve (Testing)
```bash
# Phase 1
python run_waf_phase1.py

# Auto-approve all
python auto_approve_docs.py

# Phase 2
python run_waf_phase2.py
```

#### Workflow 3: Via API
```bash
# Phase 1
curl -X POST http://localhost:3000/api/waf/ingest/phase1

# Manual validation

# Phase 2
curl -X POST http://localhost:3000/api/waf/ingest/phase2
```

---

## API Reference

### Query Endpoint

**POST** `/api/waf/query`

Query the WAF documentation with a natural language question.

**Request**:
```json
{
  "question": "What are the five pillars of the Well-Architected Framework?",
  "topK": 5
}
```

**Response**:
```json
{
  "answer": "The Azure Well-Architected Framework is built on five pillars: Reliability, Security, Cost Optimization, Operational Excellence, and Performance Efficiency...",
  "sources": [
    {
      "url": "https://learn.microsoft.com/azure/well-architected/pillars",
      "title": "Azure Well-Architected Framework pillars",
      "section": "pillar",
      "score": 0.92
    }
  ],
  "hasResults": true,
  "suggestedFollowUps": [
    "Tell me more about the reliability pillar",
    "What are the security best practices?"
  ]
}
```

### Ingestion Endpoints

**POST** `/api/waf/ingest/phase1`
- Start Phase 1 (crawl and clean)
- Returns: `{ message: "Phase 1 ingestion started" }`

**POST** `/api/waf/ingest/phase2`
- Start Phase 2 (build index from approved docs)
- Returns: `{ message: "Phase 2 ingestion started" }`

**POST** `/api/waf/ingest`
- Full pipeline with auto-approval (legacy)
- Returns: `{ message: "Ingestion started" }`

### Status Endpoints

**GET** `/api/waf/status`
- Check ingestion progress
- Returns: `{ running: boolean, stage?: string, progress?: number }`

**GET** `/api/waf/ready`
- Check if index is available
- Returns: `{ ready: boolean }`

---

## Architecture

### Data Flow

```
1. Ingestion (Offline, 15-30 min)
   ├── Crawler discovers URLs (500 pages)
   ├── Ingestion extracts & cleans content
   ├── Export for validation (Phase 1)
   ├── Manual review and approval
   ├── Chunker splits into 800-token pieces (Phase 2)
   └── Indexer generates embeddings & builds index

2. Query (Online, 1-3 sec)
   ├── User asks question via UI
   ├── Frontend → Backend /api/waf/query
   ├── Backend → Python query service
   ├── Semantic search retrieves top-K chunks
   ├── LLM generates answer from context
   └── Response with sources and follow-ups
```

### Component Overview

```
User Question
    ↓
Frontend (React)
    ↓
Backend (TypeScript) → WAFService
    ↓
Python Query Service (stdin/stdout)
    ↓
Vector Index (LlamaIndex) ← Embeddings (OpenAI)
    ↓
Retrieved Chunks
    ↓
LLM (gpt-4o-mini) → Answer + Sources
```

### Python Modules

| Module | Purpose |
|--------|---------|
| `crawler.py` | BFS web crawler with deduplication |
| `cleaner.py` | HTML extraction and cleaning |
| `indexer.py` | Vector index building |
| `query.py` | Query service with retrieval and generation |
| `query_service.py` | Long-running query service |
| `query_wrapper.py` | JSON stdin/stdout wrapper |
| `query_stream_wrapper.py` | Streaming response wrapper |

### TypeScript Services

| Service | Purpose |
|---------|---------|
| `WAFService.ts` | Python process management and query orchestration |
| `waf.ts` (API) | REST endpoints for queries and ingestion |

---

## Customization

### Adjust Retrieval Parameters

Edit `backend/src/services/WAFService.ts`:
```typescript
const result = await this.query({
  question,
  topK: 10,  // Retrieve more chunks (default: 5)
  metadataFilters: {
    section: 'security'  // Filter by section
  }
});
```

### Change Chunk Size

Edit `backend/src/rag/indexer.py`:
```python
builder = WAFIndexBuilder(
    chunk_size=1000,      # Default: 800 tokens
    chunk_overlap=150,    # Default: 120 tokens
    storage_dir="..."
)
```

### Use Different Models

**Embedding Model** - Edit `backend/src/rag/indexer.py` and `query.py`:
```python
WAFQueryService(
    embedding_model="text-embedding-3-large"  # Default: text-embedding-3-small
)
```

**Generation Model** - Edit `backend/src/rag/query.py`:
```python
WAFQueryService(
    llm_model="gpt-4o"  # Default: gpt-4o-mini
)
```

### Adjust Similarity Threshold

Edit `backend/src/rag/query.py`:
```python
service = WAFQueryService(
    similarity_threshold=0.7  # Default: 0.5 (lower = more results)
)
```

### Crawler Configuration

Edit `backend/src/rag/crawler.py`:
```python
crawler = WAFCrawler(
    start_url="https://learn.microsoft.com/azure/well-architected/",
    max_depth=4,      # Default: 3
    max_pages=1000,   # Default: 500
    delay=1.0         # Default: 0.5 seconds
)
```

---

## Performance

### Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Ingestion Time | 15-30 min | Depends on network and API rate limits |
| Index Size | ~200 MB | Vector embeddings and metadata |
| First Query | 5-10 sec | Includes index loading time |
| Subsequent Queries | 1-3 sec | Index cached in memory |
| Embedding Cost | $2-5 USD | Full ingestion (~275 documents) |
| Query Cost | $0.01 USD | Per query with gpt-4o-mini |
| Memory Usage | ~500 MB | Python process with loaded index |
| Disk Space | ~300 MB | Cleaned docs + index |

### Optimization Tips

1. **First Query is Slow**: Normal - index loads into memory
2. **Use Index Caching**: Keep Python service running between queries
3. **Reduce Chunk Size**: Faster retrieval but less context
4. **Lower topK**: Fewer chunks = faster generation
5. **Use Smaller Models**: gpt-4o-mini vs gpt-4o for cost/speed
6. **Batch Ingestion**: Run during off-hours to avoid rate limits

### Cost Breakdown

**Ingestion (One-Time)**:
- Crawling: Free
- Embeddings: ~$2-5 (275 docs × ~2000 tokens each)
- Total: ~$2-5 USD

**Queries (Ongoing)**:
- Retrieval: Free (local vector search)
- Generation: ~$0.01 per query (gpt-4o-mini)
- Monthly (1000 queries): ~$10 USD

---

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| "Index not found" | Ingestion not run | Run `python run_waf_ingestion.py` |
| "OPENAI_API_KEY not found" | Missing env variable | Set in `backend/.env` |
| First query very slow | Index loading | Normal - subsequent queries faster |
| Port 3000 in use | Port conflict | Change PORT in `backend/.env` |
| Python not found | Python path issue | Set PYTHON_PATH in `backend/.env` |
| Import errors | Missing dependencies | Run `pip install -r requirements.txt` |
| Empty results | Threshold too high | Lower similarity_threshold in query.py |
| Out of memory | Index too large | Reduce max_pages in crawler |
| API rate limit | Too many requests | Add delays or use batch processing |

### Common Tasks

**Re-run Ingestion**:
```bash
rm -rf data/knowledge_bases/waf/index
rm -rf cleaned_documents validation_manifest.json
python run_waf_ingestion.py
```

**Test Query from CLI**:
```bash
cd backend/src/rag
python -c "from query import WAFQueryService; service = WAFQueryService(); result = service.query('What are the five pillars?'); print(result['answer'])"
```

**Check Index Status**:
```bash
curl http://localhost:3000/api/waf/ready
```

**View Logs**:
```bash
# Backend logs
cd backend && npm run dev

# Frontend logs  
cd frontend && npm run dev

# Python logs output to stderr (visible in backend terminal)
```

---

## File Structure

```
Azure-Architect-Assistant/
├── run_waf_phase1.py              # Phase 1 runner
├── run_waf_phase2.py              # Phase 2 runner
├── run_waf_ingestion.py           # Full pipeline (auto-approve)
├── auto_approve_docs.py           # Auto-approval helper
├── validation_manifest.json       # Document validation state (generated)
├── cleaned_documents/             # Cleaned markdown files (generated)
│   ├── doc_0001.md
│   └── ...
├── data/
│   └── knowledge_bases/
│       └── waf/
│           ├── documents/         # Processed documents (generated)
│           └── index/             # Vector index (generated)
│               ├── docstore.json
│               ├── index_store.json
│               └── vector_store.json
├── backend/
│   ├── .env                       # Environment config
│   ├── src/
│   │   ├── rag/                   # Python RAG modules
│   │   │   ├── crawler.py
│   │   │   ├── cleaner.py
│   │   │   ├── indexer.py
│   │   │   ├── query.py
│   │   │   ├── query_service.py
│   │   │   ├── query_wrapper.py
│   │   │   └── query_stream_wrapper.py
│   │   ├── services/
│   │   │   └── WAFService.ts     # TypeScript service
│   │   └── api/
│   │       └── waf.ts            # REST API endpoints
│   └── package.json
├── frontend/
│   ├── src/
│   │   ├── App.tsx               # Main app with navigation
│   │   └── WAFQueryInterface.tsx # WAF query UI component
│   └── package.json
├── docs/
│   └── WAF_GUIDE.md              # This file
└── requirements.txt               # Python dependencies
```

### Generated Files (can be deleted)

These files are generated during ingestion and can be safely deleted:
- `cleaned_documents/` - Cleaned markdown files
- `validation_manifest.json` - Document validation state
- `data/knowledge_bases/waf/index/` - Vector index
- `data/knowledge_bases/waf/documents/` - Processed documents

To regenerate, simply re-run ingestion.

---

## Next Steps

1. ✅ **Complete Setup**: Follow Quick Start guide
2. **Run Ingestion**: Generate the index with your chosen workflow
3. **Test Queries**: Try different question types
4. **Explore Customization**: Adjust parameters for your needs
5. **Review Performance**: Monitor costs and response times
6. **Validate Documents**: Review cleaned documents for quality
7. **Extend System**: Add more documentation sources
8. **Integrate**: Connect with your architecture projects

---

**Last Updated**: November 24, 2025
**Version**: 1.0.0
**Status**: Production Ready
