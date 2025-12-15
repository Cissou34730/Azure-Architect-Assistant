# Ingestion Module Refactoring Plan

**Date:** December 12, 2025  
**Branch:** resilientingestion  
**Scope:** backend/app/ingestion/

## Executive Summary

After comprehensive analysis of the ingestion codebase, I've identified critical violations of development best practices (DRY, SRP, meaningful names) and technical debt that impacts maintainability and scalability. This document provides a detailed remediation plan organized by module with prioritized actions.

### Key Issues Identified

1. **Deprecated Code Accumulation**: 40+ instances of deprecated producer/consumer pattern still present
2. **Responsibility Fragmentation**: Orchestrator class violates SRP with 482 lines doing loading, chunking, embedding, indexing, and coordination
3. **DRY Violations**: Repeated patterns for status checking, error handling, and metadata enrichment
4. **Naming Inconsistencies**: Mixed conventions (`fetch_batches` vs `chunk_documents_to_chunks`)
5. **Global State**: Module-level `_shutdown_event` and `_running_tasks` dictionary
6. **Large Files**: Repository.py (739 lines), Orchestrator.py (482 lines), Crawler.py (346 lines)

---

## Priority Classification

- 🔴 **P0 - Critical**: Blocking technical debt, security issues, or production bugs
- 🟡 **P1 - High**: Maintainability issues, code smells, violates best practices
- 🟢 **P2 - Medium**: Nice-to-have improvements, refactoring opportunities
- 🔵 **P3 - Low**: Documentation, minor naming improvements

---

## Module 1: Application Layer

### 1.1 Orchestrator (orchestrator.py) - 🔴 P0

**Current Issues:**
- **SRP Violation**: Single class responsible for workflow coordination, batch processing, chunking, embedding, indexing, error handling, checkpoint management, and shutdown handling
- **God Object**: 482 lines with multiple concerns
- **Global State**: `_shutdown_event` at module level
- **Mixed Abstraction Levels**: High-level orchestration mixed with low-level chunk processing
- **Method Length**: `run()` method exceeds 100 lines

**Refactoring Plan:**

```
orchestrator/
├── __init__.py
├── coordinator.py           # IngestionCoordinator - workflow orchestration only
├── batch_processor.py       # BatchProcessor - batch-level processing
├── chunk_processor.py       # ChunkProcessor - individual chunk processing
├── checkpoint_manager.py    # CheckpointManager - state persistence
├── shutdown_manager.py      # ShutdownManager - graceful shutdown coordination
├── workflow.py              # WorkflowDefinition, RetryPolicy (existing)
└── models.py                # ProcessingTask, StepName (existing)
```

**Actions:**

1. **Extract CheckpointManager** 🔴
   - Move checkpoint save/load logic
   - Handle counter persistence
   - Encapsulate checkpoint dict structure
   ```python
   class CheckpointManager:
       def __init__(self, repo: DatabaseRepository):
           self.repo = repo
       
       def save_checkpoint(self, job_id: str, batch_id: int, counters: Dict) -> None
       def load_checkpoint(self, job_id: str) -> Tuple[Dict, Dict]
       def update_counters(self, job_id: str, counters: Dict) -> None
   ```

2. **Extract ShutdownManager** 🔴
   - Move shutdown event from module-level global
   - Encapsulate shutdown flag logic
   - Coordinate shutdown across multiple orchestrators
   ```python
   class ShutdownManager:
       def __init__(self):
           self._shutdown_event = asyncio.Event()
       
       def request_shutdown(self) -> None
       def is_shutdown_requested(self) -> bool
       def clear_shutdown_flag(self) -> None
   ```

3. **Extract ChunkProcessor** 🟡
   - Move `_process_chunk_with_retry` logic
   - Handle embedding + indexing for single chunk
   - Apply retry policy
   ```python
   class ChunkProcessor:
       def __init__(self, embedder: Embedder, indexer: Indexer, retry_policy: RetryPolicy):
           ...
       
       async def process_chunk(self, chunk: Chunk, task: ProcessingTask) -> Dict[str, Any]
   ```

4. **Extract BatchProcessor** 🟡
   - Move batch-level chunking logic
   - Coordinate chunk processing
   - Track batch-level metrics
   ```python
   class BatchProcessor:
       def __init__(self, chunker, chunk_processor: ChunkProcessor):
           ...
       
       async def process_batch(self, batch: List[Document], batch_id: int) -> BatchResult
   ```

5. **Refactor IngestionCoordinator** 🟡
   - Keep only high-level workflow coordination
   - Delegate to specialized managers
   - Reduce to <200 lines
   ```python
   class IngestionCoordinator:
       def __init__(
           self,
           repo: DatabaseRepository,
           workflow: WorkflowDefinition,
           checkpoint_manager: CheckpointManager,
           batch_processor: BatchProcessor,
           shutdown_manager: ShutdownManager
       ):
           ...
       
       async def run(self, job_id: str, kb_id: str, kb_config: Dict[str, Any]) -> None
   ```

**Benefits:**
- Each class has single responsibility
- Easier to test individual components
- Clearer separation of concerns
- Reduced cognitive load

---

### 1.2 Status Query Service (status_query_service.py) - 🟡 P1

**Current Issues:**
- **Naming**: Method `get_status` returns `KBPersistedStatus` - not clear it's KB-specific
- **Hard-coded List**: `CANONICAL_PHASES` at module level
- **Tight Coupling**: Directly instantiates repository

**Refactoring Plan:**

1. **Rename for Clarity** 🟡
   ```python
   # Before
   def get_status(self, kb_id: str) -> KBPersistedStatus
   
   # After
   def get_kb_ingestion_status(self, kb_id: str) -> KnowledgeBaseIngestionStatus
   ```

2. **Move Constants to Config** 🟡
   ```python
   # config/ingestion_phases.py
   @dataclass
   class IngestionPhaseConfig:
       phases: List[str] = field(default_factory=lambda: ["loading", "chunking", "embedding", "indexing"])
       
       def get_canonical_order(self) -> List[str]:
           return self.phases.copy()
   ```

3. **Dependency Injection** 🟢
   ```python
   class StatusQueryService:
       def __init__(self, repo: DatabaseRepository, phase_config: IngestionPhaseConfig):
           self.repo = repo
           self.phase_config = phase_config
   ```

---

### 1.3 Deprecated Files - 🔴 P0

**Files to Remove:**
- `consumer_pipeline.py` (deprecated 2025-12-10)
- `producer_pipeline.py` (deprecated 2025-12-10)
- `ingestion_service.py` (deprecated 2025-12-10)
- `workers/consumer.py` (deprecated 2025-12-10)
- `workers/producer.py` (deprecated 2025-12-10)

**Actions:**

1. **Verify No Active Usage** 🔴
   ```bash
   # Search for imports
   grep -r "from app.ingestion.application.producer_pipeline" backend/
   grep -r "ConsumerPipeline" backend/
   grep -r "IngestionService" backend/ --exclude-dir=ingestion
   ```

2. **Create Migration Archive** 🔴
   ```
   backend/archive/legacy_producer_consumer/
   ├── README.md (explains why archived, migration path)
   ├── consumer_pipeline.py
   ├── producer_pipeline.py
   ├── ingestion_service.py
   └── workers/
   ```

3. **Remove from Codebase** 🔴

4. **Update Documentation** 🔴
   - Remove references from README.md
   - Update architecture diagrams
   - Add migration guide for any external consumers

---

## Module 2: Domain Layer

### 2.1 Loading (domain/loading/loader.py) - 🟡 P1

**Current Issues:**
- **Function Name**: `fetch_batches` - unclear that it's a generator
- **DRY Violation**: Document validation/enrichment duplicated in generator and list paths
- **Mixed Concerns**: Batch creation logic mixed with validation
- **Long Function**: 144 lines for single function

**Refactoring Plan:**

1. **Rename for Clarity** 🟡
   ```python
   # Before
   def fetch_batches(...) -> Generator[List[Document], None, None]
   
   # After  
   def stream_document_batches(...) -> Generator[List[Document], None, None]
   ```

2. **Extract Document Validator** 🟡
   ```python
   class DocumentValidator:
       def __init__(self, kb_id: str):
           self.kb_id = kb_id
           self.doc_index = 0
       
       def validate_and_enrich(self, doc: Document) -> Optional[Document]:
           """Returns None if document should be skipped"""
           if not doc.text or not doc.text.strip():
               logger.warning(f"Skipping document {self.doc_index}: empty text")
               return None
           
           # Ensure document has an ID
           if not doc.id_:
               doc.id_ = f"{self.kb_id}_doc_{self.doc_index}"
           
           # Enrich metadata
           if not doc.metadata:
               doc.metadata = {}
           doc.metadata.setdefault('kb_id', self.kb_id)
           doc.metadata.setdefault('doc_id', self.doc_index)
           
           return doc
   ```

3. **Extract Batch Creator** 🟡
   ```python
   class DocumentBatchCreator:
       def __init__(self, batch_size: int):
           self.batch_size = batch_size
       
       def create_batches(
           self,
           documents: List[Document],
           validator: DocumentValidator
       ) -> Generator[List[Document], None, None]:
           """Convert list to validated batches"""
           current_batch = []
           for doc in documents:
               validated = validator.validate_and_enrich(doc)
               if validated:
                   current_batch.append(validated)
                   if len(current_batch) >= self.batch_size:
                       yield current_batch
                       current_batch = []
           
           if current_batch:
               yield current_batch
   ```

4. **Refactor stream_document_batches** 🟡
   ```python
   def stream_document_batches(
       kb_config: Dict[str, Any],
       checkpoint: Optional[Dict[str, Any]] = None,
       batch_size: int = 10
   ) -> Generator[List[Document], None, None]:
       """
       Stream validated document batches from configured source.
       
       Args:
           kb_config: KB configuration with 'source_type', 'source_config', 'kb_id'
           checkpoint: Optional checkpoint for resumption
           batch_size: Documents per batch
           
           Yields:
           Validated batches of LlamaIndex Documents
       """
       # Validate config
       kb_id = kb_config.get('kb_id')
       if not kb_id:
           raise ValueError("kb_config must contain 'kb_id'")
       
       # Create helper instances
       validator = DocumentValidator(kb_id)
       batch_creator = DocumentBatchCreator(batch_size)
       
       # Get source handler
       handler = create_source_handler(kb_config)
       
       # Stream from source
       result = handler.ingest(kb_config.get('source_config', {}))
       
       # Handle generator vs list
       if inspect.isgenerator(result):
           for batch in result:
               validated_batch = [validator.validate_and_enrich(doc) for doc in batch]
               validated_batch = [d for d in validated_batch if d is not None]
               if validated_batch:
                   yield validated_batch
       else:
           yield from batch_creator.create_batches(result, validator)
   ```

**Benefits:**
- Single responsibility for each component
- Validation logic in one place
- Easier to test
- More descriptive function names

---

### 2.2 Chunking (domain/chunking/adapter.py) - 🟡 P1

**Current Issues:**
- **Naming**: `chunk_documents_to_chunks` - redundant "chunk" in name
- **Mixed Concerns**: Hash computation, chunking, metadata enrichment all in one file
- **DRY**: Source ID extraction logic could be reusable

**Refactoring Plan:**

1. **Rename Functions** 🟡
   ```python
   # Before
   def chunk_documents_to_chunks(documents, chunker, kb_id) -> List[Chunk]
   
   # After
   def create_chunks_from_documents(documents, chunker, kb_id) -> List[Chunk]
   ```

2. **Extract ContentHasher** 🟡
   ```python
   # domain/chunking/hasher.py
   class ContentHasher:
       """Compute deterministic content hashes for chunks"""
       
       @staticmethod
       def compute_hash(text: str, kb_id: str, source_id: str) -> str:
           """Compute SHA256 hash for chunk content"""
           normalized = text.strip().lower()
           composite = f"{kb_id}::{source_id}::{normalized}"
           return hashlib.sha256(composite.encode('utf-8')).hexdigest()
   ```

3. **Extract Metadata Helper** 🟡
   ```python
   class ChunkMetadataBuilder:
       """Build standardized metadata for chunks"""
       
       @staticmethod
       def extract_source_id(metadata: Dict[str, Any], fallback_index: int) -> str:
           """Extract source identifier from document metadata"""
           return (
               metadata.get('url') or
               metadata.get('file_path') or
               metadata.get('source') or
               f"doc_{metadata.get('doc_id', fallback_index)}"
           )
       
       @staticmethod
       def enrich_chunk_metadata(
           metadata: Dict[str, Any],
           kb_id: str,
           chunk_index: int,
           content_hash: str
       ) -> Dict[str, Any]:
           """Add standard fields to chunk metadata"""
           enriched = metadata.copy()
           enriched.update({
               'kb_id': kb_id,
               'chunk_index': chunk_index,
               'content_hash': content_hash
           })
           return enriched
   ```

---

### 2.3 Website Crawler (domain/sources/website/crawler.py) - 🟡 P1

**Current Issues:**
- **Long File**: 346 lines, multiple responsibilities
- **Large Method**: `crawl()` method exceeds 200 lines
- **State Management**: Multiple mutable state variables in method
- **Logging Verbosity**: Inconsistent logging with commented-out debug statements
- **Hard-coded Values**: Timeout, retries, delays scattered throughout

**Refactoring Plan:**

1. **Extract Configuration** 🟡
   ```python
   @dataclass
   class CrawlerConfig:
       timeout: int = 15
       max_retries: int = 3
       rate_limit_delay: float = 0.5
       checkpoint_interval: int = 50
       batch_size: int = 10
       max_pages: int = 1000
       
       user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
   ```

2. **Extract CrawlState** 🟡
   ```python
   @dataclass
   class CrawlState:
       """Encapsulate crawler state for checkpoint/resume"""
       visited: Set[str] = field(default_factory=set)
       to_visit: List[str] = field(default_factory=list)
       last_doc_id: int = 0
       failed_count: int = 0
       pages_since_checkpoint: int = 0
       
       def mark_visited(self, url: str) -> None:
           self.visited.add(url)
       
       def should_visit(self, url: str) -> bool:
           return url not in self.visited and url not in self.to_visit
       
       def add_to_queue(self, urls: List[str]) -> int:
           """Add new URLs and return count added"""
           new_count = 0
           for url in urls:
               if self.should_visit(url):
                   self.to_visit.append(url)
                   new_count += 1
           return new_count
   ```

3. **Extract PageFetcher** 🟡
   ```python
   class PageFetcher:
       """Handle HTTP requests with retry logic"""
       
       def __init__(self, config: CrawlerConfig):
           self.config = config
           self.headers = {'User-Agent': config.user_agent}
       
       def fetch_page(self, url: str) -> Tuple[Optional[str], Optional[str]]:
           """
           Fetch page HTML with retry and redirect handling.
           Returns (html_content, final_url)
           """
           for attempt in range(self.config.max_retries):
               try:
                   response = requests.get(
                       url,
                       headers=self.headers,
                       timeout=self.config.timeout,
                       allow_redirects=True
                   )
                   response.raise_for_status()
                   return response.text, response.url
               except requests.RequestException as e:
                   if attempt == self.config.max_retries - 1:
                       logger.warning(f"Failed to fetch {url} after {self.config.max_retries} attempts: {e}")
                       return None, None
                   time.sleep(0.5 * (attempt + 1))  # Exponential backoff
           
           return None, None
   ```

4. **Extract ContentExtractor** 🟡
   ```python
   class ContentExtractor:
       """Extract clean content and links from HTML"""
       
       @staticmethod
       def extract_content(html: str) -> Optional[str]:
           """Extract clean text using trafilatura"""
           return trafilatura.extract(html, include_comments=False, include_tables=True)
       
       @staticmethod
       def extract_links(html: str, base_url: str) -> List[str]:
           """Extract and normalize links from HTML"""
           soup = BeautifulSoup(html, 'html.parser')
           links = []
           for a_tag in soup.find_all('a', href=True):
               href = a_tag['href']
               if href.startswith(('http://', 'https://')):
                   links.append(href)
               else:
                   links.append(urljoin(base_url, href))
           return links
   ```

5. **Refactor WebsiteCrawler** 🟡
   ```python
   class WebsiteCrawler:
       """Orchestrate website crawling with checkpointing"""
       
       def __init__(
           self,
           kb_id: str,
           config: CrawlerConfig,
           page_fetcher: PageFetcher,
           content_extractor: ContentExtractor
       ):
           self.kb_id = kb_id
           self.config = config
           self.page_fetcher = page_fetcher
           self.content_extractor = content_extractor
       
       def crawl(
           self,
           start_url: str,
           url_prefix: str = None,
           state: Optional<CrawlState> = None
       ) -> Generator[List[Document], None, None]:
           """
           Crawl website yielding document batches.
           Much shorter method (<80 lines) delegating to helpers.
           """
           # Initialize state
           state = state or CrawlState(to_visit=[start_url])
           batch_builder = DocumentBatchBuilder(self.kb_id, self.config.batch_size)
           
           logger.info(f"Crawler start: {start_url}")
           
           while state.to_visit and len(state.visited) < self.config.max_pages:
               url = state.to_visit.pop(0)
               
               if not self._is_valid_url(url, url_prefix):
                   continue
               
               # Fetch and process page
               yield from self._process_page(url, state, batch_builder)
               
               # Rate limiting
               time.sleep(self.config.rate_limit_delay)
           
           # Yield final batch
           yield from batch_builder.flush()
           
           logger.info(f"Crawl complete: {len(state.visited)} pages")
   ```

**Benefits:**
- Clear separation of concerns
- Each class <100 lines
- Easy to test individual components
- Configuration externalized
- State management encapsulated

---

## Module 3: Infrastructure Layer

### 3.1 Repository (infrastructure/repository.py) - 🔴 P0

**Current Issues:**
- **Large File**: 739 lines - violates SRP
- **Mixed Concerns**: Job management, queue operations, phase status, deprecated methods all in one class
- **Deprecated Code**: Multiple methods marked deprecated but still present
- **Method Naming**: Inconsistent naming (`get_latest_job` vs `get_latest_job_record` vs `get_latest_job_id`)
- **Error Handling**: Inconsistent - some methods raise, some return None

**Refactoring Plan:**

1. **Split into Specialized Repositories** 🔴
   ```
   infrastructure/persistence/
   ├── __init__.py
   ├── job_repository.py        # IngestionJobRepository - job CRUD
   ├── queue_repository.py      # IngestionQueueRepository - queue operations
   ├── phase_repository.py      # PhaseStatusRepository - phase status
   ├── checkpoint_repository.py # CheckpointRepository - checkpoint/counters
   └── repository_factory.py    # Factory for creating repositories
   ```

2. **Create IngestionJobRepository** 🔴
   ```python
   class IngestionJobRepository:
       """Manage ingestion job persistence"""
       
       def create_job(self, kb_id: str, source_type: str, source_config: Dict, priority: int = 0) -> str
       def get_job_by_id(self, job_id: str) -> Optional[IngestionJob]
       def get_latest_job_for_kb(self, kb_id: str) -> Optional[IngestionJob]
       def update_job_status(self, job_id: str, status: str, error: str = None) -> None
       def update_heartbeat(self, job_id: str) -> None
       def list_jobs_by_status(self, status: str) -> List[IngestionJob]
   ```

3. **Create PhaseStatusRepository** 🔴
   ```python
   class PhaseStatusRepository:
       """Manage phase status persistence"""
       
       def initialize_phases(self, job_id: str, phases: List[str]) -> None
       def get_phase_status(self, job_id: str, phase_name: str) -> Optional[PhaseState]
       def get_all_phase_statuses(self, job_id: str) -> Dict[str, PhaseState]
       def update_phase_status(self, job_id: str, phase_name: str, updates: Dict) -> None
       def mark_phase_completed(self, job_id: str, phase_name: str) -> None
   ```

4. **Create CheckpointRepository** 🔴
   ```python
   class CheckpointRepository:
       """Manage checkpoint and counter persistence"""
       
       def save_checkpoint(self, job_id: str, checkpoint: Dict) -> None
       def load_checkpoint(self, job_id: str) -> Dict
       def save_counters(self, job_id: str, counters: Dict) -> None
       def load_counters(self, job_id: str) -> Dict
       def update_checkpoint_and_counters(self, job_id: str, checkpoint: Dict, counters: Dict) -> None
   ```

5. **Remove Deprecated Methods** 🔴
   - `update_phase_progress` (deprecated)
   - `get_phase_progress` (deprecated)
   - Any methods only used by old producer/consumer

6. **Standardize Method Naming** 🟡
   ```python
   # Before - inconsistent
   get_latest_job(kb_id)         # Returns IngestionState
   get_latest_job_record(kb_id)  # Returns IngestionJob
   get_latest_job_id(kb_id)      # Returns str
   
   # After - clear and consistent
   get_latest_job_for_kb(kb_id) -> Optional[IngestionJob]
   get_latest_job_id_for_kb(kb_id) -> Optional[str]
   ```

7. **Standardize Error Handling** 🟡
   ```python
   class JobNotFoundError(Exception):
       """Raised when job doesn't exist"""
       pass
   
   class PhaseNotFoundError(Exception):
       """Raised when phase doesn't exist"""
       pass
   
   # Use consistently - don't mix None returns and exceptions
   def get_job_by_id(self, job_id: str) -> IngestionJob:
       """
       Get job by ID.
       Raises JobNotFoundError if not found.
       """
   ```

**Benefits:**
- Each repository <200 lines
- Clear responsibility boundaries
- Easier to test
- Consistent error handling

---

### 3.2 Database Models (models.py) - 🟢 P2

**Current Issues:**
- **Enum Duplication**: `JobStatus` enum in models.py and `domain/enums.py`
- **Naming**: `IngestionQueueItem` vs `QueueItem` inconsistency

**Refactoring Plan:**

1. **Consolidate Enums** 🟢
   ```python
   # Use domain enums as single source of truth
   # Remove enum definitions from models.py
   from app.ingestion.domain.enums import JobStatus, QueueStatus, PhaseStatus
   
   class IngestionJob(Base):
       status = Column(Enum(JobStatus), nullable=False)
   ```

2. **Consistent Naming** 🟢
   ```python
   # Rename for clarity
   IngestionQueueItem -> IngestionQueueEntry
   ```

---

## Module 4: Router Layer

### 4.1 Ingestion V2 Router (routers/ingestion_v2.py) - 🟡 P1

**Current Issues:**
- **Global State**: `_running_tasks` dictionary at module level
- **Mixed Concerns**: Task management, API routes, cleanup all in one file
- **Long File**: 428 lines
- **Function in Router**: `run_orchestrator_background` should be in service layer

**Refactoring Plan:**

1. **Extract Task Manager** 🟡
   ```python
   # application/task_manager.py
   class IngestionTaskManager:
       """Manage running ingestion tasks"""
       
       def __init__(self):
           self._running_tasks: Dict[str, asyncio.Task] = {}
           self._lock = asyncio.Lock()
       
       async def start_task(
           self,
           job_id: str,
           kb_id: str,
           kb_config: Dict[str, Any],
           orchestrator_factory: Callable
       ) -> asyncio.Task:
           """Start new ingestion task"""
           async with self._lock:
               if job_id in self._running_tasks:
                   raise ValueError(f"Task already running for job {job_id}")
               
               task = asyncio.create_task(
                   self._run_orchestrator(job_id, kb_id, kb_config, orchestrator_factory)
               )
               task.set_name(f"ingestion-{kb_id}-{job_id}")
               self._running_tasks[job_id] = task
               return task
       
       async def cancel_task(self, job_id: str) -> None:
           """Cancel running task"""
           async with self._lock:
               task = self._running_tasks.get(job_id)
               if task and not task.done():
                   task.cancel()
       
       async def cleanup_all_tasks(self, timeout: float = 5.0) -> None:
           """Cleanup all running tasks with timeout"""
           # Move cleanup_running_tasks logic here
       
       def is_task_running(self, job_id: str) -> bool:
           """Check if task is currently running"""
           task = self._running_tasks.get(job_id)
           return task is not None and not task.done()
   ```

2. **Simplify Router** 🟡
   ```python
   # routers/ingestion_v2.py
   class IngestionRouter:
       """API routes for ingestion operations"""
       
       def __init__(
           self,
           task_manager: IngestionTaskManager,
           job_repository: IngestionJobRepository,
           kb_manager: KBManager
       ):
           self.task_manager = task_manager
           self.job_repo = job_repository
           self.kb_manager = kb_manager
       
       @router.post("/kb/{kb_id}/start")
       async def start_ingestion(self, kb_id: str) -> JobStatusResponse:
           # Much simpler - delegate to task_manager
       
       @router.post("/kb/{kb_id}/pause")
       async def pause_ingestion(self, kb_id: str) -> dict:
           # Delegate to task_manager
   ```

3. **Move Background Runner to Service Layer** 🟡
   ```python
   # application/ingestion_executor.py
   class IngestionExecutor:
       """Execute ingestion orchestrator in background"""
       
       def __init__(
           self,
           job_repo: IngestionJobRepository,
           orchestrator_factory: Callable
       ):
           self.job_repo = job_repo
           self.orchestrator_factory = orchestrator_factory
       
       async def execute_ingestion(
           self,
           job_id: str,
           kb_id: str,
           kb_config: Dict[str, Any]
       ) -> None:
           """Run orchestrator with error handling"""
           try:
               orchestrator = self.orchestrator_factory()
               await orchestrator.run(job_id, kb_id, kb_config)
           except asyncio.CancelledError:
               logger.warning(f"Orchestrator cancelled for job {job_id}")
               self.job_repo.update_job_status(job_id, status='paused')
               raise
           except Exception as e:
               logger.exception(f"Orchestrator failed for job {job_id}")
               self.job_repo.update_job_status(job_id, status='failed', error=str(e))
   ```

---

## Module 5: Cross-Cutting Concerns

### 5.1 Error Handling - 🟡 P1

**Current Issues:**
- Inconsistent error handling across modules
- Generic `Exception` catches without specific handling
- Error messages not standardized

**Refactoring Plan:**

1. **Define Domain Exceptions** 🟡
   ```python
   # domain/exceptions.py
   class IngestionError(Exception):
       """Base exception for ingestion errors"""
       pass
   
   class JobNotFoundError(IngestionError):
       """Job not found in database"""
       pass
   
   class JobAlreadyRunningError(IngestionError):
       """Attempt to start job that's already running"""
       pass
   
   class ChunkProcessingError(IngestionError):
       """Error processing individual chunk"""
       def __init__(self, chunk_id: str, original_error: Exception):
           self.chunk_id = chunk_id
           self.original_error = original_error
           super().__init__(f"Failed to process chunk {chunk_id}: {original_error}")
   
   class SourceHandlerError(IngestionError):
       """Error from source handler"""
       pass
   
   class CheckpointError(IngestionError):
       """Error saving/loading checkpoint"""
       pass
   ```

2. **Standardize Error Responses** 🟡
   ```python
   # routers/error_handlers.py
   @router.exception_handler(JobNotFoundError)
   async def job_not_found_handler(request: Request, exc: JobNotFoundError):
       return JSONResponse(
           status_code=404,
           content={
               "error": "job_not_found",
               "message": str(exc),
               "job_id": getattr(exc, 'job_id', None)
           }
       )
   ```

---

### 5.2 Logging - 🟢 P2

**Current Issues:**
- Inconsistent logging levels
- Too much debug logging in production paths
- Emoji usage inconsistent (✅, ⚠️, ✗ mixed with text)

**Refactoring Plan:**

1. **Standardize Log Format** 🟢
   ```python
   # observability/logging_config.py
   class IngestionLogger:
       """Standardized logging for ingestion operations"""
       
       @staticmethod
       def log_job_started(job_id: str, kb_id: str) -> None:
           logger.info(f"[JOB_START] job_id={job_id} kb_id={kb_id}")
       
       @staticmethod
       def log_batch_processed(job_id: str, batch_id: int, chunks_count: int) -> None:
           logger.info(f"[BATCH_COMPLETE] job_id={job_id} batch={batch_id} chunks={chunks_count}")
       
       @staticmethod
       def log_job_paused(job_id: str, reason: str) -> None:
           logger.warning(f"[JOB_PAUSED] job_id={job_id} reason={reason}")
   ```

2. **Remove Production Debug Logs** 🟢
   - Remove excessive per-URL crawl logs
   - Remove per-chunk processing logs
   - Keep only batch-level and job-level logs in production

---

### 5.3 Configuration - 🟡 P1

**Current Issues:**
- Hard-coded values scattered throughout (timeouts, batch sizes, retry counts)
- No central configuration management

**Refactoring Plan:**

1. **Central Configuration** 🟡
   ```python
   # config/ingestion_settings.py
   @dataclass
   class IngestionSettings:
       # Batch Processing
       default_batch_size: int = 10
       max_batch_size: int = 50
       
       # Retry Policy
       max_retry_attempts: int = 3
       retry_backoff_multiplier: float = 2.0
       
       # Timeouts
       http_timeout_seconds: int = 15
       task_shutdown_timeout_seconds: float = 5.0
       
       # Crawler
       crawler_rate_limit_delay: float = 0.5
       crawler_max_pages: int = 1000
       crawler_checkpoint_interval: int = 50
       
       # Embedding
       embedding_batch_size: int = 100
       
       @classmethod
       def from_env(cls) -> 'IngestionSettings':
           """Load from environment variables"""
           return cls(
               default_batch_size=int(os.getenv('INGESTION_BATCH_SIZE', '10')),
               max_retry_attempts=int(os.getenv('INGESTION_MAX_RETRIES', '3')),
               # ...
           )
   ```

---

## Implementation Roadmap

### Phase 1: Critical Cleanup (Week 1) - 🔴 P0

**Goal**: Remove technical debt and split large files

1. Archive deprecated producer/consumer files
2. Split Repository into 4 specialized repositories
3. Extract CheckpointManager from Orchestrator
4. Extract ShutdownManager from Orchestrator
5. Verify all tests pass

**Success Criteria**:
- No deprecated code in active codebase
- All repository files <250 lines
- Tests pass

---

### Phase 2: Orchestrator Refactoring (Week 2) - 🟡 P1

**Goal**: Apply SRP to orchestrator

1. Extract ChunkProcessor
2. Extract BatchProcessor
3. Refactor IngestionCoordinator
4. Extract TaskManager from router
5. Update tests

**Success Criteria**:
- Each orchestrator component <200 lines
- Clear separation of concerns
- Tests pass

---

### Phase 3: Domain Improvements (Week 3) - 🟡 P1

**Goal**: Improve domain layer

1. Refactor loader with DocumentValidator
2. Refactor chunking adapter
3. Split website crawler
4. Standardize naming conventions
5. Update tests

**Success Criteria**:
- All domain files <250 lines
- Consistent naming
- Tests pass

---

### Phase 4: Polish & Documentation (Week 4) - 🟢 P2

**Goal**: Final improvements

1. Consolidate configuration
2. Standardize logging
3. Update architecture documentation
4. Add migration guide
5. Code review and cleanup

**Success Criteria**:
- Configuration centralized
- Documentation updated
- Code review passed

---

## Metrics & Success Criteria

### Code Quality Metrics

**Before Refactoring:**
- Average file size: ~250 lines
- Largest files: 739 (repository), 482 (orchestrator), 428 (router), 346 (crawler)
- Deprecated code: 40+ instances
- Classes with >5 responsibilities: 4 (Repository, Orchestrator, Crawler, Router)
- Test coverage: ~65%

**After Refactoring Goals:**
- Average file size: <150 lines
- No file >250 lines
- Deprecated code: 0
- Classes with >3 responsibilities: 0
- Test coverage: >80%

### Maintainability Metrics

- **Cyclomatic Complexity**: Target <10 per method
- **Code Duplication**: Target <3% (currently ~8%)
- **SOLID Principles**: All classes pass SRP check

---

## Risk Mitigation

### Risks

1. **Breaking Changes**: Refactoring may break existing code
   - Mitigation: Comprehensive test suite, incremental changes, feature flags
   
2. **Team Velocity**: Refactoring may slow feature development
   - Mitigation: Phased approach, pair programming, dedicated refactoring time
   
3. **Knowledge Transfer**: New structure may confuse team
   - Mitigation: Documentation, architecture diagrams, code walkthroughs

---

## Appendix A: File Size Analysis

```
Backend Ingestion File Sizes (lines):
├── 739: infrastructure/repository.py           [🔴 CRITICAL]
├── 482: application/orchestrator.py            [🔴 CRITICAL]
├── 428: routers/ingestion_v2.py                [🟡 HIGH]
├── 346: domain/sources/website/crawler.py      [🟡 HIGH]
├── 144: domain/loading/loader.py               [🟢 OK]
├── 133: domain/chunking/adapter.py             [🟢 OK]
├── 103: application/status_query_service.py    [🟢 OK]
└── ...

Deprecated Files (to be removed):
├── 450: application/consumer_pipeline.py       [🔴 REMOVE]
├── 380: application/producer_pipeline.py       [🔴 REMOVE]
├── 350: application/ingestion_service.py       [🔴 REMOVE]
└── ...
```

---

## Appendix B: Naming Conventions

### Current Inconsistencies

| Current Name | Issue | Proposed Name |
|--------------|-------|---------------|
| `fetch_batches` | Not clear it's generator | `stream_document_batches` |
| `chunk_documents_to_chunks` | Redundant | `create_chunks_from_documents` |
| `get_latest_job` | Ambiguous return type | `get_latest_job_for_kb` |
| `run_orchestrator_background` | Location (router) | Move to `IngestionExecutor.execute` |
| `_running_tasks` | Global state | `IngestionTaskManager._tasks` |
| `_shutdown_event` | Global state | `ShutdownManager._shutdown_event` |

### Proposed Conventions

- **Generators**: Prefix with `stream_` or `yield_`
- **Converters**: Use `create_X_from_Y` or `convert_X_to_Y`
- **Query Methods**: `get_X_for_Y` or `find_X_by_Y`
- **Boolean Methods**: `is_X`, `has_Y`, `should_Z`
- **Private State**: Never module-level, always instance variable

---

## Conclusion

This refactoring plan addresses critical technical debt while improving code maintainability, testability, and adherence to SOLID principles. The phased approach allows for incremental improvements without disrupting ongoing development.

**Estimated Effort**: 4 weeks (1 developer)  
**Expected Benefits**: 
- 50% reduction in average file size
- 30% increase in test coverage
- Elimination of all deprecated code
- Improved onboarding experience for new developers

**Next Steps**:
1. Review plan with team
2. Create GitHub issues for each phase
3. Set up branch protection for refactoring work
4. Begin Phase 1 implementation
