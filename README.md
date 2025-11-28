# Azure Architecture Assistant

**Version 4.0.0** - Unified Python Backend with Modern React Architecture

A proof-of-concept application that helps Azure Solution Architects analyze project documents, clarify requirements through interactive chat, generate high-level Azure architecture proposals, and query multiple Azure knowledge bases including the Well-Architected Framework (WAF).

## Features

### Architecture Project Management
1. **Project Management**: Create and manage multiple architecture projects with SQLAlchemy + async SQLite
2. **Document Upload**: Upload RFP, specifications, and project documents (text format supported)
3. **Document Analysis**: AI-powered analysis to extract requirements, constraints, and architecture context
4. **Interactive Chat**: Multi-turn conversations with AI to refine architecture understanding
5. **Architecture State**: Structured view of project context, NFRs, constraints, and open questions
6. **Architecture Proposal**: Generate comprehensive Azure architecture proposals with streaming progress
7. **Real-Time Progress**: Server-Sent Events (SSE) provide live updates during proposal generation

### Multi-Source Knowledge Base System
8. **Multiple Knowledge Bases**: WAF (Well-Architected Framework), Azure Services, and custom sources
9. **KB Management UI**: Create, configure, and manage knowledge bases with wizard interface
10. **Real-Time Ingestion**: Live progress tracking with phase-by-phase updates (crawling, indexing, embedding)
11. **Flexible Sources**: Support for web crawling (URLs, sitemaps) and local files
12. **Parallel Querying**: Query multiple KBs simultaneously for comprehensive results
13. **Source Attribution**: All results tagged with source KB and relevance scores
14. **Health Monitoring**: KB status checks and readiness indicators
15. **Vector Search**: Fast semantic search using OpenAI embeddings with preloaded indices
16. **KB Operations**: Delete, cancel ingestion, and manage KB lifecycle

### Modern React Architecture
14. **Component Organization**: Feature-based structure (common/, projects/, kb/)
15. **Custom Hooks**: Separation of business logic (useProjectWorkspace, useKBWorkspace)
16. **Barrel Exports**: Clean imports with index.ts files per feature
17. **Type Safety**: Full TypeScript coverage throughout the stack

## Architecture

### **Unified Python Backend (v4.0)**

**Fully migrated** from TypeScript + Python to unified Python FastAPI backend for simplicity, performance, and maintainability.

```
Frontend (React + Vite) → Python Backend (FastAPI) → LlamaIndex + OpenAI
       Port 5173                  Port 8000
```

#### Stack Overview:

**Backend (Python FastAPI)** - Port 8000
- **FastAPI Framework**: Modern, async Python web framework
- **SQLAlchemy + aiosqlite**: Async SQLite ORM for project persistence
- **LlamaIndex 0.12.x**: Multi-source RAG with vector search
- **OpenAI Integration**: GPT-4o-mini for LLM, text-embedding-3-small for embeddings
- **Startup Preloading**: KB indices load at startup for instant queries
- **SSE Support**: Server-Sent Events for real-time progress updates

**Frontend (React + TypeScript + Vite)** - Port 5173
- **React 18**: Modern React with hooks
- **TypeScript**: Full type safety
- **Vite**: Fast development with HMR
- **Tailwind CSS**: Utility-first styling
- **Component Architecture**: Feature-based organization
  - `components/common/` - Reusable UI (Navigation, TabNavigation)
  - `components/projects/` - Project workspace and panels
  - `components/kb/` - Knowledge base query interface
- **Custom Hooks**: Business logic separation
  - `useProjectWorkspace` - Orchestrates project state, chat, proposals
  - `useKBWorkspace` - Manages KB health and queries
- **API Layer**: Centralized service objects (projectApi, chatApi, kbApi)

**Storage:**
- SQLite: `data/projects.db` (projects, conversations, state)
- Vector Indices: `data/knowledge_bases/*/index/` (LlamaIndex persistent storage)

### Component Architecture

```
App.tsx (Composition Root)
├── Navigation (View Switcher)
│   └── common/Navigation.tsx
├── ProjectWorkspace (Project Feature)
│   ├── useProjectWorkspace (Orchestration Hook)
│   │   ├── useProjects (project CRUD)
│   │   ├── useProjectState (state management)
│   │   ├── useChat (conversation)
│   │   └── useProposal (architecture generation)
│   └── UI Components
│       ├── ProjectList (sidebar)
│       ├── TabNavigation (common)
│       ├── DocumentsPanel
│       ├── ChatPanel
│       ├── StatePanel
│       └── ProposalPanel
├── KBIngestionWorkspace (KB Management Feature)
│   ├── useKBIngestion (Orchestration Hook)
│   │   ├── useKBList (KB list & polling)
│   │   └── useKBStatus (Status monitoring)
│   └── UI Components
│       ├── KBList (KB list with status)
│       ├── KBListItem (Individual KB card)
│       ├── CreateKBWizard (4-step wizard)
│       │   ├── BasicInfoStep
│       │   ├── SourceTypeStep
│       │   ├── ConfigurationStep
│       │   └── ReviewStep
│       ├── IngestionProgress (Real-time progress)
│       └── KBDetail (Detail view)
└── KBWorkspace (Knowledge Base Query Feature)
    ├── useKBWorkspace (Orchestration Hook)
    │   ├── useKBHealth (health monitoring)
    │   └── useKBQuery (query execution)
    └── UI Components
        ├── KBLoadingScreen
        ├── KBStatusNotReady
        ├── KBHeader
        ├── KBQueryForm
        └── KBQueryResults
```

### Backend Service Architecture

```
Python FastAPI Backend (Port 8000)
├── Startup Initialization
│   ├── Initialize database (SQLAlchemy async)
│   └── Preload KB indices (LlamaIndex)
├── API Routers (Fully Modular - 3-Layer Pattern)
│   ├── /api/projects/* (Project management)
│   │   ├── models.py (Pydantic request/response models)
│   │   ├── operations.py (ProjectService - business logic)
│   │   └── router.py (FastAPI endpoints)
│   ├── /api/ingestion/* (KB ingestion)
│   │   ├── models.py (Request/response models)
│   │   ├── operations.py (KBIngestionService)
│   │   └── router.py (Ingestion endpoints)
│   ├── /api/kb/* (KB management - NEW modular structure)
│   │   ├── models.py (KBInfo, KBHealthInfo models)
│   │   ├── operations.py (KBManagementService)
│   │   └── router.py (Health & list endpoints)
│   └── /api/query/* (KB queries - NEW modular structure)
│       ├── models.py (Query request/response models)
│       ├── operations.py (KBQueryService)
│       └── router.py (Query endpoints: /chat, /proposal, /kb-query)
├── Services Layer (Singleton Pattern)
│   ├── service_registry.py (Singleton factory functions)
│   │   ├── get_kb_manager() (Global KB manager)
│   │   ├── invalidate_kb_manager() (Cache invalidation)
│   │   ├── get_query_service() (WAF query service)
│   │   └── get_multi_query_service() (Multi-KB orchestrator)
│   ├── services/
│   │   └── llm_service.py (Document analysis, chat, proposals)
│   ├── ProjectService (CRUD, documents, chat, proposals)
│   ├── KBIngestionService (Create, ingest, monitor)
│   ├── KBManagementService (List KBs, health checks)
│   └── KBQueryService (Query operations with context)
├── KB System (Singleton with Cache Management)
│   ├── kb/manager.py (KBManager - configuration & CRUD)
│   └── kb/ingestion/ (Pipeline, job manager, crawlers)
└── Data Layer
    ├── SQLAlchemy models (Project, Message, State)
    └── LlamaIndex (Vector indices, embeddings)
```

### Key Design Principles

**Frontend Architecture:**
- **Feature-based organization** - Components grouped by domain (projects/, kb/, common/)
- **Custom hooks** - Business logic separated from UI (useProjectWorkspace, useKBWorkspace)
- **Composition pattern** - Small, focused components composed into larger features
- **Barrel exports** - Clean imports via index.ts files
- **Type safety** - Full TypeScript coverage

**Backend Architecture:**
- **Async-first** - FastAPI with async/await throughout
- **3-layer modular pattern** - All routers follow models/operations/router structure
- **Service layer** - Business logic separated from routes
- **Singleton services** - KB services initialized once, reused across requests
  - Global singleton with factory functions (get_kb_manager())
  - Cache invalidation after mutations (invalidate_kb_manager())
  - Ensures consistency between config.json and in-memory state
- **Lazy initialization** - Defer expensive operations until needed
- **Streaming responses** - SSE for real-time progress updates

**Benefits of v4.0 Architecture:**
- ✅ Single backend to run and monitor (Python only)
- ✅ Direct Python-to-LlamaIndex integration (no HTTP proxy)
- ✅ Simpler deployment (one service + static React build)
- ✅ Better type safety (SQLAlchemy models + TypeScript)
- ✅ Natural fit for AI/LLM workflows
- ✅ Modular, testable component structure
- ✅ 100% modular routers (models/operations/router pattern)
- ✅ Singleton pattern with cache invalidation for data consistency

### AI & Knowledge Base Pipeline

**LLM Operations (OpenAI GPT-4o-mini):**
- Document analysis: Extract requirements, constraints, and context
- Chat conversations: Multi-turn dialogue with context
- Proposal generation: Comprehensive architecture documents
- Model: `gpt-4o-mini` with temperature 0.7

**Knowledge Base RAG (LlamaIndex + OpenAI):**
- **Embeddings**: `text-embedding-3-small` (1536 dimensions)
- **Vector Store**: File-based persistent storage (~60MB per KB)
- **Startup**: Indices preload at server start for instant queries
- **Query Flow**: 
  1. Question → Embedding generation
  2. Vector similarity search across loaded KBs
  3. Context retrieval (top-K chunks)
  4. Answer generation with source citations
- **Performance**:
  - Index loading: ~5-10s at startup (one-time cost)
  - Query time: ~2-3s (retrieval + generation)
  - Parallel multi-KB queries supported

**Integration:**
- Direct Python service calls (no HTTP proxy)
- Automatic KB selection based on query context
- Source attribution with relevance scores
- Streaming progress for long-running operations

### RAG Architecture & Process

The system implements a sophisticated Retrieval-Augmented Generation (RAG) pipeline designed for multi-source knowledge retrieval.

#### 1. Ingestion Pipeline
The ingestion process converts raw data into searchable vector indices through a 3-phase pipeline:
1.  **Crawling**: Fetches documents from configured sources (Web URLs, Sitemaps, or Local Files).
2.  **Processing**: Cleans raw content, extracts metadata, and normalizes text.
3.  **Indexing**:
    -   **Chunking**: splits text into manageable segments (default: 800 tokens) with overlap.
    -   **Embedding**: Generates vector embeddings using `text-embedding-3-small`.
    -   **Storage**: Saves vector indices locally using LlamaIndex's file-based storage.

#### 2. Query Orchestration
Queries are handled by the `MultiSourceQueryService` which supports different profiles:
-   **Chat Profile**: Optimizes for speed and conversational flow (Top-3 results per KB).
-   **Proposal Profile**: Optimizes for comprehensive context (Top-5 results per KB).

#### 3. Retrieval Flow
1.  **Profile Selection**: Determines the query strategy (Chat vs Proposal).
2.  **Parallel Querying**: Queries relevant Knowledge Bases concurrently.
3.  **Result Merging**: Aggregates results, ranks by relevance score, and filters based on profile limits.
4.  **Synthesis**: LLM uses the retrieved context to generate the final answer or architecture proposal.

## Prerequisites

- **Python 3.10+** (for unified backend)
- **Node.js 18+** and npm (for frontend only)
- **React 19.2.0**
- **FastAPI 0.115.5**
- **LlamaIndex >= 0.14.0**
- **OpenAI API key** or Azure OpenAI credentials

## Setup

### 1. Clone and Install Dependencies

```bash
# Install Python dependencies in virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate  # Linux/Mac

cd backend
pip install -r requirements.txt
cd ..

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Configure Environment Variables

Create a `.env` file in the **project root**:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini

# Service Port
PYTHON_PORT=8000

# Logging
LOG_LEVEL=info

# OR for Azure OpenAI
AZURE_OPENAI_API_KEY=your-azure-openai-key
OPENAI_API_ENDPOINT=https://your-resource.openai.azure.com/
```

### 3. Run the Application

**Development Mode (Recommended):**

```powershell
# Terminal 1 - Start Python backend
cd backend
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 - Start React frontend
cd frontend
npm run dev
```

Access the application at `http://localhost:5173`

**Using NPM Scripts (from project root):**

```powershell
# Start Python backend
npm run backend

# Start frontend (separate terminal)
npm run frontend
```

## Usage Workflow

### Architecture Projects Tab

1. **Create a Project**
   - Enter a project name in the sidebar
   - Click "Create Project"

2. **Add Requirements**
   - Select your project from the list
   - Go to "Documents" tab
   - Either:
     - Enter text requirements directly in the textarea
     - Upload document files
   - Click "Save Requirements" or "Upload Documents"

3. **Analyze Documents**
   - Click "Analyze Documents" button
   - AI extracts architecture context, requirements, and constraints
   - Automatically switches to "State" tab

4. **Review Architecture State**
   - View extracted information:
     - Project Context & Objectives
     - Non-Functional Requirements (NFRs)
     - Application Structure
     - Data & Compliance
     - Technical Constraints
     - Open Questions

5. **Refine with Chat**
   - Go to "Chat" tab
   - Ask questions to clarify requirements
   - Discuss architecture approaches
   - State updates automatically based on conversation

6. **Generate Architecture Proposal**
   - Go to "Proposal" tab
   - Click "Generate Proposal"
   - Watch real-time progress updates
   - Review comprehensive architecture document

### Knowledge Base Management Tab

1. **Create a Knowledge Base**
   - Navigate to "KB Management" tab
   - Click "Create New KB" button
   - Follow 4-step wizard:
     - **Basic Info**: Enter name, ID, description
     - **Source Type**: Choose web (URLs/sitemap) or file upload
     - **Configuration**: Add URLs or configure source
     - **Review**: Confirm and create

2. **Start Ingestion**
   - Select your KB from the list
   - Click "Start Ingestion" button
   - Watch real-time progress:
     - Crawling phase (fetching documents)
     - Processing phase (cleaning, filtering)
     - Indexing phase (chunking, embedding)
     - Completed (ready for queries)

3. **Manage Knowledge Bases**
   - View all KBs with status indicators
   - Cancel running jobs (Stop button)
   - Delete KBs (three-dot menu → Delete)
   - Monitor progress with phase timeline

### Knowledge Base Query Tab

1. **Check KB Status**
   - Navigate to "Knowledge Base Query" tab
   - View KB health status (ready/not ready count)
   - Click "Refresh Status" to update

2. **Query Knowledge Bases**
   - Enter your question in natural language
   - Examples:
     - "What are the five pillars of the Well-Architected Framework?"
     - "What are best practices for Azure SQL security?"
     - "How do I design a highly available multi-region architecture?"
   - Click "Search Knowledge Bases"

3. **Review Results**
   - Read AI-generated answer
   - View source citations with relevance scores
   - Click source links to read original documentation
   - Use suggested follow-up questions

## API Endpoints

### Projects (Modular)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects` | List all projects |
| POST | `/api/projects` | Create new project |
| PUT | `/api/projects/{id}/requirements` | Update project requirements |
| POST | `/api/projects/{id}/documents` | Upload & extract documents |
| POST | `/api/projects/{id}/analyze-docs` | Analyze documents & extract state |
| POST | `/api/projects/{id}/chat` | Send chat message |
| GET | `/api/projects/{id}/state` | Get architecture state |
| GET | `/api/projects/{id}/messages` | Get conversation history |
| GET | `/api/projects/{id}/architecture/proposal` | Generate proposal (SSE) |

### KB Ingestion (Modular)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ingestion/kb/create` | Create new knowledge base |
| GET | `/api/ingestion/kb/list` | List all knowledge bases |
| GET | `/api/ingestion/kb/{id}` | Get KB details |
| DELETE | `/api/ingestion/kb/{id}` | Delete knowledge base |
| POST | `/api/ingestion/kb/{id}/start` | Start ingestion job |
| GET | `/api/ingestion/kb/{id}/status` | Get ingestion status |
| POST | `/api/ingestion/kb/{id}/cancel` | Cancel ingestion job |
| GET | `/api/ingestion/jobs` | List all jobs |

### KB Management (Modular - NEW)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/kb/list` | List available knowledge bases |
| GET | `/api/kb/health` | Check KB health status (ready/not ready) |

### KB Query (Modular - NEW)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/query/chat` | Query KBs with chat-style interface |
| POST | `/api/query/proposal` | Query with architecture proposal context |
| POST | `/api/query/kb-query` | Query specific KBs (returns answer + sources) |

#### KB Query Request

```json
{
  "question": "What are security best practices for Azure Storage?",
  "top_k_per_kb": 3
}
```

#### KB Query Response

```json
{
  "answer": "Based on Azure best practices...",
  "sources": [
    {
      "url": "https://learn.microsoft.com/...",
      "title": "Security best practices",
      "section": "security",
      "kb_name": "WAF",
      "score": 0.89
    }
  ],
  "has_results": true,
  "suggested_follow_ups": [
    "How do I implement encryption at rest?",
    "What about network security?"
  ]
}
```

## Data Models

### Project

```python
{
  "id": "uuid",
  "name": "string",
  "text_requirements": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### ProjectState

```python
{
  "project_id": "uuid",
  "context": {
    "summary": "string",
    "objectives": ["string"],
    "target_users": "string",
    "scenario_type": "string"
  },
  "nfrs": {
    "availability": "string",
    "security": "string", 
    "performance": "string",
    "cost_constraints": "string"
  },
  "application_structure": {
    "components": ["string"],
    "integrations": ["string"]
  },
  "data_compliance": {
    "data_types": ["string"],
    "compliance_requirements": ["string"],
    "data_residency": "string"
  },
  "technical_constraints": {
    "constraints": ["string"],
    "assumptions": ["string"]
  },
  "open_questions": ["string"],
  "last_updated": "datetime"
}
```

### Message

```python
{
  "id": "uuid",
  "project_id": "uuid",
  "role": "user" | "assistant",
  "content": "string",
  "timestamp": "datetime"
}
```

## Limitations (POC)

### Current Scope
- **Single-user application**: No authentication or multi-tenancy
- **Local storage**: SQLite database not suitable for distributed deployments
- **Text-only documents**: Full support for text files; PDF/DOCX parsing not implemented
- **Basic error handling**: Minimal validation and user feedback
- **Development mode**: Not production-ready (no containerization, monitoring, etc.)

### Knowledge Base System
- **File-based storage**: Vector indices stored locally (~60MB per KB)
- **Startup time**: 5-10 seconds to load indices at server start
- **Query performance**: ~2-3 seconds per query
- **Limited scalability**: Multiple KBs increase memory usage linearly
- **Manual ingestion**: KB content updates require re-ingestion
- **OpenAI dependency**: Requires API access; no offline mode
- **English only**: No multilingual support

## Future Enhancements

### Architecture & Deployment
- **Production deployment**: Docker containerization, Azure App Service
- **Cloud database**: Migrate to PostgreSQL, Azure SQL, or Cosmos DB
- **Vector database**: Azure AI Search, Qdrant, or Pinecone for scalable KB queries
- **Authentication**: Azure AD integration for multi-user access
- **Monitoring**: Application Insights, logging, and alerting

### Features
- **Advanced document parsing**: PDF, DOCX, Excel support
- **Architecture diagrams**: Auto-generate visual representations
- **Export capabilities**: Word, PDF, PowerPoint output
- **Version history**: Track changes to architecture state over time
- **Collaborative editing**: Multiple users working on same project
- **Azure validation**: Integration with Azure APIs to validate proposals

### Knowledge Base Improvements
- **Multi-KB support**: Query 40+ knowledge bases in parallel
- **Incremental updates**: Delta sync for documentation changes
- **Improved retrieval**: Re-ranking, hybrid search, query expansion
- **Conversation memory**: Multi-turn dialogue with context retention
- **Answer confidence**: Display reliability scores
- **User feedback**: Rate answers to improve quality
- **Multilingual**: Support for multiple languages

## Troubleshooting

### Backend Issues

**Problem**: Python dependencies not found
```powershell
# Solution: Install in virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r backend/requirements.txt
```

**Problem**: `OPENAI_API_KEY` not found
```powershell
# Solution: Create .env file in project root
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4o-mini
```

**Problem**: Port 8000 already in use
```powershell
# Solution: Stop other process or change port
# Check what's using the port
netstat -ano | findstr :8000
# Kill the process or change PYTHON_PORT in .env
```

### Frontend Issues

**Problem**: `npm install` fails
```powershell
# Solution: Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Problem**: Vite dev server won't start
```powershell
# Solution: Check port 5173 is available
# Or change port in vite.config.ts
```

### Knowledge Base Issues

**Problem**: "KB not ready" error
- **Solution**: KB indices need to be ingested first
- Check `data/knowledge_bases/*/index/` exists
- Run ingestion scripts if needed

**Problem**: Slow query responses
- **Solution**: First query after server start is slower (loads indices)
- Subsequent queries should be ~2-3 seconds
- Check OpenAI API status if consistently slow

**Problem**: KB health check fails
```powershell
# Solution: Check KB index files exist
ls data/knowledge_bases/waf/index/
# Should see default__vector_store.json and docstore.json
```

### General Issues

**Problem**: Database errors
```powershell
# Solution: Delete and recreate database
rm data/projects.db
# Restart backend to auto-create fresh database
```

**Problem**: CORS errors in browser
- **Solution**: Ensure both services are running
  - Backend: http://localhost:8000
  - Frontend: http://localhost:5173
- Check Vite proxy configuration in `vite.config.ts`

## Project Structure

```
Azure-Architect-Assistant/
├── backend/                      # Python FastAPI Backend (Port 8000)
│   ├── app/
│   │   ├── main.py              # FastAPI application entry
│   │   ├── database.py          # SQLAlchemy async setup
│   │   ├── service_registry.py  # Singleton factory functions
│   │   ├── services.py          # Service definitions
│   │   ├── routers/             # Modular API routers (3-layer pattern)
│   │   │   ├── project_management/   # Project module
│   │   │   ├── kb_ingestion/        # KB ingestion module
│   │   │   ├── kb_management/       # KB management module
│   │   │   └── kb_query/            # KB query module
│   │   ├── services/            # Business logic
│   │   ├── kb/                  # Knowledge base system
│   │   └── models/              # SQLAlchemy ORM models
│   └── requirements.txt         # Python dependencies
│
├── frontend/                     # React Frontend (Port 5173)
│   ├── src/
│   │   ├── App.tsx              # Main application (view routing)
│   │   ├── main.tsx             # React entry point
│   │   ├── index.css            # Tailwind styles
│   │   ├── components/          # UI components
│   │   │   ├── common/          # Reusable components
│   │   │   ├── projects/        # Project workspace
│   │   │   ├── ingestion/       # KB management feature
│   │   │   └── kb/              # Knowledge base query
│   │   ├── hooks/               # Custom React hooks
│   │   ├── services/            # API layer
│   │   └── types/               # TypeScript definitions
│   ├── package.json
│   ├── vite.config.ts           # Vite configuration
│   └── tsconfig.json            # TypeScript config
│
├── data/                         # Application data
│   ├── projects.db              # SQLite database (auto-created)
│   └── knowledge_bases/         # KB storage
│
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md          # System architecture
│   ├── REFACTORING_SUMMARY.md   # v4.0 refactoring
│   └── ...                      # Various documentation files
│
├── .env                          # Environment variables
├── .env.example                 # Environment template
├── package.json                 # Workspace scripts
└── README.md                    # This file
```

## Quick Start

1. **Install dependencies**
   ```powershell
   # Python backend
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r backend/requirements.txt
   
   # Frontend
   cd frontend
   npm install
   cd ..
   ```

2. **Configure environment**
   ```powershell
   # Create .env in project root
   OPENAI_API_KEY=your-key-here
   OPENAI_MODEL=gpt-4o-mini
   ```

3. **Start services**
   ```powershell
   # Terminal 1 - Python backend
   cd backend
   python -m uvicorn app.main:app --reload --port 8000
   
   # Terminal 2 - Frontend
   cd frontend
   npm run dev
   ```

4. **Access application**
   - Open http://localhost:5173
   - Create a project and start building!

## Documentation

- Technical deep-dives live under `/docs`. Runtime artifacts (e.g., ingestion snapshots) are not committed.
- Ingestion is KB-centric: only one active job per knowledge base. See `docs/ingestion-state.md` for API and snapshot details.

- **[Architecture Overview](docs/ARCHITECTURE.md)** - System design and patterns
- **[Backend Refactoring Analysis](docs/BACKEND_REFACTORING_ANALYSIS.md)** - Comprehensive code review and improvements (Nov 2024)
- **[Refactoring Summary](docs/REFACTORING_SUMMARY.md)** - v4.0 changes
- **[Component Structure](frontend/COMPONENTS_STRUCTURE.md)** - Frontend organization
  
## Contributing

This is a proof-of-concept project. Contributions, ideas, and feedback are welcome!

## License

MIT

