# KB Service Refactoring Plan - Option 2: Hybrid Services Pattern

## 🎯 Overview

**Goal:** Reorganize the codebase to separate query operations (services) from configuration management (kb), creating architectural consistency where services provide capabilities and the kb module manages state.

**Approach:** Move query logic from `kb/` to `services/kb/` while keeping configuration management in `kb/`, establishing clear boundaries between "what can I do?" and "what do I manage?".

---

## STEP 1: Create New Service Structure

Create the foundation for KB query services in the services directory.

### 1.1 Create service directory structure
Create `backend/app/services/kb/` directory to house query services.

### 1.2 Create query service module
Create `services/kb/query_service.py` that will merge functionality from both `kb/service.py` (single KB queries) and `kb/multi_query.py` (multi-KB orchestration).

### 1.3 Create service package initialization
Create `services/kb/__init__.py` to export the query service classes and expose clean public API.

---

## STEP 2: Extract Models from KB Module

Separate domain models from business logic to improve cohesion.

### 2.1 Create models module
Create `kb/models.py` to house domain models extracted from various KB files:
- `QueryProfile` enum (currently in `multi_query.py`)
- `KBConfig` class (currently in `knowledge_base_manager.py`)

### 2.2 Refactor KB manager
Update `kb/knowledge_base_manager.py` to import models from the new `models.py` instead of defining them inline.

### 2.3 Rename KB manager file
Rename `kb/knowledge_base_manager.py` to `kb/manager.py` for brevity and clarity.

### 2.4 Update KB package exports
Update `kb/__init__.py` to export only management-related classes:
- Remove service exports (`KnowledgeBaseService`, `MultiSourceQueryService`)
- Keep management exports (`KBManager`)
- Add model exports (`KBConfig`, `QueryProfile`)

---

## STEP 3: Move Query Logic to Services

Transfer all query execution logic from kb module to services module.

### 3.1 Migrate single KB query service
Copy content from `kb/service.py` to `services/kb/query_service.py`:
- Rename class from `KnowledgeBaseService` to `KBQueryService`
- Update imports to reference `app.kb.models` for `KBConfig`
- Keep all query execution logic, index loading, and LLM integration

### 3.2 Migrate multi-KB query service
Copy content from `kb/multi_query.py` and append to `services/kb/query_service.py`:
- Rename class from `MultiSourceQueryService` to `MultiKBQueryService`
- Update internal references to use `KBQueryService` instead of `KnowledgeBaseService`
- Update imports to reference `app.kb` for `KBManager` and `app.kb.models` for types

### 3.3 Update cross-references
Ensure `MultiKBQueryService` correctly instantiates `KBQueryService` instances for each KB.

### 3.4 Move utility functions
Move helper functions like `clear_index_cache()` to the service module.

---

## STEP 4: Update Service Registry

Modify the centralized service registry to use new service types.

### 4.1 Update imports
Change imports from `app.kb` to `app.services.kb` for query services.

### 4.2 Update type annotations
Change return types and variable types from `MultiSourceQueryService` to `MultiKBQueryService`.

### 4.3 Update instantiation
Ensure the registry creates instances of the new `MultiKBQueryService` class.

---

## STEP 5: Update All Router Imports

Systematically update all routers to use the new service locations.

### 5.1 Update query router
Modify `routers/kb_query/query_router.py`:
- Change imports from `app.kb` to `app.services.kb`
- Update type hints for dependency injection functions
- Keep endpoint logic unchanged

### 5.2 Update query operations
Modify `routers/kb_query/query_operations.py`:
- Change imports from `app.kb` to `app.services.kb`
- Update type hints in method signatures
- Keep business logic unchanged

### 5.3 Update management router
Modify `routers/kb_management/management_router.py`:
- Update imports for query services
- Update imports for cache management functions
- Keep KB manager imports pointing to `app.kb`

### 5.4 Update project management router
Modify `routers/project_management/project_operations.py`:
- Update `QueryProfile` import from `app.kb.multi_query` to `app.services.kb`
- Keep service registry usage unchanged

---

## STEP 6: Update Tests

Ensure all test files reflect the new structure.

### 6.1 Locate test files
Identify all test files that import KB-related classes in:
- `backend/tests/services/`
- `backend/tests/kb/`
- `backend/tests/routers/`

### 6.2 Update test imports
Replace old import paths with new ones:
- Change `app.kb.service` to `app.services.kb`
- Change `app.kb.multi_query` to `app.services.kb`
- Update class names from `KnowledgeBaseService` to `KBQueryService`
- Update class names from `MultiSourceQueryService` to `MultiKBQueryService`

### 6.3 Update test fixtures
Modify pytest fixtures that instantiate query services to use new class names and import paths.

### 6.4 Update mock configurations
Update any mock setups or patches to reference the new module paths.

---

## STEP 7: Clean Up Old Files

Remove deprecated files that have been migrated.

### 7.1 Delete old KB service files
Remove `backend/app/kb/service.py` and `backend/app/kb/multi_query.py` as their functionality is now in `services/kb/`.

### 7.2 Delete unused RAG service files
Remove empty/TODO files:
- `backend/app/services/rag/query.py`
- `backend/app/services/rag/index.py`
- If the rag directory is now empty, remove `backend/app/services/rag/` entirely

---

## STEP 8: Add Documentation

Document the architectural decisions and module purposes.

### 8.1 Create KB management README
Create `kb/README.md` explaining:
- Module purpose: configuration and lifecycle management
- What belongs here: KB configuration, status management, metadata
- What doesn't belong here: query execution, index building
- Usage examples for `KBManager`

### 8.2 Create KB service README
Create `services/kb/README.md` explaining:
- Module purpose: query execution capabilities
- What belongs here: vector search, LLM integration, multi-KB orchestration
- Usage examples for both `KBQueryService` and `MultiKBQueryService`

### 8.3 Update main README
Add architecture patterns section to `backend/README.md` or main `README.md`:
- Document when to use DDD (ingestion module)
- Document when to use Services pattern (kb queries, llm, mcp)
- Explain the hybrid approach and rationale

---

## STEP 9: Verify and Test

Ensure the refactoring hasn't broken anything.

### 9.1 Run static type checking
Execute mypy on the modified modules to catch type errors.

### 9.2 Run unit tests
Execute pytest on service and kb test suites to verify isolated functionality.

### 9.3 Run integration tests
Execute full test suite with focus on query-related tests.

### 9.4 Manual smoke test
Start the backend server and manually test query endpoints with sample requests.

---

## STEP 10: Commit Changes

Preserve the refactoring in version control with clear documentation.

### 10.1 Review all changes
Use git status and git diff to review all modified, added, and deleted files.

### 10.2 Stage changes systematically
Stage related files together:
- New service files
- Modified KB files
- Updated routers
- Updated tests
- New documentation

### 10.3 Commit with comprehensive message
Write detailed commit message explaining:
- What was changed (files moved, classes renamed)
- Why it was changed (architectural consistency)
- What the new structure achieves (clear separation of concerns)
- Confirmation that tests pass and no breaking changes

---

## 📊 Final File Structure

### Before Refactoring:
```
backend/app/
├── kb/
│   ├── knowledge_base_manager.py  ← Configuration + models
│   ├── service.py                 ← Single KB query
│   ├── multi_query.py             ← Multi KB query + QueryProfile
│   └── __init__.py
├── services/
│   ├── llm_service.py
│   ├── mcp/
│   └── rag/
│       ├── query.py               ← Empty TODO
│       └── index.py               ← Empty
└── routers/
    └── kb_query/
        ├── query_router.py        ← Imports from kb/
        └── query_operations.py    ← Imports from kb/
```

### After Refactoring:
```
backend/app/
├── kb/                            ← Configuration Management
│   ├── manager.py                 (Lifecycle & config)
│   ├── models.py                  (Domain models)
│   ├── README.md                  (Purpose & usage)
│   └── __init__.py                (Exports: KBManager, models)
│
├── services/
│   ├── llm_service.py             (Text generation)
│   ├── mcp/                       (External APIs)
│   └── kb/                        ← Query Services (NEW)
│       ├── query_service.py       (Query execution)
│       ├── README.md              (Usage examples)
│       └── __init__.py            (Exports query services)
│
├── routers/                       ← Presentation Layer
│   └── kb_query/                  (HTTP endpoints)
│       ├── query_router.py        ← Imports from services/kb/
│       └── query_operations.py    ← Imports from services/kb/
│
└── ingestion/                     ← Complex Domain (DDD)
    ├── domain/
    ├── infrastructure/
    └── application/
```

---

## 🎯 Architectural Principles

### Clear Separation:
- **Services** = Stateless operations providing capabilities
- **KB** = Stateful management of configuration
- **Ingestion** = Complex domain with DDD architecture
- **Routers** = HTTP presentation layer

### Decision Rules:
- **Complex domain with business rules?** → Use DDD (ingestion)
- **Simple CRUD or API wrapper?** → Use Services pattern (kb queries, llm, mcp)
- **Configuration and lifecycle?** → Use Management pattern (kb, projects)

### Benefits:
- ✅ Consistent architecture across modules
- ✅ Clear mental model: services provide capabilities, managers handle state
- ✅ Aligned with existing patterns (LLM service, MCP service)
- ✅ Scalable for adding new services
- ✅ Testable through clear boundaries
- ✅ Documented decision rationale

---

## ✅ Success Criteria

After completing all steps, verify:

1. ✅ All imports updated (no references to old paths)
2. ✅ All tests passing
3. ✅ No old `kb/service.py` or `kb/multi_query.py` files
4. ✅ No empty `services/rag/` TODO files
5. ✅ Clear READMEs documenting architecture decisions
6. ✅ Service registry updated with new types
7. ✅ Backend starts without errors
8. ✅ Query endpoints work correctly
9. ✅ Type checking passes (mypy)
10. ✅ Git history shows clean refactor commit
