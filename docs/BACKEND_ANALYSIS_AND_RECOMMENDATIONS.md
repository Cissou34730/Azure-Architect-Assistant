# Backend Architecture Analysis & Recommendations

**Date**: November 27, 2025  
**Scope**: Python FastAPI Backend Structure, Logic, and Naming Conventions

---

## Executive Summary

After comprehensive review of the Python backend codebase, I've identified **significant structural issues** that impact maintainability, testability, and clarity. While the recent modularization of routers was a step forward, there are deeper architectural problems that need addressing.

**Key Issues**:
1. **Inconsistent service layer architecture** - Multiple patterns coexist
2. **Confused naming conventions** - Similar names for different concepts
3. **Duplicated logic across multiple locations** - RAG vs KB implementations
4. **Mixed concerns** - Business logic scattered across layers
5. **Poor dependency injection** - Global singletons everywhere
6. **Unclear module boundaries** - Overlapping responsibilities

**Severity**: 🔴 **HIGH** - These issues will compound as the codebase grows.

---

## 1. Directory Structure Issues

### Current Structure (Problematic)

```
backend/app/
├── main.py                    # Entry point
├── database.py                # DB config
├── llm_service.py            # ❌ Root-level service (should be in services/)
├── services.py               # ❌ "Service manager" singleton factory
├── routers/                  # API endpoints
│   ├── kb.py                 # ❌ Monolithic router
│   ├── query.py              # ❌ Monolithic router
│   ├── project_management/   # ✅ Modular (good)
│   │   ├── models.py
│   │   ├── operations.py
│   │   └── router.py
│   └── kb_ingestion/         # ✅ Modular (good)
│       ├── models.py
│       ├── operations.py
│       └── router.py
├── services/                 # ❌ EMPTY - should contain business logic
├── models/                   # ✅ DB models (good)
│   └── project.py
├── kb/                       # ❌ Mixed concerns
│   ├── manager.py            # Configuration loading
│   ├── service.py            # Query service
│   ├── multi_query.py        # Multi-KB orchestration
│   └── ingestion/            # Ingestion pipeline
│       ├── job_manager.py
│       ├── base.py
│       └── sources/
└── rag/                      # ❌ LEGACY - duplicate of kb/
    ├── kb_query.py           # Duplicate query logic
    ├── query_service.py      # Duplicate service
    ├── crawler.py            # Duplicate crawler
    └── indexer.py            # Duplicate indexer
```

### Problems Identified

#### Problem 1.1: Root-Level Services
**Issue**: `llm_service.py` is at app root instead of in `services/` directory.

**Why it's bad**:
- Breaks conventional structure (services should be in services/)
- Makes imports inconsistent: `from app.llm_service` vs `from app.services`
- Confuses newcomers about where to find business logic

**Impact**: Low maintainability, cognitive overhead

---

#### Problem 1.2: Empty `services/` Directory
**Issue**: There's a `services/` directory that is **completely empty**.

**Why it's bad**:
- Suggests an abandoned architectural decision
- Creates confusion about where to put new services
- Violates principle of least surprise

**Impact**: Developer confusion, inconsistent code placement

---

#### Problem 1.3: `services.py` as Singleton Factory
**Issue**: `services.py` is a "service manager" that creates global singleton instances.

```python
# Current anti-pattern
_query_service: Optional[WAFQueryService] = None
_kb_manager: Optional[KBManager] = None
_multi_query_service: Optional[MultiSourceQueryService] = None

def get_query_service() -> WAFQueryService:
    global _query_service
    if _query_service is None:
        _query_service = WAFQueryService(...)
    return _query_service
```

**Why it's bad**:
- Global mutable state makes testing difficult
- No way to mock services in tests
- Tight coupling between components
- No lifecycle management beyond "create once"
- Cannot easily swap implementations
- Breaks dependency injection principles

**Impact**: High - Makes testing nearly impossible, tight coupling

---

#### Problem 1.4: Duplicate RAG and KB Logic
**Issue**: Both `rag/` and `kb/` directories contain overlapping functionality.

**Duplicates**:
- `rag/kb_query.py` vs `kb/service.py` - Both query knowledge bases
- `rag/crawler.py` vs `kb/ingestion/sources/web_*.py` - Both crawl web content
- `rag/indexer.py` vs `kb/ingestion/sources/web_indexer.py` - Both build indices
- `rag/query_service.py` vs `kb/multi_query.py` - Both orchestrate queries

**Why it's bad**:
- Maintenance nightmare - bug fixes needed in two places
- Unclear which implementation is "correct"
- Code bloat - 2x the code for same functionality
- Different implementations may behave differently
- Wastes developer time deciding which to use/modify

**Impact**: Critical - Technical debt, confusion, maintenance burden

---

#### Problem 1.5: Inconsistent Router Modularity
**Issue**: Some routers are modular, others monolithic.

**Modular** (Good):
- `project_management/` - models, operations, router separated
- `kb_ingestion/` - models, operations, router separated

**Monolithic** (Bad):
- `kb.py` - 114 lines, mixed concerns
- `query.py` - 207 lines, mixed concerns
- Legacy files still present (`_projects_old.py`, `_kb_ingestion_old.py`)

**Why it's bad**:
- Inconsistent patterns confuse developers
- Harder to test monolithic files
- Business logic mixed with routing logic
- Cannot reuse operations outside HTTP context

**Impact**: Medium - Inconsistency, harder testing

---

## 2. Naming Issues

### Problem 2.1: Service Class Naming Confusion

**Multiple "Service" classes with unclear distinctions**:

```python
LLMService                    # In llm_service.py (root)
KnowledgeBaseService          # In kb/service.py
MultiSourceQueryService       # In kb/multi_query.py
KnowledgeBaseQueryService     # In rag/kb_query.py (LEGACY)
WAFQueryService               # In rag/kb_query.py (LEGACY)
ProjectService                # In routers/project_management/operations.py
KBIngestionService            # In routers/kb_ingestion/operations.py
```

**Problems**:
1. **"Service" suffix overused** - 7 different classes ending in "Service"
2. **Similar names, different purposes**:
   - `KnowledgeBaseService` (single KB queries)
   - `KnowledgeBaseQueryService` (legacy single KB queries)
   - `MultiSourceQueryService` (multi-KB orchestration)
3. **Unclear hierarchy** - Are these subclasses? Replacements? Different concerns?
4. **No pattern** - Some in `services/`, some in modules, some at root

**Recommendation**: Establish clear naming convention:
- `*Repository` for data access (DB operations)
- `*Service` for business logic orchestration
- `*Manager` for configuration/lifecycle management
- `*Client` for external API wrappers (OpenAI, etc.)
- `*Engine` for computational logic (embeddings, indexing)

---

### Problem 2.2: Ambiguous Module Names

**Confusing module names**:

| Module | What developers expect | What it actually contains |
|--------|------------------------|---------------------------|
| `services.py` | Business logic services | Singleton factory functions |
| `services/` | Business logic services | Empty directory |
| `kb/` | Knowledge base domain | Queries, ingestion, config, jobs - everything |
| `rag/` | RAG implementation | Legacy duplicate of kb/ |
| `llm_service.py` | LLM service | Actually at root, not in services/ |

**Why it's bad**:
- Developer surprise - files don't contain what names suggest
- Wastes time searching for code
- Discourages proper organization

---

### Problem 2.3: Function Naming Inconsistencies

**Getter functions use multiple patterns**:

```python
# Pattern 1: get_* factory (services.py)
get_query_service()
get_kb_manager()
get_multi_query_service()

# Pattern 2: get_* constructor (llm_service.py)
get_openai_client()
get_llm_service()

# Pattern 3: instance method (routers)
get_job_manager()  # Returns singleton
```

**Issues**:
- `get_*` could mean "create new instance" or "return singleton"
- No way to distinguish without reading implementation
- Inconsistent with Python conventions (prefer factories to be classes)

**Recommendation**: Use clear naming:
- Singletons: `instance()` or class method `YourClass.instance()`
- Factories: `create_*()` or `build_*()`
- Getters: `get_*()` only for retrieving existing data

---

## 3. Architectural Issues

### Problem 3.1: No Dependency Injection

**Current pattern**: Global singletons everywhere

```python
# In routers
from app.services import get_kb_manager, get_multi_query_service

async def endpoint():
    service = get_multi_query_service()  # Gets global singleton
    result = service.query(...)
```

**Why it's bad**:
- Cannot inject mocks for testing
- Cannot override implementations
- Tight coupling to concrete classes
- No inversion of control
- Difficult to test in isolation

**Better approach**: FastAPI dependency injection

```python
# Proposed
from fastapi import Depends

async def get_query_service() -> MultiSourceQueryService:
    """FastAPI dependency that creates/returns service"""
    return MultiSourceQueryService(...)

@router.post("/query")
async def query(
    request: QueryRequest,
    service: MultiSourceQueryService = Depends(get_query_service)
):
    return service.query(...)
```

**Benefits**:
- Can override dependencies in tests
- Explicit dependencies in function signatures
- Framework-native pattern
- Supports lifecycle management (startup/shutdown)

---

### Problem 3.2: Scattered Business Logic

**Business logic exists in multiple layers**:

1. **Routers** (`kb.py`, `query.py`):
   ```python
   @router.get("/health")
   async def check_kb_health():
       service = get_multi_query_service()  # ← Gets singleton
       health_dict = service.get_kb_health()  # ← Calls service
       # 20+ lines of transformation logic HERE in router
       kb_health = []
       for kb_id, kb_info in health_dict.items():  # ← Business logic
           # ... more logic ...
   ```

2. **Services** (`kb/service.py`, `kb/multi_query.py`):
   - Actual business logic

3. **Operations modules** (`routers/*/operations.py`):
   - More business logic

4. **Root-level files** (`llm_service.py`):
   - Even more business logic

**Why it's bad**:
- No single source of truth
- Logic duplication
- Cannot reuse logic outside HTTP context
- Hard to test business logic independently

**Recommendation**: Strict layering:
- **Routers**: HTTP request/response only, validation, error handling
- **Services**: Business logic orchestration
- **Repositories**: Data access
- **Domain**: Pure business logic, no dependencies

---

### Problem 3.3: No Clear Domain Layer

**Missing domain models and logic**:

Currently:
- `models/` contains SQLAlchemy ORM models (infrastructure concern)
- `routers/*/models.py` contains Pydantic request/response models (API concern)
- **No domain models** representing business concepts

**What's missing**:
```python
# Should exist: domain/knowledge_base.py
class KnowledgeBase:
    """Domain model - pure business logic"""
    def __init__(self, id: str, name: str, ...):
        self.id = id
        self.name = name
    
    def is_ready_for_queries(self) -> bool:
        """Business rule"""
        return self.status == 'indexed' and self.has_embeddings
    
    def supports_profile(self, profile: QueryProfile) -> bool:
        """Business rule"""
        return profile in self.profiles
```

**Why it's bad**:
- Business rules scattered across service methods
- No reusable domain logic
- Anemic domain model (data holders with no behavior)
- Tight coupling to infrastructure (DB, HTTP)

---

### Problem 3.4: Mixed Abstraction Levels

**Example from `kb/manager.py`**:

```python
class KBManager:
    def _load_config(self):
        """Load KB configurations"""  # ← Configuration concern
    
    def get_kb(self, kb_id: str):
        """Get KB config"""  # ← Configuration concern
    
    def delete_kb(self, kb_id: str):
        """Delete a knowledge base"""  # ← Operation concern
        # Contains file system operations, job cancellation, etc.
```

**Why it's bad**:
- `KBManager` is supposed to manage **configuration**
- But it also performs **operations** (delete, cancel jobs)
- Violates Single Responsibility Principle
- Makes testing harder (must mock file system for config tests)

**Recommendation**: Split into:
- `KBConfigRepository` - loads/saves configuration
- `KBService` - business operations (create, delete, query)
- `KBLifecycleManager` - startup/shutdown, caching

---

## 4. Code Quality Issues

### Problem 4.1: Inconsistent Error Handling

**Multiple error handling patterns**:

```python
# Pattern 1: Raise ValueError (operations.py)
if not project:
    raise ValueError("Project not found")

# Pattern 2: Raise HTTPException (routers)
if not kb:
    raise HTTPException(status_code=404, detail="KB not found")

# Pattern 3: Return error dict (legacy)
return {"error": "Something went wrong"}

# Pattern 4: Log and raise generic Exception
except Exception as e:
    logger.error(f"Failed: {e}")
    raise
```

**Why it's bad**:
- Inconsistent error responses
- Business logic layer shouldn't know about HTTP
- Generic exceptions lose error context
- No custom exception hierarchy

**Recommendation**: Define domain exceptions:

```python
# domain/exceptions.py
class DomainException(Exception):
    """Base for all domain exceptions"""
    pass

class ResourceNotFoundError(DomainException):
    """Resource doesn't exist"""
    pass

class ValidationError(DomainException):
    """Invalid input"""
    pass

# In routers, map to HTTP
@app.exception_handler(ResourceNotFoundError)
async def handle_not_found(request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})
```

---

### Problem 4.2: Inadequate Type Hints

**Many functions lack proper type hints**:

```python
# Current - weak typing
def query(self, question, top_k=5, metadata_filters=None):
    ...

# Better
def query(
    self,
    question: str,
    top_k: int = 5,
    metadata_filters: Optional[Dict[str, Any]] = None
) -> QueryResult:
    ...
```

**Issues**:
- Hard to understand function contracts
- No IDE autocomplete
- Runtime type errors not caught early
- Harder to refactor safely

---

### Problem 4.3: Long Functions

**Several functions exceed 50 lines**:

- `LLMService.analyze_documents()` - 80+ lines
- `ProjectService.process_chat_message()` - 100+ lines
- `KBIngestionService.run_ingestion_pipeline()` - 150+ lines

**Why it's bad**:
- Hard to understand what function does
- Hard to test (many code paths)
- Difficult to reuse sub-logic
- Violates Single Responsibility Principle

**Recommendation**: Extract sub-methods, apply command pattern

---

## 5. Testing Concerns

### Problem 5.1: Untestable Design

**Current architecture makes testing extremely difficult**:

1. **Global singletons** - Cannot inject mocks
2. **Tight coupling** - Services depend on other services directly
3. **Side effects** - Services modify global state
4. **External dependencies** - Direct OpenAI API calls in business logic
5. **No interfaces** - Concrete classes everywhere

**Example - impossible to unit test**:

```python
# This function is untestable in isolation
async def endpoint():
    service = get_multi_query_service()  # ← Global singleton
    llm = get_llm_service()               # ← Another global
    result = service.query(...)            # ← Calls OpenAI
    # How do you test this without:
    # - Real OpenAI API key
    # - Real KB indices
    # - Actual network calls
```

---

### Problem 5.2: Missing Test Infrastructure

**Current state**:
- ✅ One test file exists: `backend/test_ingestion_api.py`
- ❌ No unit tests
- ❌ No integration tests
- ❌ No test fixtures
- ❌ No test utilities
- ❌ No mocking infrastructure

**Impact**: Cannot refactor safely, regressions inevitable

---

## 6. Documentation Issues

### Problem 6.1: Inconsistent Docstrings

**Multiple docstring styles**:

```python
# Style 1: One-liner
def query(self, question: str):
    """Query the knowledge base."""

# Style 2: Google style
def analyze(self, documents: List[str]) -> Dict:
    """
    Analyze documents.
    
    Args:
        documents: List of documents
        
    Returns:
        Analysis results
    """

# Style 3: No docstring
def _internal_method(self):
    # Just code
    pass
```

**Recommendation**: Adopt PEP 257 + Google style consistently

---

### Problem 6.2: Missing Architecture Documentation

**Documentation exists**:
- ✅ README.md - User-facing
- ✅ Various docs in `docs/`

**Documentation missing**:
- ❌ Service dependency graph
- ❌ Data flow diagrams
- ❌ API architecture decision records (ADRs)
- ❌ Testing strategy
- ❌ Deployment guide
- ❌ Contributing guidelines

---

## Recommendations Summary

### 🔴 Critical (Do Immediately)

1. **Eliminate duplicate RAG/KB code**
   - Choose one implementation (kb/ is newer, keep that)
   - Delete `rag/` directory entirely
   - Update imports

2. **Implement proper dependency injection**
   - Replace `services.py` singleton factory with FastAPI dependencies
   - Make services injectable

3. **Standardize router structure**
   - Refactor `kb.py` and `query.py` to modular structure
   - Consistent with `project_management/` and `kb_ingestion/`

4. **Move services to services/ directory**
   - Move `llm_service.py` → `services/llm_service.py`
   - Delete empty `services/` directory or populate it

---

### 🟡 High Priority (Next Sprint)

5. **Define domain layer**
   - Create `domain/` directory
   - Extract business logic from services
   - Create domain models with behavior

6. **Establish naming conventions**
   - Rename service classes consistently
   - Document naming patterns in ADR

7. **Create exception hierarchy**
   - Define domain exceptions
   - Map to HTTP status codes in routers
   - Remove HTTPException from business logic

8. **Add comprehensive type hints**
   - Type all function signatures
   - Use `mypy` for static type checking

---

### 🟢 Medium Priority (Future)

9. **Split KBManager responsibilities**
   - Configuration → `KBConfigRepository`
   - Operations → `KBService`
   - Lifecycle → `KBLifecycleManager`

10. **Extract reusable patterns**
    - Create base classes for common patterns
    - Reduce code duplication

11. **Add test infrastructure**
    - Set up pytest with fixtures
    - Create mock factories
    - Add test configuration

12. **Improve documentation**
    - Architecture Decision Records
    - Service dependency diagrams
    - API documentation with examples

---

## Proposed Refactored Structure

```
backend/app/
├── main.py                          # Entry point, wires dependencies
├── config/                          # Configuration
│   ├── __init__.py
│   ├── settings.py                  # Pydantic settings
│   └── database.py                  # DB configuration
├── domain/                          # Business logic (pure Python)
│   ├── __init__.py
│   ├── knowledge_base/
│   │   ├── __init__.py
│   │   ├── entities.py              # KnowledgeBase, Query, Result
│   │   ├── value_objects.py         # QueryProfile, SourceType
│   │   ├── services.py              # Domain services (no infra deps)
│   │   └── exceptions.py            # Domain-specific exceptions
│   └── project/
│       ├── __init__.py
│       ├── entities.py              # Project, Conversation
│       ├── services.py
│       └── exceptions.py
├── services/                        # Application services (orchestration)
│   ├── __init__.py
│   ├── knowledge_base_service.py    # KB operations
│   ├── project_service.py           # Project operations
│   ├── llm_service.py               # LLM client wrapper
│   └── ingestion_service.py         # Ingestion orchestration
├── repositories/                    # Data access layer
│   ├── __init__.py
│   ├── project_repository.py        # SQLAlchemy operations
│   └── kb_config_repository.py      # Config file operations
├── infrastructure/                  # External dependencies
│   ├── __init__.py
│   ├── openai_client.py            # OpenAI API wrapper
│   ├── llama_index_engine.py       # LlamaIndex wrapper
│   └── file_storage.py             # File operations
├── api/                            # HTTP layer
│   ├── __init__.py
│   ├── dependencies.py             # FastAPI dependencies
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── knowledge_base.py       # KB endpoints
│   │   ├── projects.py             # Project endpoints
│   │   └── queries.py              # Query endpoints
│   ├── models/                     # Pydantic request/response
│   │   ├── __init__.py
│   │   ├── knowledge_base.py
│   │   └── projects.py
│   └── exception_handlers.py       # HTTP error mapping
├── models/                         # SQLAlchemy ORM models
│   ├── __init__.py
│   └── project.py
└── tests/                          # Test suite
    ├── unit/
    ├── integration/
    └── fixtures/
```

---

## Migration Strategy

### Phase 1: Foundation (Week 1)
1. Create new directory structure
2. Move `llm_service.py` to `services/`
3. Delete `rag/` directory
4. Update all imports

### Phase 2: Service Layer (Week 2)
5. Replace singleton factory with DI
6. Refactor `kb.py` and `query.py` to modular structure
7. Extract business logic to service classes

### Phase 3: Domain Layer (Week 3)
8. Create domain entities
9. Extract business rules from services
10. Define exception hierarchy

### Phase 4: Testing (Week 4)
11. Add test infrastructure
12. Write unit tests for domain layer
13. Write integration tests for API

---

## Conclusion

The current backend architecture has **significant technical debt** that will impede future development. The issues are systemic and require refactoring, but the codebase is still small enough to refactor safely.

**Key takeaway**: The recent modularization of routers (`project_management/`, `kb_ingestion/`) was a good step, but **only scratches the surface**. We need to:

1. ✅ **Eliminate duplication** (rag/ vs kb/)
2. ✅ **Establish clear layers** (domain, services, repositories, API)
3. ✅ **Use dependency injection** (FastAPI native)
4. ✅ **Consistent naming and patterns**
5. ✅ **Make code testable**

These changes will:
- ✅ Reduce cognitive overhead
- ✅ Improve maintainability
- ✅ Enable safe refactoring
- ✅ Support testing
- ✅ Facilitate onboarding new developers

**Recommendation**: Start with Phase 1 (foundation) immediately. The longer we wait, the more expensive refactoring becomes.

---

## Appendix: Code Metrics

**Current state**:
- Total Python files: ~49
- Total lines of code: ~8,500
- Services with "Service" suffix: 7
- Duplicate implementations: rag/ + kb/ (4+ classes)
- Test coverage: <5%
- Modular routers: 2/4 (50%)
- Global singletons: 3+

**Target state** (after refactoring):
- Test coverage: >80%
- Modular routers: 100%
- Global singletons: 0
- Duplicate implementations: 0
- Clear separation of concerns: ✅

---

**Questions?** Let's discuss priorities and timeline for implementing these recommendations.
