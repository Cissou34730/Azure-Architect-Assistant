# WAF Normalization to DB - Detailed Implementation Plan

**Last Updated**: February 4, 2026  
**Status**: Ready for Implementation  
**Estimated Effort**: 2-3 weeks (split into 4 phases)

## Table of Contents
- [Overview](#overview)
- [Phase 1: Schema, Models & Migration](#phase-1-schema-models--migration)
- [Phase 2: Core Services & Engine](#phase-2-core-services--engine)
- [Phase 3: Integration & API](#phase-3-integration--api)
- [Phase 4: Backfill, Testing & Documentation](#phase-4-backfill-testing--documentation)
- [Phase 5: Deployment & Operations](#phase-5-deployment--operations)
- [Quality Standards](#quality-standards)
- [Testing Strategy](#testing-strategy)

---

## Overview

### Purpose
Transform the denormalized JSON-based WAF checklist storage in `ProjectState.state` into normalized relational tables to enable:
- Cross-project analytics
- Agent-driven evaluations with history
- Robust consistency guarantees
- Performance optimization for queries

### Architecture Principles
- **Dual-write approach**: During rollout, maintain both JSON and normalized formats
- **Idempotent operations**: All sync/backfill operations must be repeatable
- **Deterministic IDs**: Use UUID v5 for `ChecklistItem.id` to avoid duplicates
- **Feature-flagged**: `FEATURE_WAF_NORMALIZED` controls behavior
- **Template caching**: Microsoft Learn templates fetched once via MCP, cached locally

### Guardrails
- Informational, not blocking
- Percentage completion as primary signal
- Highlight uncovered critical/high items
- Architect can proceed even if incomplete, but sees risk

---

## Phase 1: Schema, Models & Migration

**Estimated Time**: 2-3 days  
**Dependencies**: None

### Task 1.1: Create SQLAlchemy Models

**File**: `backend/app/models/checklist.py` (NEW)

**What to Implement**:

```python
# Imports required:
from sqlalchemy import Column, String, Text, Enum, Integer, Float, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

# Import base from existing models
from backend.app.models.base import Base
```

**Models to Create**:

1. **ChecklistTemplate Model**
   - Fields:
     - `id`: UUID, primary_key=True, default=uuid.uuid4
     - `slug`: String(255), unique=True, nullable=False, indexed
     - `title`: String(500), nullable=False
     - `description`: Text, nullable=True
     - `version`: String(50), nullable=False
     - `source`: String(100), nullable=False (e.g., "microsoft-learn")
     - `source_url`: String(1000), nullable=False (Microsoft Learn URL)
     - `source_version`: String(100), nullable=False (doc version or fetch date)
     - `content`: JSONB, nullable=False (original template structure)
     - `created_at`: DateTime, default=datetime.utcnow, nullable=False
     - `updated_at`: DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
   - Relationships:
     - `checklists`: one-to-many with Checklist
   - Indexes:
     - `slug` (unique)
     - `(source, source_version)` composite

2. **Checklist Model**
   - Fields:
     - `id`: UUID, primary_key=True, default=uuid.uuid4
     - `project_id`: UUID, ForeignKey('projects.id'), nullable=False
     - `template_id`: UUID, ForeignKey('checklist_templates.id'), nullable=True
     - `title`: String(500), nullable=False
     - `created_by`: String(255), nullable=True
     - `status`: Enum('open', 'archived', name='checklist_status'), default='open'
     - `created_at`: DateTime, default=datetime.utcnow
     - `updated_at`: DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
   - Relationships:
     - `project`: many-to-one with Project
     - `template`: many-to-one with ChecklistTemplate
     - `items`: one-to-many with ChecklistItem
   - Indexes:
     - `project_id` (IX_checklist_project_id)
     - `(project_id, template_id)` composite unique constraint
     - `status`

3. **ChecklistItem Model**
   - Fields:
     - `id`: UUID, primary_key=True (deterministic UUID v5)
     - `checklist_id`: UUID, ForeignKey('checklists.id', ondelete='CASCADE'), nullable=False
     - `template_item_id`: String(255), nullable=False (original id from template)
     - `title`: String(1000), nullable=False
     - `description`: Text, nullable=True
     - `pillar`: String(100), nullable=True
     - `severity`: Enum('low', 'medium', 'high', 'critical', name='severity_level'), nullable=False
     - `guidance`: JSONB, nullable=True (recommended fix)
     - `metadata`: JSONB, nullable=True (tags, remediations)
     - `created_at`: DateTime, default=datetime.utcnow
     - `updated_at`: DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
   - Relationships:
     - `checklist`: many-to-one with Checklist
     - `evaluations`: one-to-many with ChecklistItemEvaluation
   - Indexes:
     - `checklist_id` (IX_item_checklist_id)
     - `severity`
     - `(checklist_id, template_item_id)` unique constraint
   - Note: Include helper method `compute_deterministic_id(project_id: UUID, template_slug: str, template_item_id: str) -> UUID` as classmethod

4. **ChecklistItemEvaluation Model**
   - Fields:
     - `id`: UUID, primary_key=True, default=uuid.uuid4
     - `item_id`: UUID, ForeignKey('checklist_items.id', ondelete='CASCADE'), nullable=False
     - `project_id`: UUID, ForeignKey('projects.id'), nullable=False
     - `evaluator`: String(255), nullable=False (tool/agent/user identifier)
     - `status`: Enum('open', 'in_progress', 'fixed', 'false_positive', name='evaluation_status'), nullable=False
     - `score`: Float, nullable=True (optional severity numeric)
     - `evidence`: JSONB, nullable=True (artifacts, citations)
     - `source_type`: String(100), nullable=False (e.g., 'agent-validation', 'manual')
     - `source_id`: String(255), nullable=True (tool run id for deduplication)
     - `created_at`: DateTime, default=datetime.utcnow
     - `updated_at`: DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
   - Relationships:
     - `item`: many-to-one with ChecklistItem
     - `project`: many-to-one with Project
   - Indexes:
     - `item_id` (IX_evaluation_item_id)
     - `project_id`
     - `(project_id, item_id, created_at)` composite (IX_evaluation_project_item)
     - `(item_id, source_type, source_id)` for deduplication queries

**Type Safety Requirements**:
- Use explicit types for all fields
- No `Any` type allowed
- Use TypedDict or Pydantic models for JSONB field structures
- Add docstrings to all models and methods

**Quality Checks**:
- [ ] All fields have explicit types
- [ ] Relationships defined with back_populates
- [ ] Foreign key constraints include ondelete rules
- [ ] Indexes match query patterns from plan
- [ ] Unique constraints prevent duplicates
- [ ] Helper method for deterministic ID generation included
- [ ] Enums defined with proper names

---

### Task 1.2: Create Alembic Migration

**File**: `backend/migrations/versions/<timestamp>_create_waf_normalized.py` (NEW)

**What to Implement**:

1. **Migration Header**:
   ```python
   """Create WAF normalized checklist tables
   
   Revision ID: <auto_generated>
   Revises: <current_head>
   Create Date: <timestamp>
   
   This migration creates normalized tables for WAF checklist management:
   - checklist_templates: Template definitions from Microsoft Learn
   - checklists: Project-specific checklist instances
   - checklist_items: Individual checklist items
   - checklist_item_evaluations: Evaluation history per item
   
   IMPORTANT: After running this migration, execute backfill:
   python scripts/backfill_waf.py --dry-run --batch-size=50
   
   Estimated runtime: ~5-10 minutes for 1000 projects
   """
   ```

2. **upgrade() function**:
   - Create enum types first:
     - `checklist_status`: ('open', 'archived')
     - `severity_level`: ('low', 'medium', 'high', 'critical')
     - `evaluation_status`: ('open', 'in_progress', 'fixed', 'false_positive')
   - Create tables in order:
     1. `checklist_templates`
     2. `checklists`
     3. `checklist_items`
     4. `checklist_item_evaluations`
   - Create indexes after table creation:
     - All indexes listed in Task 1.1
   - Add foreign key constraints with CASCADE rules

3. **downgrade() function**:
   - Drop tables in reverse order:
     1. `checklist_item_evaluations`
     2. `checklist_items`
     3. `checklists`
     4. `checklist_templates`
   - Drop enum types
   - Include warning comment: "# WARNING: This will permanently delete all checklist data"

**Quality Checks**:
- [ ] Migration runs without errors on empty database
- [ ] Migration runs without errors on database with existing schema
- [ ] downgrade() successfully reverts all changes
- [ ] All foreign key constraints include ondelete='CASCADE'
- [ ] All indexes are created
- [ ] Enum types match model definitions exactly
- [ ] Table names match SQLAlchemy model __tablename__ attributes
- [ ] Migration includes descriptive docstring with runtime estimates

---

### Task 1.3: Add Configuration Constants

**File**: `backend/app/config/settings.py` (MODIFY)

**What to Change**:

Add new configuration section:
```python
# WAF Checklist Normalization Settings
FEATURE_WAF_NORMALIZED: bool = Field(
    default=False,
    description="Enable normalized WAF checklist storage (dual-write mode)"
)

WAF_NAMESPACE_UUID: UUID = Field(
    default=UUID("3a7e8c2f-1b4d-4f5e-9c3d-2a8b7e6f1c4d"),
    description="Namespace UUID for deterministic checklist item IDs (UUID v5)"
)

WAF_TEMPLATE_CACHE_DIR: Path = Field(
    default=Path("backend/config/checklists"),
    description="Local directory for cached WAF template files"
)

WAF_BACKFILL_BATCH_SIZE: int = Field(
    default=50,
    description="Number of projects to process per backfill batch"
)

WAF_SYNC_CHUNK_SIZE: int = Field(
    default=500,
    description="Number of items to process per database transaction during sync"
)
```

**Quality Checks**:
- [ ] All new settings have explicit types
- [ ] All settings have descriptive help text
- [ ] Default values are sensible
- [ ] WAF_NAMESPACE_UUID is a fixed, documented value
- [ ] Path settings use pathlib.Path type

---

### Task 1.4: Update Database Initialization

**File**: `backend/app/db/session.py` (MODIFY)

**What to Change**:

1. Import the new models:
   ```python
   from backend.app.models.checklist import (
       ChecklistTemplate,
       Checklist,
       ChecklistItem,
       ChecklistItemEvaluation
   )
   ```

2. Ensure models are registered with SQLAlchemy metadata (usually automatic if imported before Base.metadata.create_all())

**File**: `backend/app/models/__init__.py` (MODIFY)

**What to Change**:

Add exports:
```python
from backend.app.models.checklist import (
    ChecklistTemplate,
    Checklist,
    ChecklistItem,
    ChecklistItemEvaluation
)

__all__ = [
    # ... existing exports ...
    "ChecklistTemplate",
    "Checklist",
    "ChecklistItem",
    "ChecklistItemEvaluation",
]
```

**Quality Checks**:
- [ ] New models imported in session.py
- [ ] Models exported from __init__.py
- [ ] No circular import issues
- [ ] Test database creation includes new tables

---

### Phase 1 Verification Checklist

- [ ] All 4 models created with correct fields and types
- [ ] Migration file created and reviewed
- [ ] Migration runs successfully: `alembic upgrade head`
- [ ] Migration can be reverted: `alembic downgrade -1`
- [ ] Configuration settings added and typed correctly
- [ ] Models registered in database initialization
- [ ] No linting errors (run `ruff check backend/app/models/checklist.py`)
- [ ] No type errors (run `mypy backend/app/models/checklist.py`)
- [ ] All docstrings present and descriptive

**Testing Task 1.5**: Create Basic Model Tests

**File**: `backend/tests/models/test_checklist_models.py` (NEW)

**What to Test**:
1. Model instantiation with valid data
2. Foreign key relationships work correctly
3. Unique constraints prevent duplicates
4. Deterministic ID generation produces stable UUIDs
5. Enum values constrained correctly
6. Default values applied correctly

---

## Phase 2: Core Services & Engine

**Estimated Time**: 3-5 days  
**Dependencies**: Phase 1 complete

### Task 2.1: Create Checklist Template Registry

**File**: `backend/app/agents_system/checklists/registry.py` (NEW)

**What to Implement**:

1. **ChecklistRegistry Class**:
   ```python
   from typing import Optional
   from pathlib import Path
   import json
   from backend.app.models.checklist import ChecklistTemplate
   from backend.app.config.settings import Settings
   
   class ChecklistRegistry:
       """
       Manages WAF checklist templates cached from Microsoft Learn.
       
       Templates are fetched once via MCP server and cached locally.
       No per-project fetches - registry serves from local cache.
       """
   ```

   **Methods to Implement**:

   a. `__init__(self, cache_dir: Path, settings: Settings) -> None`
      - Store cache_dir and settings
      - Initialize empty template dict: `_templates: dict[str, ChecklistTemplate]`
      - Call `_load_cached_templates()` to populate from disk

   b. `_load_cached_templates(self) -> None`
      - Scan cache_dir for JSON files
      - Parse each JSON as ChecklistTemplate
      - Validate structure (must have: slug, title, version, content)
      - Store in _templates dict keyed by slug
      - Log: number of templates loaded

   c. `get_template(self, slug: str) -> Optional[ChecklistTemplate]`
      - Return _templates.get(slug)
      - Log warning if template not found

   d. `list_templates(self) -> list[ChecklistTemplate]`
      - Return list(_templates.values())
      - Sort by slug for consistency

   e. `register_template(self, template: ChecklistTemplate) -> None`
      - Validate template has required fields
      - Store in _templates dict
      - Persist to cache_dir as JSON
      - Log: template registered

   f. `refresh_from_cache(self) -> int`
      - Clear _templates
      - Call _load_cached_templates()
      - Return count of loaded templates

2. **Template JSON Structure** (to document):
   ```json
   {
     "slug": "waf-2026-v1",
     "title": "Azure Well-Architected Framework 2026",
     "description": "...",
     "version": "2026.1.0",
     "source": "microsoft-learn",
     "source_url": "https://learn.microsoft.com/...",
     "source_version": "2026-01-15",
     "content": {
       "categories": [...],
       "items": [...]
     }
   }
   ```

**Quality Checks**:
- [ ] All methods have explicit return type annotations
- [ ] No `Any` types used
- [ ] Comprehensive docstrings for class and all methods
- [ ] Error handling for invalid JSON files
- [ ] Logging at appropriate levels (INFO for loads, WARNING for failures)
- [ ] Thread-safe if needed (document concurrency assumptions)

---

### Task 2.2: Create Normalization Helpers

**File**: `backend/app/services/normalize_helpers.py` (NEW)

**What to Implement**:

1. **Type Definitions** (using TypedDict):
   ```python
   from typing import TypedDict, Literal
   
   class WafChecklistItemDict(TypedDict):
       id: str
       title: str
       description: str
       pillar: str
       severity: Literal['low', 'medium', 'high', 'critical']
       guidance: dict
       metadata: dict
   
   class WafChecklistEvaluationDict(TypedDict):
       item_id: str
       status: Literal['open', 'in_progress', 'fixed', 'false_positive']
       evaluator: str
       evidence: dict
       source_type: str
       source_id: str | None
       timestamp: str
   ```

2. **Helper Functions**:

   a. `compute_deterministic_item_id(project_id: UUID, template_slug: str, template_item_id: str, namespace_uuid: UUID) -> UUID`
      - Use uuid.uuid5(namespace_uuid, f"{project_id}:{template_slug}:{template_item_id}")
      - Document: "Generates deterministic UUID for checklist items to ensure idempotency"
      - Return UUID

   b. `normalize_waf_item(item_dict: dict, project_id: UUID, template_slug: str, namespace_uuid: UUID) -> dict`
      - Extract fields: id, title, description, pillar, severity, guidance, metadata
      - Compute deterministic_id using compute_deterministic_item_id()
      - Return normalized dict matching ChecklistItem model fields
      - Validate severity is valid enum value
      - Handle missing optional fields gracefully

   c. `normalize_waf_evaluation(eval_dict: dict, item_id: UUID, project_id: UUID) -> dict`
      - Extract: evaluator, status, score, evidence, source_type, source_id
      - Validate status enum value
      - Return normalized dict matching ChecklistItemEvaluation model fields
      - Parse timestamp to datetime if string

   d. `denormalize_checklist_to_json(checklist: Checklist, items: list[ChecklistItem], evaluations: list[ChecklistItemEvaluation]) -> dict`
      - Reconstruct original wafChecklist JSON structure from normalized models
      - Group evaluations by item_id
      - Return dict compatible with ProjectState.state['wafChecklist'] structure
      - Document: "Used for backward compatibility and dual-write verification"

   e. `validate_normalized_consistency(original_json: dict, reconstructed_json: dict) -> tuple[bool, list[str]]`
      - Compare original and reconstructed JSON structures
      - Return (is_valid, list_of_differences)
      - Check: item counts match, IDs present, evaluations preserved
      - Used for backfill verification

**Quality Checks**:
- [ ] All functions have full type annotations
- [ ] TypedDict classes defined for complex structures
- [ ] Comprehensive docstrings with examples
- [ ] Input validation with clear error messages
- [ ] Edge cases handled (missing fields, None values)
- [ ] Unit tests written (see Phase 4)

---

### Task 2.3: Create Checklist Engine Core

**File**: `backend/app/agents_system/checklists/engine.py` (NEW)

**What to Implement**:

This is the most complex component. Break into smaller methods.

1. **ChecklistEngine Class Structure**:
   ```python
   from typing import Callable
   from sqlalchemy.ext.asyncio import AsyncSession
   from backend.app.agents_system.checklists.registry import ChecklistRegistry
   from backend.app.models.checklist import *
   from backend.app.services.normalize_helpers import *
   import structlog
   
   logger = structlog.get_logger(__name__)
   
   class ChecklistEngine:
       """
       Core engine for processing agent results and syncing checklist state.
       
       Responsibilities:
       - Process agent AAA_STATE_UPDATE with checklist evaluations
       - Sync ProjectState.state ↔ normalized DB rows
       - Compute completion metrics and next actions
       - Support dual-write mode with consistency checks
       """
   ```

2. **__init__ Method**:
   ```python
   def __init__(
       self,
       db_session_factory: Callable[[], AsyncSession],
       registry: ChecklistRegistry,
       settings: Settings
   ) -> None:
   ```
   - Store dependencies
   - Initialize feature_flag from settings.FEATURE_WAF_NORMALIZED
   - Initialize namespace_uuid from settings.WAF_NAMESPACE_UUID
   - Initialize chunk_size from settings.WAF_SYNC_CHUNK_SIZE

3. **process_agent_result Method**:
   ```python
   async def process_agent_result(
       self,
       project_id: UUID,
       agent_result: dict,
   ) -> dict:
       """
       Process agent result containing AAA_STATE_UPDATE with checklist data.
       
       Args:
           project_id: Project UUID
           agent_result: Agent output dict with potential AAA_STATE_UPDATE
           
       Returns:
           Merge summary dict with counts and status
           
       Raises:
           ValueError: If agent_result structure invalid
       """
   ```
   - Extract AAA_STATE_UPDATE from agent_result
   - Look for wafChecklist section
   - If present:
     - Begin async DB session
     - For each template in wafChecklist:
       - Get or create ChecklistTemplate
       - Get or create Checklist for project
       - For each item in template:
         - Normalize using normalize_helpers
         - Upsert ChecklistItem
       - For each evaluation in result:
         - Normalize evaluation
         - Create ChecklistItemEvaluation
     - Commit transaction
     - Return summary: {"items_processed": N, "evaluations_created": M, "checklist_id": UUID}
   - Log at each major step
   - Handle errors gracefully, rollback on failure

4. **sync_project_state_to_db Method**:
   ```python
   async def sync_project_state_to_db(
       self,
       project_id: UUID,
       project_state: dict,
       chunk_size: int | None = None
   ) -> dict:
       """
       Idempotent backfill of items and evaluations from ProjectState.
       
       Args:
           project_id: Project UUID
           project_state: ProjectState.state dict
           chunk_size: Items per transaction (default from settings)
           
       Returns:
           Summary dict with counts
       """
   ```
   - Extract wafChecklist from project_state
   - If not present, return early
   - Process in chunks (default chunk_size or parameter)
   - For each chunk:
     - Begin transaction
     - Upsert ChecklistTemplate, Checklist, ChecklistItems, Evaluations
     - Commit
   - Track total counts
   - Return summary: {"items_synced": N, "evaluations_synced": M, "errors": []}
   - Make idempotent: check existence before insert, use upsert patterns

5. **sync_db_to_project_state Method**:
   ```python
   async def sync_db_to_project_state(
       self,
       project_id: UUID
   ) -> dict:
       """
       Rebuild wafChecklist JSON from normalized rows.
       
       Used for backward compatibility and verification.
       
       Args:
           project_id: Project UUID
           
       Returns:
           wafChecklist dict structure
       """
   ```
   - Query all Checklists for project
   - For each Checklist:
     - Load related ChecklistItems
     - Load related ChecklistItemEvaluations
   - Use denormalize_checklist_to_json() helper
   - Return reconstructed JSON
   - Cache result if performance becomes issue

6. **evaluate_item Method**:
   ```python
   async def evaluate_item(
       self,
       project_id: UUID,
       item_id: UUID,
       evaluation_payload: dict
   ) -> ChecklistItemEvaluation:
       """
       Create new evaluation for checklist item.
       
       Args:
           project_id: Project UUID
           item_id: ChecklistItem UUID
           evaluation_payload: Evaluation data (status, evidence, etc.)
           
       Returns:
           Created ChecklistItemEvaluation instance
       """
   ```
   - Validate item exists and belongs to project
   - Normalize evaluation_payload
   - Create ChecklistItemEvaluation record
   - Update item metadata if needed
   - Return evaluation object

7. **list_next_actions Method**:
   ```python
   async def list_next_actions(
       self,
       project_id: UUID,
       limit: int = 20,
       severity: str | None = None
   ) -> list[dict]:
       """
       List uncovered or incomplete checklist items prioritized by severity.
       
       Args:
           project_id: Project UUID
           limit: Maximum items to return
           severity: Optional filter (critical, high, medium, low)
           
       Returns:
           List of dicts with item details and latest evaluation
       """
   ```
   - Query ChecklistItems for project
   - Filter by severity if specified
   - Left join latest ChecklistItemEvaluation
   - Filter to open/in_progress status
   - Order by severity (critical > high > medium > low), then created_at
   - Limit results
   - Return list of dicts with: item_id, title, pillar, severity, latest_status, last_evaluated

8. **compute_progress Method**:
   ```python
   async def compute_progress(
       self,
       project_id: UUID,
       checklist_id: UUID | None = None
   ) -> dict:
       """
       Calculate completion metrics for project or specific checklist.
       
       Args:
           project_id: Project UUID
           checklist_id: Optional specific checklist (default: all for project)
           
       Returns:
           Dict with: total_items, completed_items, percent_complete,
                     severity_breakdown, last_updated
       """
   ```
   - Query ChecklistItems (filtered by checklist_id if provided)
   - Count total items
   - Join latest evaluations
   - Count items with status='fixed' or 'false_positive'
   - Calculate percentage
   - Group by severity for breakdown
   - Return structured dict

**Quality Checks**:
- [ ] All methods fully typed (no Any)
- [ ] Comprehensive docstrings with Args, Returns, Raises
- [ ] Transactions used correctly (begin, commit, rollback on error)
- [ ] Idempotency guaranteed for sync operations
- [ ] Chunk processing implemented for large datasets
- [ ] Logging at INFO and ERROR levels
- [ ] Error handling with specific exceptions
- [ ] Feature flag checked where appropriate

---

### Task 2.4: Create Service Wrapper

**File**: `backend/app/agents_system/checklists/service.py` (NEW)

**What to Implement**:

1. **ChecklistService Class**:
   ```python
   from backend.app.agents_system.checklists.engine import ChecklistEngine
   from backend.app.agents_system.checklists.registry import ChecklistRegistry
   from backend.app.db.session import get_db
   from fastapi import Depends
   from sqlalchemy.ext.asyncio import AsyncSession
   
   class ChecklistService:
       """
       Service layer adapter for ChecklistEngine.
       
       Provides dependency injection and API-friendly interface.
       """
   ```

2. **Methods** (thin wrappers around engine):

   a. `__init__(self, engine: ChecklistEngine, registry: ChecklistRegistry) -> None`

   b. `async def process_agent_result(...) -> dict` - delegates to engine

   c. `async def sync_project(...) -> dict` - delegates to engine.sync_project_state_to_db

   d. `async def get_progress(...) -> dict` - delegates to engine.compute_progress

   e. `async def list_next_actions(...) -> list[dict]` - delegates to engine

   f. `async def evaluate_item(...) -> ChecklistItemEvaluation` - delegates to engine

3. **Dependency Injection Function**:
   ```python
   async def get_checklist_service(
       db: AsyncSession = Depends(get_db),
       settings: Settings = Depends(get_settings)
   ) -> ChecklistService:
       """FastAPI dependency for ChecklistService."""
       registry = ChecklistRegistry(
           cache_dir=settings.WAF_TEMPLATE_CACHE_DIR,
           settings=settings
       )
       engine = ChecklistEngine(
           db_session_factory=lambda: db,
           registry=registry,
           settings=settings
       )
       return ChecklistService(engine=engine, registry=registry)
   ```

**Quality Checks**:
- [ ] All methods properly typed
- [ ] Docstrings present
- [ ] FastAPI dependency injection pattern followed
- [ ] Service acts as thin adapter (business logic in engine)

---

### Phase 2 Verification Checklist

- [ ] ChecklistRegistry loads templates from cache correctly
- [ ] Normalization helpers produce correct output structures
- [ ] ChecklistEngine.process_agent_result creates DB records
- [ ] ChecklistEngine.sync_project_state_to_db is idempotent
- [ ] ChecklistEngine.sync_db_to_project_state reconstructs JSON correctly
- [ ] ChecklistEngine.compute_progress calculates percentages correctly
- [ ] ChecklistService wrapper functions correctly
- [ ] No linting errors: `ruff check backend/app/agents_system/checklists/`
- [ ] No type errors: `mypy backend/app/agents_system/checklists/`
- [ ] All docstrings present and accurate

---

## Phase 3: Integration & API

**Estimated Time**: 2-4 days  
**Dependencies**: Phase 2 complete

### Task 3.1: Integrate with Agent Orchestrator

**File**: `backend/app/agents_system/orchestrator/orchestrator.py` (MODIFY)

**What to Change**:

1. **Add on_end Callback Support**:

   Locate the `AgentOrchestrator` class `__init__` method:
   ```python
   def __init__(
       self,
       # ... existing params ...
   ) -> None:
   ```

   **Add parameter**:
   ```python
   on_end: Callable[[UUID, dict], Awaitable[dict]] | None = None
   ```

   **Store in instance**:
   ```python
   self._on_end_callback = on_end
   ```

2. **Call Callback After Agent Execution**:

   Locate where agent execution completes (likely in a `run` or `execute` method):
   ```python
   # After agent completes and result is available
   agent_result = await self._execute_agent(...)
   
   # NEW: Call on_end callback if registered
   if self._on_end_callback is not None:
       try:
           callback_result = await self._on_end_callback(project_id, agent_result)
           logger.info("on_end callback completed", callback_result=callback_result)
       except Exception as e:
           logger.error("on_end callback failed", error=str(e))
           # Don't fail the whole operation if callback fails
   
   return agent_result
   ```

**Quality Checks**:
- [ ] on_end parameter added with correct type annotation
- [ ] Callback invoked after agent completes
- [ ] Callback errors don't crash agent execution
- [ ] Callback result logged for debugging
- [ ] Typing remains strict (no Any)

---

### Task 3.2: Register Callback in Agent Runner

**File**: `backend/app/agents_system/runner.py` (MODIFY)

**What to Change**:

1. **Import Dependencies**:
   ```python
   from backend.app.agents_system.checklists.engine import ChecklistEngine
   from backend.app.agents_system.checklists.registry import ChecklistRegistry
   from backend.app.config.settings import get_settings
   ```

2. **Modify initialize() or startup**:

   Locate where `AgentOrchestrator` is instantiated:
   ```python
   # Existing code:
   orchestrator = AgentOrchestrator(...)
   ```

   **Add before instantiation**:
   ```python
   # Initialize checklist engine
   settings = get_settings()
   if settings.FEATURE_WAF_NORMALIZED:
       registry = ChecklistRegistry(
           cache_dir=settings.WAF_TEMPLATE_CACHE_DIR,
           settings=settings
       )
       engine = ChecklistEngine(
           db_session_factory=get_db,  # Adjust based on your DI pattern
           registry=registry,
           settings=settings
       )
       
       async def checklist_callback(project_id: UUID, agent_result: dict) -> dict:
           """Process checklist updates from agent results."""
           return await engine.process_agent_result(project_id, agent_result)
       
       on_end_callback = checklist_callback
   else:
       on_end_callback = None
   ```

   **Update orchestrator instantiation**:
   ```python
   orchestrator = AgentOrchestrator(
       # ... existing params ...
       on_end=on_end_callback
   )
   ```

**Quality Checks**:
- [ ] Feature flag checked before creating engine
- [ ] Callback properly typed
- [ ] Engine initialized with correct dependencies
- [ ] Callback passed to orchestrator
- [ ] No circular imports

---

### Task 3.3: Integrate with Router Agent

**File**: `backend/app/agents_system/agents/router.py` (MODIFY)

**What to Change**:

1. **Import Dependencies**:
   ```python
   from backend.app.agents_system.checklists.service import get_checklist_service
   ```

2. **Add Sync After update_project_state()**:

   Locate where `update_project_state()` is called (likely in `_apply_legacy_updates` or similar):
   ```python
   # Existing code:
   await update_project_state(project_id, updated_state, db)
   ```

   **Add after**:
   ```python
   # NEW: Sync to normalized DB if feature enabled
   settings = get_settings()
   if settings.FEATURE_WAF_NORMALIZED:
       try:
           service = await get_checklist_service(db=db, settings=settings)
           sync_result = await service.sync_project(
               project_id=project_id,
               project_state=updated_state
           )
           logger.info(
               "Synced project state to normalized DB",
               project_id=str(project_id),
               sync_result=sync_result
           )
       except Exception as e:
           logger.error(
               "Failed to sync project state to normalized DB",
               project_id=str(project_id),
               error=str(e)
           )
           # Don't fail the request if sync fails - log and continue
   ```

**Design Decision**:
- For synchronous guarantee: await the sync
- For lower latency: schedule as background task using FastAPI BackgroundTasks
- Recommendation: Start with await (synchronous), optimize later if needed

**Quality Checks**:
- [ ] Feature flag checked
- [ ] Sync called after update_project_state succeeds
- [ ] Errors logged but don't crash request
- [ ] Typing preserved
- [ ] Service obtained via dependency injection

---

### Task 3.4: Create API Router

**File**: `backend/app/routers/checklists/__init__.py` (NEW)

Create package marker file.

**File**: `backend/app/routers/checklists/checklist_router.py` (NEW)

**What to Implement**:

1. **Router Setup**:
   ```python
   from fastapi import APIRouter, Depends, HTTPException, Query
   from sqlalchemy.ext.asyncio import AsyncSession
   from uuid import UUID
   from backend.app.db.session import get_db
   from backend.app.agents_system.checklists.service import get_checklist_service, ChecklistService
   from backend.app.models.checklist import *
   from typing import Literal
   import structlog
   
   logger = structlog.get_logger(__name__)
   
   router = APIRouter(
       prefix="/api/projects/{project_id}/checklists",
       tags=["checklists"]
   )
   ```

2. **Pydantic Models for Request/Response**:

   Create file `backend/app/routers/checklists/schemas.py`:
   ```python
   from pydantic import BaseModel, Field
   from uuid import UUID
   from typing import Literal
   from datetime import datetime
   
   class ChecklistSummary(BaseModel):
       id: UUID
       project_id: UUID
       template_id: UUID | None
       title: str
       status: Literal['open', 'archived']
       items_count: int
       last_synced_at: datetime | None
   
   class ChecklistItemDetail(BaseModel):
       id: UUID
       template_item_id: str
       title: str
       description: str | None
       pillar: str | None
       severity: Literal['low', 'medium', 'high', 'critical']
       guidance: dict | None
       metadata: dict | None
       latest_evaluation: dict | None  # Optional evaluation summary
   
   class ChecklistDetail(BaseModel):
       id: UUID
       project_id: UUID
       template_id: UUID | None
       title: str
       status: Literal['open', 'archived']
       items: list[ChecklistItemDetail]
   
   class EvaluateItemRequest(BaseModel):
       status: Literal['open', 'in_progress', 'fixed', 'false_positive']
       evaluator: str
       evidence: dict | None = None
       comment: str | None = None
       source_type: str = "manual"
       source_id: str | None = None
   
   class ProgressResponse(BaseModel):
       total_items: int
       completed_items: int
       percent_complete: float
       severity_breakdown: dict[str, int]
       last_updated: datetime | None
       uncovered_critical: list[dict]  # Top 3 critical/high uncovered items
   
   class ResyncRequest(BaseModel):
       mode: Literal['from_state', 'from_db']
       dry_run: bool = False
   ```

3. **Endpoint Implementations**:

   a. **GET `/api/projects/{project_id}/checklists`**:
   ```python
   @router.get("", response_model=list[ChecklistSummary])
   async def list_checklists(
       project_id: UUID,
       template_slug: str | None = Query(None),
       status: Literal['open', 'archived'] | None = Query(None),
       limit: int = Query(100, le=1000),
       offset: int = Query(0, ge=0),
       db: AsyncSession = Depends(get_db),
       service: ChecklistService = Depends(get_checklist_service)
   ) -> list[ChecklistSummary]:
       """List all checklists for a project."""
       # Query Checklist model with filters
       # Join to count items
       # Return list of ChecklistSummary
   ```

   b. **GET `/api/projects/{project_id}/checklists/{checklist_id}`**:
   ```python
   @router.get("/{checklist_id}", response_model=ChecklistDetail)
   async def get_checklist(
       project_id: UUID,
       checklist_id: UUID,
       db: AsyncSession = Depends(get_db),
       service: ChecklistService = Depends(get_checklist_service)
   ) -> ChecklistDetail:
       """Get detailed checklist with items and latest evaluations."""
       # Query Checklist by ID
       # Verify project_id matches
       # Load items and latest evaluations
       # Return ChecklistDetail
       # Raise HTTPException 404 if not found
   ```

   c. **PATCH `/api/projects/{project_id}/checklists/{checklist_id}/items/{item_id}`**:
   ```python
   @router.patch("/{checklist_id}/items/{item_id}")
   async def update_checklist_item(
       project_id: UUID,
       checklist_id: UUID,
       item_id: UUID,
       payload: EvaluateItemRequest,
       db: AsyncSession = Depends(get_db),
       service: ChecklistService = Depends(get_checklist_service)
   ) -> dict:
       """Create evaluation for checklist item (manual or tool)."""
       # Verify item exists and belongs to project/checklist
       # Call service.evaluate_item()
       # Return updated item + evaluation
       # Handle errors with appropriate HTTP status codes
   ```

   d. **POST `/api/projects/{project_id}/checklists/{checklist_id}/items/{item_id}/evaluate`**:
   ```python
   @router.post("/{checklist_id}/items/{item_id}/evaluate")
   async def evaluate_item(
       project_id: UUID,
       checklist_id: UUID,
       item_id: UUID,
       payload: EvaluateItemRequest,
       db: AsyncSession = Depends(get_db),
       service: ChecklistService = Depends(get_checklist_service)
   ) -> dict:
       """Evaluate checklist item (similar to PATCH but explicit POST)."""
       # Same logic as PATCH above
       # Return 202 if processed async, 200 if sync
   ```

   e. **GET `/api/projects/{project_id}/checklists/{checklist_id}/progress`**:
   ```python
   @router.get("/{checklist_id}/progress", response_model=ProgressResponse)
   async def get_progress(
       project_id: UUID,
       checklist_id: UUID,
       service: ChecklistService = Depends(get_checklist_service)
   ) -> ProgressResponse:
       """Get completion metrics for checklist."""
       # Call service.get_progress()
       # Query top 3 uncovered critical/high items
       # Return ProgressResponse
   ```

   f. **POST `/api/projects/{project_id}/checklists/resync`**:
   ```python
   @router.post("/resync")
   async def resync_checklist(
       project_id: UUID,
       payload: ResyncRequest,
       db: AsyncSession = Depends(get_db),
       service: ChecklistService = Depends(get_checklist_service)
   ) -> dict:
       """Trigger sync between ProjectState and normalized DB."""
       # Based on mode:
       #   from_state: call service.sync_project()
       #   from_db: call engine.sync_db_to_project_state()
       # If dry_run, don't commit
       # Return summary
   ```

4. **Error Handling**:
   - 404: Checklist or item not found
   - 403: Unauthorized access to project
   - 400: Invalid payload or validation error
   - 500: Internal server error with logged details

**Quality Checks**:
- [ ] All endpoints have response_model defined
- [ ] All path/query parameters typed correctly
- [ ] Pydantic schemas defined for all request/response bodies
- [ ] Authentication/authorization checks included (reuse existing project auth)
- [ ] Database transactions handled correctly
- [ ] Error responses follow API conventions
- [ ] OpenAPI docs generated correctly (test via /docs endpoint)
- [ ] All endpoints have docstrings

---

### Task 3.5: Register Router in Main App

**File**: `backend/app/main.py` (MODIFY)

**What to Change**:

1. **Import Router**:
   ```python
   from backend.app.routers.checklists.checklist_router import router as checklist_router
   ```

2. **Include Router**:
   Locate where routers are registered:
   ```python
   app.include_router(checklist_router)
   ```

**Quality Checks**:
- [ ] Router registered correctly
- [ ] No route conflicts with existing routes
- [ ] Test: `curl http://localhost:8000/docs` shows new endpoints

---

### Task 3.6: Update Frontend Types

**File**: `frontend/src/types/api-artifacts.ts` (MODIFY)

**What to Change**:

Add TypeScript interfaces matching backend schemas:

```typescript
export interface ChecklistSummary {
  id: string;
  projectId: string;
  templateId: string | null;
  title: string;
  status: 'open' | 'archived';
  itemsCount: number;
  lastSyncedAt: string | null;
}

export interface ChecklistItemDetail {
  id: string;
  templateItemId: string;
  title: string;
  description: string | null;
  pillar: string | null;
  severity: 'low' | 'medium' | 'high' | 'critical';
  guidance: Record<string, unknown> | null;
  metadata: Record<string, unknown> | null;
  latestEvaluation: {
    status: string;
    evaluator: string;
    timestamp: string;
  } | null;
}

export interface ChecklistDetail {
  id: string;
  projectId: string;
  templateId: string | null;
  title: string;
  status: 'open' | 'archived';
  items: ChecklistItemDetail[];
}

export interface ProgressResponse {
  totalItems: number;
  completedItems: number;
  percentComplete: number;
  severityBreakdown: Record<string, number>;
  lastUpdated: string | null;
  uncoveredCritical: Array<{
    id: string;
    title: string;
    severity: string;
  }>;
}
```

**Quality Checks**:
- [ ] Types match backend Pydantic schemas exactly
- [ ] Use apiMappings.ts for any naming differences (camelCase vs snake_case)
- [ ] No `any` types used
- [ ] Export interfaces for use in components

---

### Phase 3 Verification Checklist

- [ ] Orchestrator accepts on_end callback
- [ ] Runner registers callback with engine
- [ ] Router syncs after update_project_state
- [ ] All API endpoints implemented and tested
- [ ] API router registered in main app
- [ ] Frontend types added and match backend
- [ ] No linting errors: `ruff check backend/app/routers/checklists/`
- [ ] No type errors: `mypy backend/app/routers/checklists/`
- [ ] OpenAPI docs accessible and accurate
- [ ] Manual API test: GET /api/projects/{id}/checklists returns data

---

## Phase 4: Backfill, Testing & Documentation

**Estimated Time**: 3-5 days  
**Dependencies**: Phase 3 complete

### Task 4.1: Create Backfill Service

**File**: `backend/app/services/backfill_service.py` (NEW)

**What to Implement**:

1. **BackfillService Class**:
   ```python
   from backend.app.agents_system.checklists.engine import ChecklistEngine
   from backend.app.models.project import Project
   from sqlalchemy import select
   from sqlalchemy.ext.asyncio import AsyncSession
   import structlog
   
   logger = structlog.get_logger(__name__)
   
   class BackfillService:
       """
       Handles bulk backfill of projects from ProjectState to normalized DB.
       
       Features:
       - Idempotent chunked processing
       - Dry-run mode for validation
       - Progress tracking
       - Verification sampling
       """
   ```

2. **__init__ Method**:
   ```python
   def __init__(
       self,
       engine: ChecklistEngine,
       db_session_factory: Callable[[], AsyncSession],
       batch_size: int = 50
   ) -> None:
   ```

3. **backfill_all_projects Method**:
   ```python
   async def backfill_all_projects(
       self,
       dry_run: bool = False,
       verify_sample: bool = True
   ) -> dict:
       """
       Backfill all projects with WAF checklists.
       
       Args:
           dry_run: If True, validate but don't write
           verify_sample: If True, validate random 1% sample
           
       Returns:
           Summary dict with counts and errors
       """
   ```
   - Query all projects with `project_state.state['wafChecklist']` present
   - Process in batches (self.batch_size)
   - For each project:
     - Call engine.sync_project_state_to_db()
     - Track success/failure
     - If verify_sample and random() < 0.01:
       - Run verification (Task 4.2)
   - Log progress every N projects
   - Return summary: {
       "total_projects": int,
       "processed": int,
       "skipped": int,
       "errors": list[dict],
       "verification_passed": bool
     }

4. **backfill_project Method**:
   ```python
   async def backfill_project(
       self,
       project_id: UUID,
       dry_run: bool = False
   ) -> dict:
       """Backfill single project."""
   ```
   - Load project_state for project_id
   - Call engine.sync_project_state_to_db()
   - Return result

5. **get_backfill_progress Method**:
   ```python
   async def get_backfill_progress(self) -> dict:
       """
       Get current backfill progress across all projects.
       
       Returns:
           Dict with total projects, migrated projects, percentage
       """
   ```
   - Count projects with wafChecklist in JSON
   - Count projects with Checklist records in DB
   - Calculate percentage
   - Return summary

**Quality Checks**:
- [ ] All methods fully typed
- [ ] Comprehensive docstrings
- [ ] Idempotency guaranteed
- [ ] Progress logging implemented
- [ ] Error handling with rollback
- [ ] Dry-run mode implemented correctly

---

### Task 4.2: Create Verification Helpers

**File**: `backend/app/services/backfill_service.py` (ADD to existing)

**What to Add**:

1. **verify_project_consistency Method**:
   ```python
   async def verify_project_consistency(
       self,
       project_id: UUID
   ) -> tuple[bool, list[str]]:
       """
       Verify normalized DB matches ProjectState JSON for a project.
       
       Args:
           project_id: Project UUID to verify
           
       Returns:
           (is_consistent, list_of_differences)
       """
   ```
   - Load project_state JSON
   - Call engine.sync_db_to_project_state() to reconstruct JSON
   - Use normalize_helpers.validate_normalized_consistency()
   - Return result

2. **generate_verification_report Method**:
   ```python
   async def generate_verification_report(
       self,
       sample_size: int = 10
   ) -> dict:
       """
       Generate verification report for random sample of projects.
       
       Returns:
           Report dict with pass/fail and details
       """
   ```
   - Select random sample of projects
   - Verify each using verify_project_consistency()
   - Aggregate results
   - Return: {
       "sample_size": int,
       "passed": int,
       "failed": int,
       "inconsistencies": list[dict]
     }

**Quality Checks**:
- [ ] Verification logic thorough
- [ ] Random sampling implemented correctly
- [ ] Report format clear and actionable

---

### Task 4.3: Create Backfill CLI Script

**File**: `scripts/backfill_waf.py` (NEW)

**What to Implement**:

1. **Script Structure**:
   ```python
   #!/usr/bin/env python
   """
   WAF Checklist Backfill Script
   
   Migrates existing ProjectState.state['wafChecklist'] JSON
   to normalized database tables.
   
   Usage:
       python scripts/backfill_waf.py --dry-run --batch-size 50
       python scripts/backfill_waf.py --execute --verify
       python scripts/backfill_waf.py --project-id <uuid>
   """
   
   import asyncio
   import click
   from uuid import UUID
   from backend.app.db.session import async_session_maker
   from backend.app.services.backfill_service import BackfillService
   from backend.app.agents_system.checklists.engine import ChecklistEngine
   from backend.app.agents_system.checklists.registry import ChecklistRegistry
   from backend.app.config.settings import get_settings
   import structlog
   
   logger = structlog.get_logger(__name__)
   ```

2. **CLI Commands**:

   a. **Main Command Group**:
   ```python
   @click.group()
   def cli():
       """WAF Checklist Backfill CLI."""
       pass
   ```

   b. **backfill Command**:
   ```python
   @cli.command()
   @click.option('--dry-run', is_flag=True, help='Validate without writing')
   @click.option('--batch-size', default=50, help='Projects per batch')
   @click.option('--verify', is_flag=True, help='Run verification sample')
   def backfill(dry_run: bool, batch_size: int, verify: bool) -> None:
       """Backfill all projects."""
       # Initialize dependencies
       # Create BackfillService
       # Call backfill_all_projects()
       # Print summary
   ```

   c. **backfill-project Command**:
   ```python
   @cli.command()
   @click.argument('project_id', type=click.UUID)
   @click.option('--dry-run', is_flag=True)
   def backfill_project(project_id: UUID, dry_run: bool) -> None:
       """Backfill single project."""
       # Initialize dependencies
       # Create BackfillService
       # Call backfill_project()
       # Print result
   ```

   d. **verify Command**:
   ```python
   @cli.command()
   @click.option('--sample-size', default=10, help='Number of projects to verify')
   def verify(sample_size: int) -> None:
       """Verify backfill consistency."""
       # Initialize dependencies
       # Create BackfillService
       # Call generate_verification_report()
       # Print report
   ```

   e. **progress Command**:
   ```python
   @cli.command()
   def progress() -> None:
       """Show backfill progress."""
       # Initialize dependencies
       # Create BackfillService
       # Call get_backfill_progress()
       # Print progress bar and stats
   ```

3. **Main Entry Point**:
   ```python
   if __name__ == '__main__':
       cli()
   ```

**Quality Checks**:
- [ ] All CLI options documented with help text
- [ ] Error handling with clear messages
- [ ] Progress output user-friendly
- [ ] Dry-run mode works correctly
- [ ] Script can be run with `uv python scripts/backfill_waf.py`

---

### Task 4.4: Create Maintenance CLI Script

**File**: `scripts/maintain_checklists.py` (NEW)

**What to Implement**:

1. **Commands to Include**:
   - `refresh-templates`: Re-fetch templates from Microsoft Learn MCP
   - `sync-project`: Force resync specific project
   - `stats`: Show DB statistics (total checklists, items, evaluations)
   - `cleanup`: Remove orphaned records

2. **Script Structure** (similar to backfill_waf.py):
   ```python
   #!/usr/bin/env python
   """
   WAF Checklist Maintenance Script
   
   Utilities for managing normalized checklist data.
   """
   
   import asyncio
   import click
   # ... imports ...
   
   @click.group()
   def cli():
       """Checklist maintenance utilities."""
       pass
   
   @cli.command()
   def refresh_templates() -> None:
       """Refresh cached templates from Microsoft Learn."""
       # Use MCP server to fetch latest templates
       # Update cache directory
       # Reload registry
   
   @cli.command()
   @click.argument('project_id', type=click.UUID)
   @click.option('--direction', type=click.Choice(['to-db', 'from-db']))
   def sync_project(project_id: UUID, direction: str) -> None:
       """Sync project between JSON and DB."""
       # Call appropriate engine method based on direction
   
   @cli.command()
   def stats() -> None:
       """Show database statistics."""
       # Query counts from each table
       # Print summary
   
   @cli.command()
   @click.option('--dry-run', is_flag=True)
   def cleanup(dry_run: bool) -> None:
       """Remove orphaned records."""
       # Find evaluations without items
       # Find items without checklists
       # Delete if not dry-run
   
   if __name__ == '__main__':
       cli()
   ```

**Quality Checks**:
- [ ] All commands documented
- [ ] Dry-run mode where applicable
- [ ] Clear output messages
- [ ] Error handling

---

### Task 4.5: Write Unit Tests

**File**: `backend/tests/models/test_checklist_models.py` (from Phase 1)

**What to Test**:
1. Model instantiation with valid data
2. Foreign key relationships
3. Unique constraints
4. Deterministic ID generation
5. Enum validation
6. Default values

**File**: `backend/tests/services/test_normalize_helpers.py` (NEW)

**What to Test**:
1. `compute_deterministic_item_id()` produces stable UUIDs
2. `normalize_waf_item()` with valid input
3. `normalize_waf_item()` with missing optional fields
4. `normalize_waf_evaluation()` with valid input
5. `denormalize_checklist_to_json()` reconstruction
6. `validate_normalized_consistency()` detects differences

**File**: `backend/tests/services/test_checklist_service.py` (NEW)

**What to Test** (with mocked DB):
1. `evaluate_item()` creates evaluation record
2. `list_next_actions()` returns prioritized items
3. `compute_progress()` calculates percentage correctly
4. Progress thresholds: <50% red, <80% yellow, >95% green

**File**: `backend/tests/agents_system/test_checklist_engine.py` (NEW)

**What to Test** (with test DB fixture):
1. `process_agent_result()` creates checklist records
2. `sync_project_state_to_db()` is idempotent (run twice, same result)
3. `sync_db_to_project_state()` reconstructs JSON correctly
4. Chunking behavior with large datasets
5. Error handling and rollback on failure

**File**: `backend/tests/agents_system/test_agent_checklist_integration.py` (NEW)

**What to Test** (integration):
1. Full flow: agent result → normalized DB → progress calculation
2. Dual-write mode: JSON and DB both updated
3. Progress endpoint returns expected percentage
4. Feature flag behavior (enabled vs disabled)

**Quality Standards for Tests**:
- [ ] Use pytest fixtures for DB setup/teardown
- [ ] Use factories or builders for test data
- [ ] Test both success and error cases
- [ ] Mock external dependencies (MCP server, file I/O)
- [ ] Assert on specific values, not just "not None"
- [ ] Clear test names describing what is tested
- [ ] Use parametrize for similar test cases with different inputs

---

### Task 4.6: Write Integration Tests

**File**: `backend/tests/test_api/test_waf_checklists.py` (NEW)

**What to Test**:
1. GET /api/projects/{id}/checklists - returns list
2. GET /api/projects/{id}/checklists/{cid} - returns detail or 404
3. PATCH /api/projects/{id}/checklists/{cid}/items/{iid} - updates item
4. POST evaluate endpoint - creates evaluation
5. GET progress endpoint - returns metrics
6. POST resync endpoint - triggers sync
7. Authorization: reject access to other users' projects
8. Validation: reject invalid payloads

**Test Structure**:
```python
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.tests.fixtures import test_db, test_project, test_checklist

client = TestClient(app)

@pytest.mark.asyncio
async def test_list_checklists(test_db, test_project):
    """Test GET /api/projects/{id}/checklists returns checklists."""
    response = client.get(f"/api/projects/{test_project.id}/checklists")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # ... more assertions ...

# ... more tests ...
```

**Quality Checks**:
- [ ] All endpoints covered
- [ ] Test both authenticated and unauthenticated requests
- [ ] Test error cases (404, 400, 403, 500)
- [ ] Use test fixtures for setup
- [ ] Cleanup after tests

---

### Task 4.7: Write Backfill Tests

**File**: `backend/tests/test_backfill.py` (NEW)

**What to Test**:
1. Backfill with no projects (should complete successfully)
2. Backfill with sample projects containing wafChecklist
3. Idempotency: run twice, same records created
4. Chunking: verify batches processed correctly
5. Dry-run mode: no writes to DB
6. Verification: consistency check passes for sample
7. Error handling: failed project doesn't crash entire backfill

**Test Structure**:
```python
import pytest
from backend.app.services.backfill_service import BackfillService
from backend.tests.fixtures import test_db, sample_projects_with_waf

@pytest.mark.asyncio
async def test_backfill_idempotent(test_db, sample_projects_with_waf):
    """Test backfill can run multiple times without duplicates."""
    service = BackfillService(...)
    
    # Run backfill first time
    result1 = await service.backfill_all_projects(dry_run=False)
    
    # Count records
    count1 = await count_checklist_items(test_db)
    
    # Run backfill second time
    result2 = await service.backfill_all_projects(dry_run=False)
    
    # Count records again
    count2 = await count_checklist_items(test_db)
    
    # Assert counts are the same
    assert count1 == count2
    assert result2["processed"] == result1["processed"]
```

**Quality Checks**:
- [ ] Test with realistic data volumes
- [ ] Verify performance (timing checks)
- [ ] Test edge cases (empty checklists, malformed JSON)

---

### Task 4.8: Create Documentation

**File**: `docs/waf_normalization_implementation/WAF_NORMALIZED_DB.md` (NEW)

**What to Include**:

1. **Overview Section**:
   - Purpose and motivation
   - High-level architecture diagram (ASCII or Mermaid)
   - Key concepts (templates, checklists, items, evaluations)

2. **Schema Reference**:
   - All tables with field descriptions
   - Relationships diagram
   - Index strategy
   - Why certain design decisions were made

3. **API Reference**:
   - All endpoints with example requests/responses
   - Authentication requirements
   - Error codes and meanings

4. **Backfill Runbook**:
   - Prerequisites
   - Step-by-step instructions for dry-run
   - Step-by-step instructions for execution
   - Expected runtime estimates
   - Verification steps
   - Rollback procedure
   - Troubleshooting common issues

5. **Configuration Reference**:
   - All feature flags and environment variables
   - Default values and recommendations
   - When to enable/disable features

6. **FAQ Section**:
   - Why normalize vs keep JSON?
   - How does dual-write work?
   - What happens if sync fails?
   - How to migrate existing projects?

**File**: `docs/UX_IDE_WORKFLOW.md` (MODIFY)

**What to Add**:

Add new section: "WAF Checklist Lifecycle"

1. **Initialization**:
   - How checklist is created for new project
   - Template selection process
   - Initial state

2. **Agent Evaluation**:
   - How agents populate evaluations
   - AAA_STATE_UPDATE format
   - Sync process

3. **Manual Evaluation**:
   - How architects can override/add evaluations
   - UI workflow
   - API calls involved

4. **Progress Tracking**:
   - How completion is calculated
   - Thresholds and color coding
   - Uncovered items callout

5. **Resync Operation**:
   - When to use
   - What it does
   - Expected behavior

**File**: `docs/waf_normalization_implementation/FRONTEND_INTEGRATION.md` (NEW)

**What to Include**:

1. **Type Definitions**:
   - Reference to api-artifacts.ts
   - Type alignment between FE and BE

2. **API Client Updates**:
   - New API calls to add
   - Example usage in React components

3. **UI Components**:
   - Progress badge component spec
   - Uncovered items callout component spec
   - Checklist item detail view

4. **State Management**:
   - Where to store checklist data
   - When to fetch/refresh

5. **Error Handling**:
   - API error scenarios
   - User-facing error messages

**Quality Checks**:
- [ ] All sections complete and accurate
- [ ] Code examples tested and working
- [ ] Diagrams clear and helpful
- [ ] Runbook steps verified by following them
- [ ] Links between docs working
- [ ] Markdown renders correctly

---

### Phase 4 Verification Checklist

- [ ] BackfillService implemented and tested
- [ ] Verification helpers working correctly
- [ ] backfill_waf.py script runs successfully
- [ ] maintain_checklists.py script functional
- [ ] All unit tests passing: `pytest backend/tests/services/`
- [ ] All integration tests passing: `pytest backend/tests/agents_system/`
- [ ] API tests passing: `pytest backend/tests/test_api/`
- [ ] Backfill tests passing: `pytest backend/tests/test_backfill.py`
- [ ] Test coverage > 80% for new code
- [ ] All documentation written and reviewed
- [ ] Documentation linked from main docs/README.md
- [ ] No linting errors in test files
- [ ] No type errors in test files

---

## Phase 5: Deployment & Operations

**Estimated Time**: 1-3 days (mostly operational)  
**Dependencies**: Phase 4 complete and verified

### Task 5.1: Prepare Staging Deployment

**What to Do**:

1. **Pre-deployment Checklist**:
   - [ ] All tests passing in CI
   - [ ] Code review completed
   - [ ] Migration reviewed by DBA (if applicable)
   - [ ] Backfill script tested on development DB
   - [ ] Documentation reviewed and published
   - [ ] Rollback plan documented

2. **Deploy to Staging**:
   - [ ] Merge feature branch to staging branch
   - [ ] Deploy backend with `FEATURE_WAF_NORMALIZED=false`
   - [ ] Run migration: `alembic upgrade head`
   - [ ] Verify migration succeeded: check tables exist
   - [ ] Restart backend services

3. **Run Backfill in Staging**:
   ```powershell
   # Dry-run first
   uv python scripts/backfill_waf.py backfill --dry-run --batch-size 50
   
   # Review output, check for errors
   
   # Execute backfill
   uv python scripts/backfill_waf.py backfill --batch-size 50 --verify
   
   # Monitor progress
   uv python scripts/backfill_waf.py progress
   ```

4. **Verification in Staging**:
   ```powershell
   # Run verification report
   uv python scripts/backfill_waf.py verify --sample-size 20
   
   # Check specific project
   uv python scripts/backfill_waf.py backfill-project <project-id>
   
   # Query database directly
   # Verify record counts match expectations
   ```

5. **Enable Feature Flag**:
   - [ ] Set `FEATURE_WAF_NORMALIZED=true` in staging config
   - [ ] Restart services
   - [ ] Monitor logs for errors

6. **Test Dual-Write Mode**:
   - [ ] Create new project, trigger agent evaluation
   - [ ] Verify both JSON and DB updated
   - [ ] Check consistency between JSON and DB
   - [ ] Test API endpoints manually

**Quality Checks**:
- [ ] No errors in logs during backfill
- [ ] Verification report shows 100% pass rate
- [ ] API endpoints return expected data
- [ ] Frontend displays checklist data correctly
- [ ] Performance acceptable (response times < 200ms for list endpoints)

---

### Task 5.2: Monitor Staging

**Duration**: 7-14 days

**What to Monitor**:

1. **Metrics to Track**:
   - Backfill progress (should reach 100%)
   - Sync error rate (should be < 0.1%)
   - API endpoint latency
   - Database query performance
   - Consistency check pass rate

2. **Log Analysis**:
   - Search for ERROR level logs related to checklists
   - Review WARNING logs for sync issues
   - Check for duplicate item_id errors
   - Monitor database deadlocks or timeouts

3. **User Feedback**:
   - Collect feedback from QA team
   - Test E2E workflows
   - Verify data accuracy with manual spot checks

4. **Performance Testing**:
   - Load test API endpoints
   - Test with large checklists (100+ items)
   - Verify chunking works correctly

**Success Criteria**:
- [ ] Zero data loss incidents
- [ ] < 0.5% consistency mismatches
- [ ] All API endpoints meet SLA
- [ ] No P0/P1 bugs reported

---

### Task 5.3: Prepare Production Deployment

**What to Do**:

1. **Pre-Production Checklist**:
   - [ ] Staging validation complete (7+ days)
   - [ ] All metrics within acceptable ranges
   - [ ] No critical issues outstanding
   - [ ] Rollback plan tested in staging
   - [ ] Production database backup completed
   - [ ] Maintenance window scheduled (if needed)
   - [ ] Stakeholders notified

2. **Production Deployment Plan**:
   - [ ] Deploy code with `FEATURE_WAF_NORMALIZED=false`
   - [ ] Run migration during maintenance window
   - [ ] Verify migration success
   - [ ] Run backfill in dry-run mode
   - [ ] Review dry-run results
   - [ ] Execute backfill (estimate runtime: 1-2 hours for 1000 projects)
   - [ ] Run verification on 5% sample
   - [ ] Enable feature flag gradually (canary rollout)

3. **Canary Rollout Strategy**:
   - Day 1: Enable for 10% of projects (least critical)
   - Day 2: Monitor metrics, expand to 25%
   - Day 3: Expand to 50%
   - Day 4: Expand to 100% if all metrics healthy

**Quality Checks**:
- [ ] Production backup verified and restorable
- [ ] Rollback tested in staging
- [ ] Communication plan for downtime (if any)

---

### Task 5.4: Production Backfill

**File**: Create `docs/waf_normalization_implementation/PRODUCTION_BACKFILL_LOG.md` (NEW)

**What to Document** (in real-time during backfill):

```markdown
# Production Backfill Log

## Pre-Backfill State
- Date: YYYY-MM-DD HH:MM UTC
- Database version: <version>
- Total projects with wafChecklist: <count>
- Estimated runtime: <minutes>
- Operator: <name>

## Execution Log

### Dry-Run Results
- Time: YYYY-MM-DD HH:MM UTC
- Projects scanned: <count>
- Projects to migrate: <count>
- Projects to skip: <count>
- Errors detected: <count>
- Dry-run passed: YES/NO

### Execution
- Start time: YYYY-MM-DD HH:MM UTC
- Batch size: 50
- Progress updates:
  - 10% complete at HH:MM
  - 25% complete at HH:MM
  - 50% complete at HH:MM
  - 75% complete at HH:MM
  - 100% complete at HH:MM
- End time: YYYY-MM-DD HH:MM UTC
- Total duration: <minutes>

### Post-Backfill Verification
- Verification sample size: 50 projects
- Verification passed: YES/NO
- Inconsistencies found: <count>
- Action taken: <description>

## Metrics
- Checklists created: <count>
- ChecklistItems created: <count>
- ChecklistItemEvaluations created: <count>
- Database size increase: <MB>

## Issues & Resolutions
(List any issues encountered and how they were resolved)

## Sign-off
- Backfill completed successfully: YES/NO
- Signed by: <name>
- Date: YYYY-MM-DD
```

**Execution Commands**:
```powershell
# Record start time
$startTime = Get-Date

# Dry-run
uv python scripts/backfill_waf.py backfill --dry-run --batch-size 50 | Tee-Object -FilePath "backfill_dryrun.log"

# Review output
# If dry-run passes, execute

# Execute
uv python scripts/backfill_waf.py backfill --batch-size 50 --verify | Tee-Object -FilePath "backfill_execution.log"

# Record end time
$endTime = Get-Date
$duration = $endTime - $startTime
Write-Host "Duration: $duration"

# Verify
uv python scripts/backfill_waf.py verify --sample-size 50 | Tee-Object -FilePath "backfill_verify.log"
```

**Quality Checks**:
- [ ] All commands logged with output
- [ ] Verification passes with 100% success rate
- [ ] Database integrity checks pass
- [ ] Spot-check random projects manually

---

### Task 5.5: Enable Feature Flag

**What to Do**:

1. **Gradual Rollout Configuration**:

   If using feature management system:
   ```python
   # In settings.py or feature flag config
   WAF_NORMALIZED_ROLLOUT_PERCENTAGE: int = Field(
       default=0,
       description="Percentage of projects using normalized DB (0-100)"
   )
   ```

   Modify engine or service to check:
   ```python
   def should_use_normalized(self, project_id: UUID) -> bool:
       """Determine if project should use normalized DB."""
       if not self.settings.FEATURE_WAF_NORMALIZED:
           return False
       
       # Canary: use hash of project_id for stable assignment
       if self.settings.WAF_NORMALIZED_ROLLOUT_PERCENTAGE < 100:
           hash_val = int(str(project_id).replace('-', ''), 16)
           bucket = hash_val % 100
           return bucket < self.settings.WAF_NORMALIZED_ROLLOUT_PERCENTAGE
       
       return True
   ```

2. **Rollout Schedule**:
   - Day 1 (Post-backfill): Set `FEATURE_WAF_NORMALIZED=true`, `WAF_NORMALIZED_ROLLOUT_PERCENTAGE=10`
   - Day 2 (After 24h monitoring): Increase to 25% if metrics healthy
   - Day 3: Increase to 50%
   - Day 4: Increase to 75%
   - Day 5: Increase to 100%

3. **Monitoring During Rollout**:
   - Set up dashboard with key metrics
   - Alert on anomalies
   - Prepare rollback procedure

**Quality Checks**:
- [ ] Rollout percentage changes take effect without restart
- [ ] Projects assigned to buckets consistently
- [ ] Metrics tracked per bucket
- [ ] Rollback tested (reduce percentage)

---

### Task 5.6: Setup Monitoring & Alerts

**File**: `docs/waf_normalization_implementation/MONITORING.md` (NEW)

**What to Document**:

1. **Metrics to Instrument**:

   Add to backend (use existing metrics library):
   ```python
   # In engine.py or service.py
   from prometheus_client import Counter, Histogram
   
   waf_sync_counter = Counter(
       'waf_checklist_sync_total',
       'Total checklist syncs',
       ['status', 'direction']  # status: success/error, direction: to_db/from_db
   )
   
   waf_sync_duration = Histogram(
       'waf_checklist_sync_duration_seconds',
       'Duration of checklist sync operations',
       ['direction']
   )
   
   waf_evaluation_counter = Counter(
       'waf_evaluation_total',
       'Total evaluations created',
       ['source_type']  # agent-validation, manual, etc.
   )
   
   waf_progress_gauge = Gauge(
       'waf_checklist_progress_percent',
       'Checklist completion percentage',
       ['project_id', 'checklist_id']
   )
   ```

2. **Alert Definitions**:

   ```yaml
   # alerts.yaml (example for Prometheus/Alertmanager)
   groups:
     - name: waf_checklist
       interval: 5m
       rules:
         - alert: HighWafSyncErrorRate
           expr: rate(waf_checklist_sync_total{status="error"}[5m]) > 0.05
           for: 10m
           labels:
             severity: warning
           annotations:
             summary: "High WAF checklist sync error rate"
             description: "Error rate is {{ $value }} errors/sec"
         
         - alert: WafSyncDurationHigh
           expr: histogram_quantile(0.95, waf_checklist_sync_duration_seconds) > 5
           for: 15m
           labels:
             severity: warning
           annotations:
             summary: "WAF sync operations are slow"
             description: "P95 duration is {{ $value }} seconds"
         
         - alert: WafBackfillStalled
           expr: waf_backfill_progress_percent < 100 and rate(waf_backfill_progress_percent[30m]) == 0
           for: 1h
           labels:
             severity: critical
           annotations:
             summary: "WAF backfill has stalled"
             description: "Backfill at {{ $value }}% with no progress"
   ```

3. **Dashboard Panels**:
   - Backfill progress (line graph over time)
   - Sync error rate (counter)
   - API endpoint latency (histogram)
   - Active checklists count (gauge)
   - Evaluations per minute (counter rate)
   - Consistency check pass rate (gauge)

**Quality Checks**:
- [ ] All metrics instrumented and exposing data
- [ ] Alerts fire correctly when thresholds exceeded
- [ ] Dashboard accessible and useful
- [ ] On-call runbook includes checklist alerts

---

### Task 5.7: Deprecation Plan for JSON Format

**File**: `docs/waf_normalization_implementation/DEPRECATION_PLAN.md` (NEW)

**What to Document**:

1. **Timeline**:
   - T+0: Dual-write enabled
   - T+30 days: Announce deprecation, normalized DB is primary
   - T+60 days: Read-only compatibility for JSON
   - T+90 days: Remove dual-write code, JSON no longer updated
   - T+120 days: Remove JSON field from schema (optional migration)

2. **Migration Path**:
   - Document how to migrate any remaining JSON-dependent code
   - Provide helper functions for read-only access to legacy data

3. **Cleanup Migration**:
   ```python
   # Future migration: <timestamp>_remove_waf_json.py
   def upgrade():
       # Remove wafChecklist from ProjectState.state JSONB
       # Or add archived flag
       pass
   
   def downgrade():
       # Not supported - data loss
       pass
   ```

**Quality Checks**:
- [ ] Timeline communicated to stakeholders
- [ ] Deprecation warnings added to code
- [ ] Migration path documented

---

### Phase 5 Verification Checklist

- [ ] Staging deployment successful
- [ ] Backfill completed in staging with 100% success
- [ ] Dual-write mode tested and verified
- [ ] 7-14 days monitoring in staging complete
- [ ] All metrics within acceptable ranges
- [ ] Production deployment plan approved
- [ ] Production database backed up
- [ ] Production backfill completed successfully
- [ ] Verification passed for production sample
- [ ] Feature flag enabled with gradual rollout
- [ ] Monitoring and alerts configured
- [ ] Dashboard shows healthy metrics
- [ ] Deprecation plan documented and communicated

---

## Quality Standards

### Code Quality Requirements

1. **Type Safety**:
   - [ ] All Python code uses type hints (no `Any` types)
   - [ ] All TypeScript code uses explicit types (no `any`)
   - [ ] mypy passes with strict mode: `mypy backend/app/`
   - [ ] TypeScript compiler passes: `tsc --noEmit`

2. **Linting**:
   - [ ] Python: `ruff check backend/` passes
   - [ ] Python: `ruff format backend/` applied
   - [ ] TypeScript: `eslint .` from frontend/ passes
   - [ ] No warnings remain

3. **Documentation**:
   - [ ] All classes have docstrings
   - [ ] All public methods have docstrings with Args/Returns/Raises
   - [ ] Complex logic has inline comments
   - [ ] README files present in new packages

4. **Testing**:
   - [ ] Unit test coverage > 80%
   - [ ] Integration tests cover all API endpoints
   - [ ] E2E tests updated if applicable
   - [ ] All tests pass: `pytest backend/tests/`

5. **Security**:
   - [ ] No hardcoded secrets or credentials
   - [ ] Input validation on all API endpoints
   - [ ] SQL injection prevention (use parameterized queries)
   - [ ] Authorization checks on all endpoints

6. **Performance**:
   - [ ] Database indexes on all foreign keys
   - [ ] Queries use appropriate indexes (verify with EXPLAIN)
   - [ ] Chunking used for large dataset operations
   - [ ] API endpoints respond < 500ms for typical requests

---

## Testing Strategy

### Test Pyramid

1. **Unit Tests (70%)**:
   - Test individual functions and methods
   - Mock external dependencies
   - Fast execution (< 1 second per test)
   - Focus: business logic correctness

2. **Integration Tests (20%)**:
   - Test interaction between components
   - Use test database
   - Test API endpoints end-to-end
   - Focus: component integration

3. **E2E Tests (10%)**:
   - Test full user workflows
   - Use staging environment
   - Test critical paths only
   - Focus: user-facing functionality

### Test Execution

**Local Development**:
```powershell
# Run all tests
uv python -m pytest backend/tests/ -v

# Run specific test file
uv python -m pytest backend/tests/services/test_normalize_helpers.py -v

# Run with coverage
uv python -m pytest backend/tests/ --cov=backend/app --cov-report=html

# Run only unit tests
uv python -m pytest backend/tests/ -m unit

# Run only integration tests
uv python -m pytest backend/tests/ -m integration
```

**CI Pipeline**:
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: uv sync
      - name: Run linting
        run: |
          uv run ruff check backend/
          uv run mypy backend/
      - name: Run tests
        run: uv run pytest backend/tests/ --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Verification Checklists

### Pre-Implementation Checklist

- [ ] Plan reviewed and approved
- [ ] Database schema designed and reviewed
- [ ] API contracts defined
- [ ] Frontend types aligned with backend
- [ ] Test strategy defined
- [ ] Monitoring plan created
- [ ] Rollout plan approved

### Development Phase Checklists

See individual phase verification checklists above.

### Pre-Deployment Checklist

- [ ] All phases complete
- [ ] All tests passing
- [ ] Code review completed
- [ ] Documentation complete
- [ ] Migration tested
- [ ] Backfill script tested
- [ ] Rollback plan documented
- [ ] Monitoring configured
- [ ] Stakeholders notified

### Post-Deployment Checklist

- [ ] Migration successful
- [ ] Backfill completed
- [ ] Verification passed
- [ ] Feature flag enabled
- [ ] Metrics healthy
- [ ] No critical errors
- [ ] User acceptance testing complete
- [ ] Documentation published

---

## Rollback Procedures

### If Issues Discovered Pre-Backfill

1. **Disable Feature Flag**:
   ```powershell
   # Set in environment config
   FEATURE_WAF_NORMALIZED=false
   ```

2. **Revert Code**:
   ```powershell
   git revert <commit-hash>
   git push origin main
   ```

3. **Revert Migration** (if already run):
   ```powershell
   alembic downgrade -1
   ```

### If Issues Discovered Post-Backfill

1. **Disable Feature Flag** (keeps data but reverts to JSON reads):
   ```powershell
   FEATURE_WAF_NORMALIZED=false
   ```

2. **Investigate Issues**:
   - Check logs for errors
   - Run verification report
   - Identify affected projects

3. **Fix Issues**:
   - If data inconsistency: re-run backfill for affected projects
   - If code bug: deploy hotfix

4. **If Critical**:
   - Restore database from backup (last resort)
   - Re-run backfill after fix
   - Document incident in postmortem

---

## Success Criteria

### Phase 1 Success Criteria

- [ ] Migration runs without errors
- [ ] All tables created with correct schema
- [ ] Models pass basic instantiation tests

### Phase 2 Success Criteria

- [ ] Engine processes agent results correctly
- [ ] Sync operations are idempotent
- [ ] Registry loads templates from cache
- [ ] All unit tests pass

### Phase 3 Success Criteria

- [ ] Orchestrator invokes callback
- [ ] Router syncs after state update
- [ ] All API endpoints functional
- [ ] Frontend types aligned

### Phase 4 Success Criteria

- [ ] Backfill completes successfully on test data
- [ ] Verification shows 100% consistency
- [ ] All tests pass (unit, integration, E2E)
- [ ] Documentation complete and accurate

### Phase 5 Success Criteria

- [ ] Production backfill completes without errors
- [ ] Verification passes for random sample
- [ ] Feature enabled with stable metrics
- [ ] No P0/P1 incidents
- [ ] User acceptance complete

### Overall Success Criteria

- [ ] All checklists migrated from JSON to normalized DB
- [ ] Agent evaluations update normalized tables
- [ ] API provides analytics capabilities
- [ ] Performance meets SLA (< 500ms for queries)
- [ ] Zero data loss
- [ ] < 0.5% inconsistencies
- [ ] Monitoring and alerts operational
- [ ] Documentation complete and maintained

---

## Timeline & Effort Estimates

| Phase | Tasks | Estimated Days | Dependencies |
|-------|-------|---------------|--------------|
| Phase 1 | Schema, Models, Migration | 2-3 days | None |
| Phase 2 | Registry, Engine, Helpers | 3-5 days | Phase 1 complete |
| Phase 3 | Integration, API, FE Types | 2-4 days | Phase 2 complete |
| Phase 4 | Backfill, Tests, Docs | 3-5 days | Phase 3 complete |
| Phase 5 | Deployment, Operations | 1-3 days + monitoring | Phase 4 complete |
| **Total** | | **11-20 days** | |

**Notes**:
- Estimates are for implementation only (not including CR or QA cycles)
- Monitoring period (7-14 days in staging) runs parallel to other work
- Production deployment scheduled separately based on availability

---

## Maintenance & Support

### Ongoing Maintenance Tasks

1. **Template Updates**:
   - Frequency: Quarterly or when Microsoft updates WAF
   - Command: `uv python scripts/maintain_checklists.py refresh-templates`
   - Responsibility: DevOps or Backend team

2. **Database Cleanup**:
   - Frequency: Monthly
   - Command: `uv python scripts/maintain_checklists.py cleanup --dry-run` (then execute)
   - Removes orphaned records

3. **Performance Monitoring**:
   - Review metrics weekly
   - Optimize slow queries
   - Add indexes if needed

4. **Backfill for New Projects**:
   - Automatic via dual-write
   - For legacy projects: run backfill script as needed

### Support Procedures

1. **User Reports Data Inconsistency**:
   - Check logs for sync errors
   - Run verification for specific project
   - Re-sync if needed: `uv python scripts/maintain_checklists.py sync-project <id> --direction to-db`

2. **API Endpoint Slow**:
   - Check database query performance
   - Review indexes
   - Add caching if appropriate

3. **Backfill Failed**:
   - Review backfill logs
   - Identify failing projects
   - Fix data issues
   - Re-run backfill for affected projects

---

## Appendix

### Glossary

- **WAF**: Well-Architected Framework (Azure best practices)
- **Checklist**: A set of items to evaluate for a project
- **Template**: A predefined checklist structure from Microsoft Learn
- **Item**: Individual checklist item (recommendation/best practice)
- **Evaluation**: Assessment of an item's status (open, fixed, etc.)
- **Dual-write**: Writing to both JSON and normalized DB simultaneously
- **Backfill**: Migrating existing JSON data to normalized tables
- **Idempotent**: Operation can be repeated without changing result

### References

- [Original Plan Document](../plan-normalizeWafChecklistToDb.prompt.prompt.md)
- [Backend Reference](../BACKEND_REFERENCE.md)
- [Frontend Reference](../FRONTEND_REFERENCE.md)
- [System Architecture](../SYSTEM_ARCHITECTURE.md)

### File Mapping

| Purpose | File Path |
|---------|-----------|
| Models | `backend/app/models/checklist.py` |
| Migration | `backend/migrations/versions/<ts>_create_waf_normalized.py` |
| Registry | `backend/app/agents_system/checklists/registry.py` |
| Engine | `backend/app/agents_system/checklists/engine.py` |
| Service | `backend/app/agents_system/checklists/service.py` |
| Helpers | `backend/app/services/normalize_helpers.py` |
| API Router | `backend/app/routers/checklists/checklist_router.py` |
| API Schemas | `backend/app/routers/checklists/schemas.py` |
| Backfill Script | `scripts/backfill_waf.py` |
| Maintenance Script | `scripts/maintain_checklists.py` |
| Backfill Service | `backend/app/services/backfill_service.py` |
| Frontend Types | `frontend/src/types/api-artifacts.ts` |

---

**End of Implementation Plan**

*This document should be updated as implementation progresses. Mark tasks complete and document any deviations from the plan.*
