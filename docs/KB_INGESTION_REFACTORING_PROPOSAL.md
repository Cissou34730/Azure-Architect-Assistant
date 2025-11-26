# KB Ingestion System - Refactoring Proposal

## Current State Analysis

### Issues Identified

1. **Hardcoded KB-specific logic**: `WAFCrawler`, `WAFIngestionPipeline`, `WAFIndexBuilder` are tightly coupled to WAF
2. **No UI Management**: Ingestion is manual via CLI scripts (`waf_phase1.py`, `waf_phase2.py`)
3. **Scattered locations**: Scripts in `scripts/ingest/`, RAG classes in `backend/app/rag/`, endpoints in `backend/app/routers/ingest.py`
4. **Data folder placement**: `data/` at root level (questionable for multi-KB architecture)
5. **Limited observability**: No progress tracking, status monitoring, or error recovery in UI

### Current Architecture

```
Root/
├── scripts/ingest/          # CLI scripts (waf_phase1.py, waf_phase2.py)
├── backend/app/rag/         # RAG classes (crawler, cleaner, indexer)
├── backend/app/routers/     # ingest.py with background tasks
└── data/                    # Knowledge base storage
    ├── knowledge_bases/
    │   └── waf/
    │       ├── documents/
    │       ├── index/
    │       ├── manifest.json
    │       └── urls.txt
    └── projects.db
```

## Proposed Solutions

### Option 1: Minimal Refactor (Quick Win)
**Focus**: Add UI tab without major restructuring

**Changes**:
- Keep `data/` at root (common pattern for data-heavy apps)
- Add "KB Management" tab in frontend
- Generic ingestion endpoints with KB ID parameter
- Keep existing RAG classes but make them KB-agnostic

**Pros**:
- Fast implementation (~4-6 hours)
- Minimal breaking changes
- Data stays centralized at root

**Cons**:
- Still some hardcoded logic
- Limited extensibility

---

### Option 2: Full Refactor (Scalable)
**Focus**: Production-ready multi-KB ingestion system

**Changes**:
1. **Folder restructure**:
   ```
   backend/
   ├── app/
   │   ├── kb/
   │   │   ├── ingestion/      # NEW: Generic ingestion logic
   │   │   │   ├── crawler.py
   │   │   │   ├── cleaner.py
   │   │   │   ├── embedder.py
   │   │   │   └── indexer.py
   │   │   ├── manager.py
   │   │   └── service.py
   │   └── routers/
   │       └── ingestion.py    # NEW: Generic ingestion API
   └── data/                   # MOVED: Inside backend
       ├── knowledge_bases/
       └── projects.db
   ```

2. **Generic ingestion classes**:
   - `DocumentCrawler` (base class with Azure/Web/Local implementations)
   - `DocumentCleaner` (pipeline with configurable processors)
   - `DocumentEmbedder` (supports multiple embedding models)
   - `IndexBuilder` (KB-agnostic with config-driven setup)

3. **New UI tab**: "KB Management" with:
   - KB list with status indicators
   - Create new KB wizard (select source, configure params)
   - Monitor ingestion progress (crawling, cleaning, embedding, indexing)
   - Validate documents before indexing
   - Trigger re-indexing

4. **Background job system**:
   - Job queue with status tracking
   - Progress reporting via WebSocket or polling
   - Error recovery and retry logic

**Pros**:
- Production-ready, scalable architecture
- Easy to add new KB types (GitHub, SharePoint, PDFs, etc.)
- Full observability and control from UI
- Clean separation of concerns

**Cons**:
- Significant refactoring effort (~2-3 days)
- Need to update imports and paths
- Migration needed for existing data

---

### Option 3: Hybrid Approach (Recommended)
**Focus**: Balance quick wins with long-term scalability

**Phase 1** (~6-8 hours):
1. Move `data/` inside `backend/` for better encapsulation
2. Create generic base classes while keeping WAF-specific implementations
3. Add UI tab with basic KB management (list, trigger ingestion, view status)
4. Implement job status tracking via polling endpoint

**Phase 2** (future sprint):
1. Add new KB source types (beyond Microsoft Learn)
2. Implement WebSocket for real-time progress
3. Add document validation/approval workflow in UI
4. Build KB configuration wizard

## Detailed Design (Hybrid Approach)

### 1. Folder Structure Changes

```
backend/
├── app/
│   ├── kb/
│   │   ├── ingestion/              # NEW
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Base classes
│   │   │   ├── crawler.py          # Generic crawler
│   │   │   ├── cleaner.py          # Generic cleaner
│   │   │   ├── indexer.py          # Generic indexer
│   │   │   └── sources/            # Source-specific implementations
│   │   │       ├── __init__.py
│   │   │       ├── microsoft_learn.py  # For WAF, Azure docs
│   │   │       ├── local_files.py      # For uploaded files
│   │   │       └── web_generic.py      # Generic web crawler
│   │   ├── manager.py
│   │   ├── service.py
│   │   └── multi_query.py
│   ├── routers/
│   │   ├── ingestion.py            # UPDATED: Generic endpoints
│   │   ├── kb.py
│   │   ├── query.py
│   │   └── projects.py
│   └── rag/                         # DEPRECATED: Move to archive
└── data/                            # MOVED from root
    ├── knowledge_bases/
    │   ├── config.json
    │   ├── waf/
    │   ├── azure-security/          # Future KB
    │   └── landing-zones/           # Future KB
    └── projects.db

scripts/
└── ingest/                          # DEPRECATED: Keep for reference
    └── archive/
```

### 2. Generic Ingestion Classes

#### Base Crawler (`backend/app/kb/ingestion/base.py`)
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class DocumentCrawler(ABC):
    """Base class for document crawlers."""
    
    def __init__(self, kb_id: str, config: Dict[str, Any]):
        self.kb_id = kb_id
        self.config = config
    
    @abstractmethod
    def crawl(self) -> List[str]:
        """Crawl and return list of document URLs/paths."""
        pass
    
    @abstractmethod
    def fetch_content(self, url: str) -> str:
        """Fetch raw content from URL."""
        pass

class DocumentCleaner(ABC):
    """Base class for document cleaners."""
    
    @abstractmethod
    def clean(self, raw_content: str, metadata: Dict) -> Dict[str, Any]:
        """Clean and structure document content."""
        pass

class IndexBuilder(ABC):
    """Base class for index builders."""
    
    @abstractmethod
    def build_index(self, documents: List[Dict], kb_config: Dict) -> None:
        """Build vector index from documents."""
        pass
```

#### Microsoft Learn Crawler (`backend/app/kb/ingestion/sources/microsoft_learn.py`)
```python
from ..base import DocumentCrawler

class MicrosoftLearnCrawler(DocumentCrawler):
    """Crawler for Microsoft Learn documentation."""
    
    def __init__(self, kb_id: str, config: Dict[str, Any]):
        super().__init__(kb_id, config)
        self.start_url = config.get('start_url')
        self.max_depth = config.get('max_depth', 3)
        self.max_pages = config.get('max_pages', 500)
    
    def crawl(self) -> List[str]:
        # Reuse existing WAFCrawler logic but generalized
        pass
```

### 3. New API Endpoints

#### Ingestion Router (`backend/app/routers/ingestion.py`)

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])

class CreateKBRequest(BaseModel):
    name: str
    source_type: str  # 'microsoft-learn', 'local-files', 'web-generic'
    source_config: dict  # Source-specific configuration

class IngestionJobResponse(BaseModel):
    job_id: str
    kb_id: str
    status: str  # 'pending', 'running', 'completed', 'failed'
    progress: int  # 0-100
    message: str
    error: Optional[str] = None

@router.post("/kb/create")
async def create_kb(request: CreateKBRequest):
    """Create a new knowledge base (config only, no ingestion yet)."""
    pass

@router.post("/kb/{kb_id}/ingest/start")
async def start_ingestion(kb_id: str):
    """Start ingestion process for a KB (crawl + clean + embed + index)."""
    pass

@router.get("/kb/{kb_id}/ingest/status")
async def get_ingestion_status(kb_id: str) -> IngestionJobResponse:
    """Get current status of ingestion job."""
    pass

@router.post("/kb/{kb_id}/ingest/cancel")
async def cancel_ingestion(kb_id: str):
    """Cancel running ingestion job."""
    pass

@router.get("/kb/{kb_id}/documents")
async def list_documents(kb_id: str):
    """List documents in KB with validation status."""
    pass

@router.post("/kb/{kb_id}/documents/{doc_id}/approve")
async def approve_document(kb_id: str, doc_id: str):
    """Approve a document for indexing."""
    pass
```

### 4. Frontend: KB Management Tab

#### New Components

```
frontend/src/components/ingestion/
├── IngestionWorkspace.tsx       # Main container
├── KBList.tsx                   # List all KBs with status
├── CreateKBWizard.tsx           # Multi-step wizard to create KB
├── IngestionProgress.tsx        # Progress bar with status
├── DocumentValidation.tsx       # Review/approve documents
└── index.ts                     # Barrel export
```

#### Navigation Update
Add new tab to `Navigation.tsx`:
```typescript
{ id: 'kb-management', label: 'KB Management', icon: '🗄️' }
```

#### Key Features
1. **KB List View**:
   - Table with: Name, Status, Document Count, Last Updated, Actions
   - Status badges: 🟢 Active, 🟡 Ingesting, 🔴 Error, ⚪ Draft

2. **Create KB Wizard**:
   - Step 1: Basic info (name, description)
   - Step 2: Select source type
   - Step 3: Configure source (URL, depth, filters)
   - Step 4: Review and create

3. **Ingestion Progress**:
   - Real-time progress bar
   - Phase indicators: Crawling → Cleaning → Embedding → Indexing
   - Document count, error count, estimated time remaining
   - Log stream showing recent activities

4. **Document Validation**:
   - List of crawled documents with preview
   - Approve/Reject controls
   - Bulk actions (Select All, Approve All)
   - Search/filter documents

### 5. Job Management System

```python
# backend/app/kb/ingestion/job_manager.py

from enum import Enum
from typing import Dict, Optional
from datetime import datetime

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class IngestionJob:
    def __init__(self, kb_id: str, job_type: str):
        self.job_id = f"{kb_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.kb_id = kb_id
        self.job_type = job_type
        self.status = JobStatus.PENDING
        self.progress = 0
        self.message = "Job created"
        self.error: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    def update(self, progress: int, message: str):
        self.progress = progress
        self.message = message

class JobManager:
    _jobs: Dict[str, IngestionJob] = {}
    
    @classmethod
    def create_job(cls, kb_id: str, job_type: str) -> IngestionJob:
        job = IngestionJob(kb_id, job_type)
        cls._jobs[job.job_id] = job
        return job
    
    @classmethod
    def get_job(cls, job_id: str) -> Optional[IngestionJob]:
        return cls._jobs.get(job_id)
```

## Data Folder Location - Best Practices

### Arguments for `data/` at Root Level
✅ **Pros**:
- Common pattern for full-stack apps (Next.js, Django often use this)
- Clear separation: code vs data
- Easy to backup/exclude from git
- Frontend can potentially access (if needed via static serving)

❌ **Cons**:
- Backend must reach outside its directory (`../data`)
- Violates backend encapsulation
- Harder to containerize backend independently

### Arguments for `data/` inside Backend
✅ **Pros**:
- **Better encapsulation**: Backend owns its data
- **Easier Docker deployment**: `COPY backend/ /app/` includes everything
- **Cleaner imports**: No `../` paths
- **Microservices-ready**: Each service has its own data

❌ **Cons**:
- Less common pattern for monorepos
- Frontend can't directly access (but shouldn't anyway)

### Recommendation: **Move to `backend/data/`**

**Rationale**:
- Your backend is the **only** consumer of this data
- Future-proofs for containerization and deployment
- Aligns with your v4.0 unified backend architecture
- Projects DB should also live with backend

**Migration Path**:
```bash
Move-Item data/ backend/data/
```

Update paths in:
- `backend/app/database.py` (projects.db path)
- `backend/app/kb/manager.py` (config.json path)
- `backend/app/kb/service.py` (index paths)
- Environment variables (if any)

## Implementation Timeline

### Phase 1: Foundation (Day 1)
- [ ] Move `data/` to `backend/data/`
- [ ] Update all path references
- [ ] Create `backend/app/kb/ingestion/` structure
- [ ] Create base classes (crawler, cleaner, indexer)
- [ ] Refactor WAF classes to use generic bases
- [ ] Test existing WAF KB still works

### Phase 2: Backend API (Day 2)
- [ ] Implement generic ingestion endpoints
- [ ] Add job management system
- [ ] Create status tracking
- [ ] Update existing `/api/ingest/` endpoints
- [ ] Add document validation endpoints
- [ ] Test with Postman/curl

### Phase 3: Frontend UI (Day 3)
- [ ] Create IngestionWorkspace component
- [ ] Add KB Management tab to navigation
- [ ] Implement KB list view
- [ ] Build ingestion progress component
- [ ] Add create KB wizard (basic version)
- [ ] Wire up API calls
- [ ] Test end-to-end flow

### Phase 4: Polish & Documentation (Day 4)
- [ ] Add error handling and retries
- [ ] Improve progress reporting
- [ ] Add document validation UI
- [ ] Write documentation
- [ ] Create example KB ingestion guide
- [ ] Update README.md

## Success Criteria

1. ✅ **Data encapsulation**: `backend/data/` location
2. ✅ **Generic architecture**: Add new KB without code changes
3. ✅ **UI management**: Full ingestion lifecycle from UI
4. ✅ **Observability**: Real-time progress and status tracking
5. ✅ **Backward compatibility**: Existing WAF KB works unchanged
6. ✅ **Documentation**: Clear guide for adding new KBs

## Questions to Resolve

1. **Do you want to start with Hybrid Phase 1 or go straight to full refactor?**
2. **Should we move `data/` to `backend/data/` now or later?**
3. **Do you want document validation workflow in initial version?**
4. **Should we support file uploads (PDFs, DOCX) in first iteration?**
5. **Real-time progress via WebSocket or polling is acceptable?**

## Next Steps

Once you approve the direction, I'll start implementation with:
1. Move `data/` folder to `backend/data/`
2. Create generic ingestion base classes
3. Refactor existing WAF logic to use new structure
4. Build UI components for KB Management tab

Let me know your preferences and any questions!
