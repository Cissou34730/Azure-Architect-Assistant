# Azure Architecture Assistant - POC

This is a proof-of-concept application that helps Azure Solution Architects analyze project documents, clarify requirements through interactive chat, generate high-level Azure architecture proposals, and query the Azure Well-Architected Framework (WAF) documentation.

## Features

### Architecture Project Management
1. **Project Management**: Create and manage multiple architecture projects with automatic SQLite persistence
2. **Document Upload**: Upload RFP, specifications, and other project documents (supports plain text, with placeholders for PDF/DOCX)
3. **Document Analysis**: AI-powered analysis to extract project context, requirements, and constraints
4. **Interactive Chat with KB Integration**: Ask questions and get answers enriched with knowledge base best practices and source citations
5. **Architecture Sheet**: Structured view of project requirements, NFRs, constraints, and open questions
6. **Architecture Proposal with KB Guidance**: Generate comprehensive Azure architecture proposals grounded in knowledge base documentation with cited sources
7. **Real-Time Progress Updates**: Server-Sent Events (SSE) provide live progress tracking during proposal generation

### Multi-Source RAG System (NEW)
8. **Profile-Based Querying**: Automatic query optimization based on context (chat vs proposal)
9. **Multiple Knowledge Bases**: Support for WAF, Azure Services, and custom documentation sources
10. **Parallel Multi-KB Queries**: Query multiple knowledge bases simultaneously for comprehensive results
11. **Source Attribution**: All results tagged with source KB (e.g., `[WAF]`, `[Azure Services]`)
12. **KB Management API**: List, health check, and manage knowledge bases via REST API
13. **Vector Search**: Fast semantic search using OpenAI embeddings with global index caching
14. **Two Query Profiles**:
    - **CHAT**: Fast, targeted (3 results/KB) for interactive conversations
    - **PROPOSAL**: Comprehensive (5 results/KB) for architecture proposals

### Legacy WAF Support
15. **Standalone WAF Query**: Dedicated interface to query Azure Well-Architected Framework documentation
16. **Two-Phase Ingestion Pipeline**: Separate crawling/cleaning and indexing phases with document validation workflow
17. **Source Citations**: All responses include clickable links to Microsoft Learn documentation

## Architecture

### Microservices Architecture

- **Express Backend** (TypeScript): Main API gateway on port 3000
  - REST API endpoints for projects, documents, chat
  - OpenAI integration for document analysis and proposal generation
  - HTTP client for Python RAG service
  - KB management endpoints (`/kb/list`, `/kb/health`)
  
- **Python FastAPI Service**: Multi-source RAG service on port 8000
  - **Startup Preloading**: Indices load into memory at startup for instant first queries
  - Profile-based query endpoints (`/query/chat`, `/query/proposal`)
  - KB management endpoints (`/kb/list`, `/kb/health`)
  - LlamaIndex 0.12.x for vector search and RAG
  - Singleton service pattern with in-memory index caching
  - Parallel multi-KB query support
  - **Routers**: Clean separation (query, kb, ingest)
  
- **Frontend**: React + Vite with Tailwind CSS on port 5173
  - **Refactored Components**: ProjectList, ChatPanel, StatePanel, ProposalPanel, DocumentsPanel
  - **Custom Hooks**: useProjects, useProjectState, useChat, useProposal
  - **API Service Layer**: Centralized HTTP client
  
- **Storage**: SQLite database with automatic persistence (`data/projects.db`)

### New Service Architecture (TypeScript)

```
Frontend (React)
    ├── Components (UI)
    │   ├── ProjectList.tsx
    │   ├── ChatPanel.tsx
    │   ├── StatePanel.tsx
    │   ├── ProposalPanel.tsx
    │   └── DocumentsPanel.tsx
    ├── Hooks (State Management)
    │   ├── useProjects.ts
    │   ├── useProjectState.ts
    │   ├── useChat.ts
    │   └── useProposal.ts
    └── Services (API Layer)
        └── apiService.ts
             ↓
Express Backend (TypeScript)
    ├── Routes: projects.ts
    ├── Services
    │   ├── LLMService (Orchestration)
    │   ├── RAGService (High-level RAG)
    │   └── KBService (HTTP Client)
    ↓
Python FastAPI Service
    ├── @startup event → Preloads services
    ├── Routers
    │   ├── query.py (chat, proposal, legacy)
    │   ├── kb.py (list, health)
    │   └── ingest.py (phase1, phase2)
    ├── Services (services.py)
    │   ├── get_query_service() → WAFQueryService
    │   ├── get_kb_manager() → KBManager
    │   └── get_multi_query_service() → MultiSourceQueryService
    └── RAG Modules
        ├── kb_query.py → KnowledgeBaseQueryService (Generic)
        └── kb/ → Multi-source management
             ↓
LlamaIndex + OpenAI
```

### Legacy Support
- `WAFService.ts` functionality migrated to `KBService.ts`
- Backward compatibility via export alias: `wafService = kbService`
- Old `/query` endpoint redirects to `/query/chat`

### AI & RAG Pipeline

- **Main AI (TypeScript → OpenAI)**:
  - Document analysis: Extract project requirements
  - Conversation processing: Refine architecture based on chat
  - Proposal generation: Create comprehensive architecture documents
  - Model: `gpt-4o-mini`
  
- **Multi-Source RAG System (Python → LlamaIndex → OpenAI)**:
  - **Startup**: Indices preload at server start (~5-10s once)
  - **Embeddings**: `text-embedding-3-small` (1536 dimensions)
  - **Generation**: `gpt-4o-mini` for answer synthesis
  - **Vector Store**: File-based persistent storage (~60MB per KB)
  - **Performance**: 
    - First query: Instant (preloaded at startup!)
    - Subsequent queries: ~2-3s (retrieval + generation)
  - **Query Profiles**:
    - `CHAT`: 3 results per KB, fast responses for interactive chat
    - `PROPOSAL`: 5 results per KB, comprehensive for architecture proposals
  - **Query Flow**: Question → Embedding → Multi-KB vector search (parallel) → Context retrieval → Answer generation
  - **Singleton Pattern**: Services initialized once, reused across all requests
  
- **Integration Pattern**:
  - TypeScript calls Python via HTTP (`POST /query/chat` or `/query/proposal`)
  - Automatic profile selection based on context
  - Parallel multi-KB queries for comprehensive results
  - Source citations with KB attribution
  
- **Cost per Operation**:
  - **Chat with RAG**: 1 embedding + 2 generation calls (~$0.001)
  - **Proposal with RAG**: 5 embeddings + 6 generation calls (~$0.005)
  - Scales linearly with number of active knowledge bases

## Prerequisites

- Node.js 18+ and npm
- Python 3.10+ (for WAF functionality)
- OpenAI API key or Azure OpenAI credentials

## Setup

### 1. Clone and Install Dependencies

```bash
# Install all dependencies (backend + frontend + Python)
npm run install:all

# OR install individually

# Install workspace dependencies
npm install

# Install backend dependencies
cd backend
npm install

# Install frontend dependencies
cd frontend
npm install

# Install Python dependencies in virtual environment
cd ..
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate  # Linux/Mac
cd python-service
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the **project root** (shared by all services):

```bash
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini

# Service Ports
EXPRESS_PORT=3000
PYTHON_PORT=8000
PYTHON_SERVICE_URL=http://localhost:8000

# Logging
LOG_LEVEL=info

# OR for Azure OpenAI
AZURE_OPENAI_API_KEY=your-azure-openai-key
OPENAI_API_ENDPOINT=https://your-resource.openai.azure.com/openai/deployments/your-deployment/chat/completions?api-version=2024-02-15-preview
```

### 3. Run the Application

**Option 1 - Run All Services (Recommended):**

```bash
npm run dev
```

This starts all three services concurrently:
- Python FastAPI service on `http://localhost:8000`
- Express backend on `http://localhost:3000`
- React frontend on `http://localhost:5173`

**Option 2 - Run Services Individually:**

**Terminal 1 - Python Service:**

```bash
npm run dev:python
```

Python FastAPI service runs on `http://localhost:8000`

**Terminal 2 - Express Backend:**

```bash
npm run dev:backend
# OR
cd backend
npm run dev
```

Backend runs on `http://localhost:3000`

**Terminal 3 - React Frontend:**

```bash
npm run dev:frontend
# OR
cd frontend
npm run dev
```

Frontend runs on `http://localhost:5173`

## Usage Workflow

1. **Create a Project**
   - Enter a project name in the left sidebar
   - Click "Create Project"

2. **Upload Documents**
   - Select the project
   - Go to the "Documents" tab
   - Upload project files (RFP, specifications, etc.)
   - Click "Analyze Documents" to generate the initial Architecture Sheet

3. **Review Architecture Sheet**
   - Go to the "State" tab to see the extracted information:
     - Context & Objectives
     - Non-Functional Requirements (NFRs)
     - Application Structure
     - Data & Compliance
     - Technical Constraints
     - Open Questions

4. **Clarify Requirements with WAF Guidance**
   - Go to the "Chat" tab
   - Ask questions about Azure services, architecture, or best practices
   - **Automatic WAF Integration**: Azure-related questions trigger WAF queries
   - View AI responses with cited sources from Microsoft Learn documentation
   - The Architecture Sheet updates automatically based on the conversation

5. **Generate Architecture Proposal with WAF Best Practices**
   - Go to the "Proposal" tab
   - Click "Generate Proposal" (takes ~40 seconds)
   - **Automatic WAF Integration**: System queries all 5 WAF pillars (Security, Reliability, Cost, Performance, Operations)
   - Review comprehensive proposal with [1], [2], [3] citations
   - Click source links to read original WAF documentation

## WAF Query System

### Overview

The WAF Query System provides intelligent, source-grounded answers to questions about the Azure Well-Architected Framework. It uses a two-phase RAG (Retrieval-Augmented Generation) pipeline with document validation and a long-running service architecture for fast query responses.

### Architecture

#### Phase 1: Ingestion & Validation
Separate crawling/cleaning from indexing to allow manual document review:

1. **Crawler** (`backend/src/rag/crawler.py`)
   - BFS traversal of learn.microsoft.com/azure/well-architected/
   - Handles /en-us/ path prefixes automatically
   - Deduplication and graceful error handling
   - Exports URLs to `data/knowledge_bases/waf/urls.txt`

2. **Cleaner** (`backend/src/rag/cleaner.py`)
   - Three-layer cleaning: Readability → BeautifulSoup → html2text
   - Removes navigation, footers, sidebars
   - Exports cleaned markdown to `data/knowledge_bases/waf/documents/`
   - Creates validation manifest: `data/knowledge_bases/waf/manifest.json`

3. **Validation Workflow**
   - Manual review via `manifest.json` (status: PENDING → APPROVED/REJECTED)
   - Auto-approval script: `scripts/utils/approve_documents.py`
   - Only APPROVED documents proceed to Phase 2

#### Phase 2: Chunking & Indexing

4. **Indexer** (`backend/src/rag/indexer.py`)
   - Loads APPROVED documents from manifest
   - Token-based chunking (800 tokens, 120 overlap)
   - Generates embeddings via OpenAI API
   - Builds vector index at `data/knowledge_bases/waf/index/`
   - Index size: ~60MB (51MB vector store + 8.5MB docstore)

#### Query Architecture: Long-Running Service

5. **Query Service** (`backend/src/rag/query_service.py`)
   - **Persistent Python process** started on server boot
   - Pre-loads 51MB vector index into memory (~35s startup)
   - Listens for queries on stdin, responds on stdout
   - Global index caching via `_INDEX_CACHE` dictionary
   - **Performance**: First query ~35s, subsequent queries ~6s

6. **WAFService Integration** (`backend/src/services/WAFService.ts`)
   - Spawns long-running Python service in constructor
   - Maintains bidirectional stdin/stdout communication
   - Tracks service readiness via `{"status": "ready"}` signal
   - Routes queries as JSON lines, receives responses as JSON
   - Graceful shutdown on SIGINT/SIGTERM
   - Used by both standalone WAF Query interface and LLMService integration

7. **LLMService WAF Integration** (`backend/src/services/LLMService.ts`)
   - **Chat Integration**: Detects Azure keywords (azure, security, performance, etc.)
   - Queries WAF automatically for Azure-related questions (~6s per query)
   - Includes WAF context and sources in LLM prompt
   - Returns WAF sources with chat responses
   - **Proposal Integration**: Queries all 5 WAF pillars in parallel (~30s total)
   - Aggregates guidance into system prompt with source citations
   - LLM generates proposal citing [1], [2], [3] sources

### Initial Setup

#### 1. Run WAF Ingestion (Two-Phase Pipeline)

The ingestion process runs in two separate phases to allow document validation.

**Phase 1: Crawl and Clean**

```bash
# Option A: Via Python script
cd Azure-Architect-Assistant
python scripts/ingest/waf_phase1.py

# Option B: Via web interface
# Navigate to "WAF Query" tab → Click "Start Phase 1"
```

This will:
- Crawl ~275 WAF documentation pages
- Clean and convert HTML to markdown
- Create validation manifest with status: PENDING

**Document Validation (Optional)**

```bash
# Review and approve documents
# Edit data/knowledge_bases/waf/manifest.json
# Change status from PENDING to APPROVED or REJECTED

# Or auto-approve all documents
python scripts/utils/approve_documents.py
```

**Phase 2: Chunk and Index**

```bash
# Option A: Via Python script
python scripts/ingest/waf_phase2.py

# Option B: Via web interface
# Navigate to "WAF Query" tab → Click "Start Phase 2"
```

This will:
- Load APPROVED documents (skip REJECTED/PENDING)
- Create 1,556 chunks from 275 documents
- Generate embeddings (~$0.01 cost)
- Build 60MB vector index (~10-15 minutes)

**Performance Notes:**
- Phase 1: ~5-10 minutes (network dependent)
- Phase 2: ~10-15 minutes (OpenAI API dependent)
- Server startup: Loads index in ~35 seconds
- Queries: 6 seconds after initial load

#### 2. Configuration

Ensure your `.env` file includes:

```bash
# Required for WAF functionality
OPENAI_API_KEY=your-openai-api-key

# Optional: Specify Python path if using virtual environment
PYTHON_PATH=python  # or /path/to/venv/bin/python
```

### Using the WAF Query System

1. **Server Startup**
   - Backend automatically starts long-running Python query service
   - Wait for log message: `[WAFService] Query service ready` (~35 seconds)
   - Service pre-loads 51MB index into memory

2. **Ask Questions**
   - Navigate to "WAF Query" tab
   - Enter your question in natural language
   - Examples:
     - "What are the five pillars of the Well-Architected Framework?"
     - "What are the best practices for securing Azure SQL databases?"
     - "How should I design a highly available multi-region architecture?"
     - "What are the cost optimization recommendations for Azure Storage?"

3. **Review Answers**
   - First query: ~35s (includes index loading time)
   - Subsequent queries: ~6s (index cached in memory)
   - AI-generated answer with source citations
   - Relevance scores for each source
   - Click source links to view original documentation

### Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Server startup | 35s | One-time cost: loads 51MB index |
| First WAF query | 35s | If service restarts |
| Subsequent WAF queries | 6s | Index cached in memory |
| Chat with WAF (Azure question) | ~8s | 6s WAF query + 2s LLM generation |
| Chat without WAF | ~2s | Direct LLM, no WAF query |
| Architecture proposal | ~40s | 5 WAF queries (sequential) + LLM with live progress updates |
| Index loading | 27s | From disk to memory |
| Embedding generation | 3.5s | Query → embedding via API |
| LLM generation | 2-5s | Answer generation |
| Phase 1 ingestion | 5-10 min | Network dependent |
| Phase 2 ingestion | 10-15 min | OpenAI API dependent |

### Technical Specifications

| Component | Technology | Configuration |
|-----------|-----------|---------------|
| Crawler | Python requests + BeautifulSoup | 275 pages, BFS traversal |
| Text Extraction | readability-lxml + html2text | Three-layer cleaning |
| Chunking | LlamaIndex TokenTextSplitter | 800 tokens, 120 overlap |
| Embeddings | OpenAI text-embedding-3-small | 1536 dimensions |
| Vector Store | LlamaIndex File Storage | 60MB (51MB vectors + 8.5MB docs) |
| Index Caching | Python global dictionary | In-memory, persistent across queries |
| Generation | OpenAI gpt-4o-mini | Temperature: 0.1, max tokens: 1000 |
| Retrieval | Cosine similarity search | Top-3 chunks, threshold 0.5 |
| Service Architecture | Long-running Python process | stdin/stdout communication |
| Query Time | First: ~35s, After: ~6s | Index cached in memory |

### Data Structure

```
data/knowledge_bases/waf/
├── urls.txt                    # 275 crawled URLs
├── documents/                  # 275 cleaned markdown files
├── manifest.json              # Document validation status
└── index/                     # Vector store (60MB)
    ├── default__vector_store.json  # 51MB - embeddings
    ├── docstore.json              # 8.5MB - document content
    ├── index_store.json           # 130KB - index metadata
    ├── graph_store.json           # Empty
    ├── image__vector_store.json   # Empty
    └── build_info.json            # Build metadata
```

### Extending the System

The WAF ingestion pipeline is designed to scale to multiple knowledge bases:

**Current Limitations:**
- 51MB index takes ~27s to load per KB
- With 40 KBs: ~2GB RAM, ~18 min startup time
- File-based storage not optimized for production scale

**Recommended Production Architecture:**
1. **Azure AI Search**: Cloud vector database with instant queries
2. **Chroma/Qdrant**: Local vector DB with disk-based storage
3. **Multiple Services**: Run separate Python processes per KB (parallel loading)

**To Add New Knowledge Bases:**
1. Create new KB directory: `data/knowledge_bases/<kb_name>/`
2. Modify crawler for different documentation sources
3. Run Phase 1 and Phase 2 for new KB
4. Start additional query service instance
5. Route queries to appropriate service based on KB selection

## API Endpoints

### Architecture Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/projects` | Create a new project |
| GET | `/api/projects` | List all projects |
| POST | `/api/projects/:id/documents` | Upload documents |
| POST | `/api/projects/:id/analyze-docs` | Analyze documents and create Architecture Sheet |
| POST | `/api/projects/:id/chat` | Send chat message (auto-queries WAF for Azure questions), returns message, state, and WAF sources |
| GET | `/api/projects/:id/state` | Get current Architecture Sheet |
| GET | `/api/projects/:id/architecture/proposal` | Generate Azure architecture proposal with real-time progress via SSE (auto-queries 5 WAF pillars sequentially) |
| GET | `/api/projects/:id/messages` | Get conversation history with WAF sources |

### WAF Query System

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/waf/query` | Query WAF documentation (uses long-running service) |
| POST | `/api/waf/ingest/phase1` | Start Phase 1: Crawl and clean |
| POST | `/api/waf/ingest/phase2` | Start Phase 2: Chunk and index |
| POST | `/api/waf/ingest` | Legacy: Start full pipeline |
| GET | `/api/waf/status` | Get ingestion status |
| GET | `/api/waf/ready` | Check if index is ready |

#### WAF Query Request

```json
{
  "question": "What are the security best practices for Azure Storage?",
  "topK": 3
}
```

#### WAF Query Response

```json
{
  "answer": "According to the Azure Well-Architected Framework...",
  "sources": [
    {
      "url": "https://learn.microsoft.com/azure/well-architected/security/...",
      "title": "Security pillar overview",
      "section": "security",
      "score": 0.89
    }
  ],
  "scores": [0.89, 0.85, 0.82],
  "hasResults": true,
  "discussionEnabled": true,
  "suggestedFollowUps": [
    "How do I implement encryption at rest?",
    "What about network security?",
    "How does this relate to compliance requirements?"
  ]
}
```

## Data Models

### ProjectState (Architecture Sheet)

```typescript
{
  projectId: string
  context: {
    summary: string
    objectives: string[]
    targetUsers: string
    scenarioType: string
  }
  nfrs: {
    availability: string
    security: string
    performance: string
    costConstraints: string
  }
  applicationStructure: {
    components: string[]
    integrations: string[]
  }
  dataCompliance: {
    dataTypes: string[]
    complianceRequirements: string[]
    dataResidency: string
  }
  technicalConstraints: {
    constraints: string[]
    assumptions: string[]
  }
  openQuestions: string[]
  lastUpdated: string
}
```

### ConversationMessage (with WAF Sources)

```typescript
{
  id: string
  projectId: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  wafSources?: Array<{
    url: string
    title: string
    section: string
    score: number
  }>
}
```

## Limitations (POC)

### Architecture Projects
- **Local SQLite Storage**: Projects stored in `data/projects.db`; suitable for single-user but not distributed deployments
- **No Authentication**: Single-user, no access control
- **Limited Document Parsing**: Full text extraction only for plain text files; PDF/DOCX are placeholders
- **No Multi-tenancy**: Designed for single-user proof-of-concept
- **Basic Error Handling**: Minimal validation and error messages

### WAF Query System
- **Local File Storage**: 60MB vector index stored locally; not suitable for distributed deployment
- **Startup Time**: 35-second delay on server start (loading 51MB index into memory)
- **Query Performance**: ~6-8s per chat response with WAF, ~40s for full proposal generation (sequential pillar queries)
- **Keyword Detection**: Simple keyword matching for Azure-related questions (may miss context)
- **Sequential Processing**: Proposal generation queries 5 pillars sequentially to avoid overwhelming Python service (more reliable but slower than parallel)
- **Scalability**: With 40 KBs, would require ~2GB RAM and ~18 min startup time
- **No Incremental Updates**: Full re-ingestion required to update documentation
- **OpenAI Dependency**: Requires OpenAI API access; no offline mode
- **Single Knowledge Base**: Current implementation optimized for WAF only
- **Single Language**: English only; no multilingual support
- **Answer Quality**: RAG responses vary based on chunk retrieval quality (ongoing optimization)

## Future Enhancements

### Architecture Projects
- ✅ SQLite database persistence (completed)
- Cloud database migration (MongoDB, PostgreSQL, Azure SQL)
- User authentication and multi-tenancy
- Advanced document parsing (PDF, DOCX, Excel)
- Architecture diagram generation
- Export capabilities (Word, PDF)
- Version history for Architecture Sheets
- Collaborative editing
- Integration with Azure services for validation

### WAF Integration Improvements
- ✅ **Real-Time Progress Updates**: Server-Sent Events for live proposal generation tracking (completed)
- ✅ **Sequential WAF Querying**: Reliable pillar-by-pillar processing (completed)
- **Smart Context Detection**: ML-based question classification (not just keywords)
- **Improved Answer Quality**: Fine-tune retrieval parameters, re-ranking, chunk size optimization
- **Parallel Optimization**: Optimize Python service to handle concurrent WAF queries safely
- **Answer Confidence Scores**: Display reliability indicators for WAF-sourced information
- **User Feedback Loop**: Rate answers to improve retrieval quality
- **Contextual Follow-ups**: Suggest related WAF topics based on conversation

### WAF Query System
- **Production Vector Database**: Migrate to Azure AI Search, Chroma, or Qdrant for instant queries
- **Multi-KB Support**: Support 40+ knowledge bases with parallel query services
- **Incremental Updates**: Delta updates for changed documentation
- **Advanced Caching**: Redis/Memcached for query result caching
- **Streaming Responses**: Real-time answer generation for better UX
- **Conversation Memory**: Multi-turn dialogue with context retention
- **Monitoring & Analytics**: Query logs, popular questions, answer quality metrics
- **Multilingual Support**: Query and retrieve in multiple languages
- **Hybrid Search**: Combine semantic and keyword search for better recall

## Troubleshooting

### WAF Ingestion Issues

**Problem**: Python dependencies not found
```bash
# Solution: Ensure Python packages are installed
pip install -r requirements.txt

# Or use a virtual environment (recommended)
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
pip install -r requirements.txt
```

**Problem**: OPENAI_API_KEY not found
```bash
# Solution: Create .env file in project root with:
OPENAI_API_KEY=your-key-here
```

**Problem**: Ingestion timeout or failure
```bash
# Solution: Run phases individually to identify the issue
python scripts/ingest/waf_phase1.py   # Crawl and clean
python scripts/utils/approve_documents.py  # Auto-approve
python scripts/ingest/waf_phase2.py   # Chunk and index
```

**Problem**: Server not starting long-running service
```bash
# Check logs for "[WAFService] Starting long-running query service"
# Ensure query_service.py exists in backend/src/rag/
# Verify Python path is correct in backend/.env
```

### Query Issues

**Problem**: "Index not found" error
- **Solution**: Run the two-phase ingestion pipeline first (see "Initial Setup" section)

**Problem**: Low-quality answers
- **Solution**: Adjust similarity threshold (currently 0.5) in `query.py`
- **Alternative**: Review and reject low-quality documents in Phase 1

**Problem**: First query takes 35 seconds
- **Solution**: This is expected - index loads into memory on first query
- **Subsequent queries take ~6 seconds**

**Problem**: Slow query response after restart
- **Solution**: The long-running service pre-loads index on server startup
- Wait for "[WAFService] Query service ready" log message (~35s)

**Problem**: Query service crashes or becomes unresponsive
```bash
# Restart the backend server to restart the service
# Check stderr logs for Python errors
# Verify sufficient RAM available (~100MB per KB)
```

### General Issues

**Problem**: Port already in use
```bash
# Solution: Change port in backend/.env
PORT=3001
```

**Problem**: CORS errors
- **Solution**: Ensure both frontend and backend are running on expected ports
- Frontend: http://localhost:5173
- Backend: http://localhost:3000

## Project Structure

```
Azure-Architect-Assistant/
├── backend/                    # Express TypeScript API (port 3000)
│   ├── src/
│   │   ├── api/               # REST API routes
│   │   │   ├── projects.ts    # Project + KB management endpoints
│   │   │   └── waf.ts         # Legacy WAF proxy endpoints
│   │   ├── services/          # Business logic (NEW ARCHITECTURE)
│   │   │   ├── index.ts            # Unified service exports
│   │   │   ├── LLMService.ts       # OpenAI orchestration (chat & proposals)
│   │   │   ├── RAGService.ts       # High-level RAG operations (NEW)
│   │   │   ├── KBService.ts        # Generic KB HTTP client (NEW)
│   │   │   ├── StorageService.ts   # SQLite persistence
│   │   │   └── WAFService.ts       # DEPRECATED (use KBService)
│   │   ├── db/                # Database utilities
│   │   ├── models/            # TypeScript models (Project, Message, WAFSource)
│   │   ├── logger.ts          # Logging configuration
│   │   └── index.ts           # Express server entry point
│   ├── package.json
│   └── tsconfig.json
├── python-service/            # FastAPI Python Service (port 8000)
│   ├── app/
│   │   ├── main.py           # FastAPI application & endpoints
│   │   ├── kb/               # Multi-source KB infrastructure (NEW)
│   │   │   ├── __init__.py
│   │   │   ├── manager.py         # KB configuration & selection
│   │   │   ├── service.py         # Generic KB query service
│   │   │   └── multi_query.py     # Profile-based multi-KB querying
│   │   └── rag/              # Legacy WAF-specific modules
│   │       ├── __init__.py
│   │       ├── crawler.py         # Web crawler for WAF docs
│   │       ├── cleaner.py         # HTML cleaning & markdown conversion
│   │       ├── indexer.py         # Vector index builder
│   │       ├── query.py           # RAG query engine (LlamaIndex)
│   │       └── query_service.py   # DEPRECATED stdin/stdout service
│   ├── requirements.txt      # Python dependencies (FastAPI, LlamaIndex, etc.)
│   └── README.md
├── frontend/                  # React + Vite frontend (port 5173)
│   ├── src/
│   │   ├── App.tsx                # Main app with routing
│   │   ├── WAFQueryInterface.tsx  # Standalone WAF query UI
│   │   ├── main.tsx               # React entry point
│   │   └── index.css              # Tailwind styles
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── scripts/
│   ├── ingest/
│   │   ├── waf_phase1.py     # Phase 1: Crawl & clean orchestration
│   │   └── waf_phase2.py     # Phase 2: Index & embed orchestration
│   ├── utils/
│   │   └── approve_documents.py   # Auto-approve manifest docs
│   └── run-python-service.ps1     # PowerShell script to start Python service
├── data/
│   ├── projects.db           # SQLite database (auto-created)
│   └── knowledge_bases/
│       ├── config.json       # Knowledge base registry
│       └── waf/
│           ├── urls.txt      # Crawled URLs (~275)
│           ├── documents/    # Cleaned markdown files
│           ├── manifest.json # Document validation manifest
│           └── index/        # Vector index (~60MB)
├── docs/
│   ├── guides/               # Implementation documentation
│   │   └── WAF_GUIDE.md     # Comprehensive WAF system guide
│   ├── RAG-ARCHITECTURE.md   # NEW: Multi-source RAG architecture
│   ├── ARCHITECTURE.md       # System architecture overview
│   ├── QUICKSTART.md         # Quick start guide
│   └── REFACTORING_COMPLETE.md  # Refactoring summary
├── .venv/                    # Python virtual environment
├── .env                      # Shared environment variables (root)
├── .env.example              # Environment template
├── package.json              # Workspace configuration & scripts
└── README.md
```

## Quick Reference

### New RAG Service Usage

**TypeScript (Recommended)**
```typescript
import { ragService } from "./services/RAGService.js";

// Chat context (fast)
const chatResult = await ragService.queryForChat("What is Azure reliability?");

// Proposal context (comprehensive)
const proposalResult = await ragService.queryForProposal([
  "What are security best practices?",
  "What are reliability patterns?"
]);
```

**Python Endpoints**
```bash
# Chat profile (fast, 3 results/KB)
curl -X POST http://localhost:8000/query/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is reliability?", "profile": "chat"}'

# List knowledge bases
curl http://localhost:8000/kb/list
```

### Documentation

- **[RAG Architecture](docs/RAG-ARCHITECTURE.md)** - Multi-source RAG guide (NEW)
- **[WAF Guide](docs/guides/WAF_GUIDE.md)** - Legacy WAF documentation
- **[Architecture Overview](docs/ARCHITECTURE.md)** - System design

## License

MIT

