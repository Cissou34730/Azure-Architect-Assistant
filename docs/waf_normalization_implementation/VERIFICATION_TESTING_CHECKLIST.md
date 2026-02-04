# WAF Normalization - Verification & Testing Checklist

This document provides comprehensive verification procedures and test cases for each implementation phase.

---

## 📋 Overview

Each phase has three types of verification:
1. **Code Quality Checks** - Linting, typing, formatting
2. **Functional Tests** - Unit and integration tests
3. **Manual Verification** - Interactive testing and validation

---

## Phase 1: Schema, Models & Migration

### Code Quality Verification

```powershell
# Run from repository root

# 1. Linting
ruff check backend/app/models/checklist.py
# Expected: No errors or warnings

# 2. Type Checking
mypy backend/app/models/checklist.py --strict
# Expected: Success: no issues found

# 3. Formatting
ruff format backend/app/models/checklist.py --check
# Expected: All files would be left unchanged
```

**Checklist**:
- [ ] No linting errors
- [ ] No type errors (mypy strict mode passes)
- [ ] Code formatted consistently
- [ ] No `Any` types used

---

### Functional Tests

**Test File**: `backend/tests/models/test_checklist_models.py`

#### Test Case 1.1: Model Instantiation
```python
def test_checklist_template_creation():
    """Test ChecklistTemplate can be instantiated with valid data."""
    template = ChecklistTemplate(
        slug="test-waf-v1",
        title="Test WAF",
        version="1.0",
        source="test",
        source_url="https://example.com",
        source_version="2026-01-01",
        content={"items": []}
    )
    assert template.slug == "test-waf-v1"
    assert template.title == "Test WAF"
```

**Run**: `pytest backend/tests/models/test_checklist_models.py::test_checklist_template_creation -v`

**Expected**: ✅ PASSED

---

#### Test Case 1.2: Foreign Key Relationships
```python
def test_checklist_item_relationship(db_session):
    """Test ChecklistItem correctly relates to Checklist."""
    checklist = Checklist(project_id=uuid4(), title="Test")
    item = ChecklistItem(
        checklist=checklist,
        template_item_id="item-1",
        title="Test Item",
        severity="high"
    )
    db_session.add(checklist)
    db_session.add(item)
    db_session.commit()
    
    assert item.checklist_id == checklist.id
    assert item in checklist.items
```

**Run**: `pytest backend/tests/models/test_checklist_models.py::test_checklist_item_relationship -v`

**Expected**: ✅ PASSED

---

#### Test Case 1.3: Unique Constraints
```python
def test_checklist_item_unique_constraint(db_session):
    """Test unique constraint on (checklist_id, template_item_id)."""
    checklist = Checklist(project_id=uuid4(), title="Test")
    item1 = ChecklistItem(
        checklist=checklist,
        template_item_id="item-1",
        title="Test",
        severity="low"
    )
    db_session.add(checklist)
    db_session.add(item1)
    db_session.commit()
    
    # Try to add duplicate
    item2 = ChecklistItem(
        checklist_id=checklist.id,
        template_item_id="item-1",  # Same!
        title="Duplicate",
        severity="low"
    )
    db_session.add(item2)
    
    with pytest.raises(IntegrityError):
        db_session.commit()
```

**Run**: `pytest backend/tests/models/test_checklist_models.py::test_checklist_item_unique_constraint -v`

**Expected**: ✅ PASSED (IntegrityError caught)

---

#### Test Case 1.4: Deterministic ID Generation
```python
def test_deterministic_id_generation():
    """Test compute_deterministic_id produces stable UUIDs."""
    from backend.app.models.checklist import ChecklistItem
    
    project_id = uuid4()
    namespace = uuid4()
    
    # Generate ID twice with same inputs
    id1 = ChecklistItem.compute_deterministic_id(
        project_id, "waf-2026", "item-1", namespace
    )
    id2 = ChecklistItem.compute_deterministic_id(
        project_id, "waf-2026", "item-1", namespace
    )
    
    # Should be identical
    assert id1 == id2
    assert isinstance(id1, UUID)
    
    # Different input should produce different ID
    id3 = ChecklistItem.compute_deterministic_id(
        project_id, "waf-2026", "item-2", namespace
    )
    assert id1 != id3
```

**Run**: `pytest backend/tests/models/test_checklist_models.py::test_deterministic_id_generation -v`

**Expected**: ✅ PASSED

---

#### Test Case 1.5: Enum Validation
```python
def test_severity_enum_validation(db_session):
    """Test severity field only accepts valid enum values."""
    checklist = Checklist(project_id=uuid4(), title="Test")
    
    # Valid severity
    item = ChecklistItem(
        checklist=checklist,
        template_item_id="item-1",
        title="Test",
        severity="critical"  # Valid
    )
    db_session.add(checklist)
    db_session.add(item)
    db_session.commit()
    assert item.severity == "critical"
    
    # Invalid severity should fail at validation layer
    # (Implementation-specific - might be pre-ORM validation)
```

**Run**: `pytest backend/tests/models/test_checklist_models.py::test_severity_enum_validation -v`

**Expected**: ✅ PASSED

---

### Manual Verification

#### Migration Testing

**Step 1: Run Migration**
```powershell
# Ensure test database is clean
alembic downgrade base

# Run migration
alembic upgrade head

# Expected: Migration succeeds with output like:
# INFO  [alembic.runtime.migration] Running upgrade -> 3a7e8c2f, create_waf_normalized
```

**Verify**:
- [ ] Migration runs without errors
- [ ] No warnings about missing dependencies

---

**Step 2: Inspect Database Schema**
```powershell
# Connect to database and verify tables created
psql $DATABASE_URL -c "\dt checklist*"

# Expected output:
# checklist_templates
# checklists
# checklist_items
# checklist_item_evaluations
```

**Verify**:
- [ ] All 4 tables created
- [ ] Table names match model `__tablename__` attributes

---

**Step 3: Check Indexes**
```sql
-- Run in database client
SELECT 
    tablename, 
    indexname 
FROM pg_indexes 
WHERE tablename LIKE 'checklist%'
ORDER BY tablename, indexname;
```

**Verify**:
- [ ] IX_checklist_project_id exists
- [ ] IX_item_checklist_id exists
- [ ] IX_evaluation_item_id exists
- [ ] IX_evaluation_project_item exists
- [ ] Unique indexes on templates.slug
- [ ] Unique index on (checklist_id, template_item_id)

---

**Step 4: Test Migration Downgrade**
```powershell
# Revert migration
alembic downgrade -1

# Expected: Downgrade succeeds

# Verify tables dropped
psql $DATABASE_URL -c "\dt checklist*"
# Expected: No tables found
```

**Verify**:
- [ ] Downgrade runs without errors
- [ ] All tables removed cleanly
- [ ] No orphaned data

---

**Step 5: Re-run Migration**
```powershell
# Migrate back up
alembic upgrade head

# Expected: Success
```

**Verify**:
- [ ] Can migrate up after downgrade
- [ ] Idempotent (running upgrade twice doesn't break)

---

### Phase 1 Sign-off

**All checks must pass before proceeding to Phase 2**:

- [ ] All code quality checks pass (linting, typing, formatting)
- [ ] All 5 test cases pass
- [ ] Migration runs successfully both ways (up and down)
- [ ] Database schema verified manually
- [ ] All indexes created correctly
- [ ] No `Any` types in code
- [ ] All methods have docstrings

**Approved By**: ___________ **Date**: ___________

---

## Phase 2: Core Services & Engine

### Code Quality Verification

```powershell
# Run from repository root

# 1. Linting
ruff check backend/app/agents_system/checklists/
ruff check backend/app/services/normalize_helpers.py

# 2. Type Checking
mypy backend/app/agents_system/checklists/ --strict
mypy backend/app/services/normalize_helpers.py --strict

# 3. Formatting
ruff format backend/app/agents_system/checklists/ --check
ruff format backend/app/services/normalize_helpers.py --check
```

**Checklist**:
- [ ] No linting errors in registry.py, engine.py, service.py
- [ ] No type errors (mypy strict passes)
- [ ] All functions have full type annotations
- [ ] No `Any` types used

---

### Functional Tests

**Test Files**:
- `backend/tests/services/test_normalize_helpers.py`
- `backend/tests/services/test_checklist_service.py`
- `backend/tests/agents_system/test_checklist_engine.py`

#### Test Case 2.1: Deterministic ID Stability
```python
def test_compute_deterministic_item_id():
    """Test deterministic ID generation is stable."""
    from backend.app.services.normalize_helpers import compute_deterministic_item_id
    from backend.app.config.settings import Settings
    
    settings = Settings()
    project_id = uuid4()
    
    id1 = compute_deterministic_item_id(
        project_id, "waf-2026", "item-1", settings.WAF_NAMESPACE_UUID
    )
    id2 = compute_deterministic_item_id(
        project_id, "waf-2026", "item-1", settings.WAF_NAMESPACE_UUID
    )
    
    assert id1 == id2
```

**Expected**: ✅ PASSED

---

#### Test Case 2.2: Item Normalization
```python
def test_normalize_waf_item():
    """Test WAF item JSON is correctly normalized to DB format."""
    from backend.app.services.normalize_helpers import normalize_waf_item
    
    item_dict = {
        "id": "waf-item-123",
        "title": "Enable MFA",
        "description": "Multi-factor authentication...",
        "pillar": "security",
        "severity": "critical",
        "guidance": {"steps": ["Step 1", "Step 2"]},
        "metadata": {"tags": ["auth", "iam"]}
    }
    
    result = normalize_waf_item(item_dict, uuid4(), "waf-2026", uuid4())
    
    assert result["template_item_id"] == "waf-item-123"
    assert result["title"] == "Enable MFA"
    assert result["severity"] == "critical"
    assert "id" in result  # Deterministic ID added
```

**Expected**: ✅ PASSED

---

#### Test Case 2.3: Registry Template Loading
```python
def test_registry_loads_templates(tmp_path):
    """Test ChecklistRegistry loads templates from cache."""
    from backend.app.agents_system.checklists.registry import ChecklistRegistry
    
    # Create cache directory with test template
    cache_dir = tmp_path / "checklists"
    cache_dir.mkdir()
    
    template_file = cache_dir / "test-waf.json"
    template_file.write_text(json.dumps({
        "slug": "test-waf",
        "title": "Test WAF",
        "version": "1.0",
        "source": "test",
        "source_url": "https://example.com",
        "source_version": "2026-01-01",
        "content": {"items": []}
    }))
    
    registry = ChecklistRegistry(cache_dir, settings)
    template = registry.get_template("test-waf")
    
    assert template is not None
    assert template.slug == "test-waf"
```

**Expected**: ✅ PASSED

---

#### Test Case 2.4: Engine Process Agent Result
```python
@pytest.mark.asyncio
async def test_engine_process_agent_result(db_session):
    """Test engine processes agent result and creates DB records."""
    from backend.app.agents_system.checklists.engine import ChecklistEngine
    
    project_id = uuid4()
    agent_result = {
        "AAA_STATE_UPDATE": {
            "wafChecklist": {
                "templates": [{
                    "slug": "waf-2026",
                    "items": [{
                        "id": "item-1",
                        "title": "Test Item",
                        "severity": "high"
                    }]
                }]
            }
        }
    }
    
    engine = ChecklistEngine(lambda: db_session, registry, settings)
    result = await engine.process_agent_result(project_id, agent_result)
    
    assert result["items_processed"] == 1
    
    # Verify DB records created
    checklist = db_session.query(Checklist).filter_by(project_id=project_id).first()
    assert checklist is not None
    assert len(checklist.items) == 1
```

**Expected**: ✅ PASSED

---

#### Test Case 2.5: Sync Idempotency
```python
@pytest.mark.asyncio
async def test_sync_project_state_idempotent(db_session):
    """Test sync can run multiple times without creating duplicates."""
    project_id = uuid4()
    project_state = {
        "wafChecklist": {
            "templates": [{
                "slug": "waf-2026",
                "items": [{"id": "item-1", "title": "Test", "severity": "low"}]
            }]
        }
    }
    
    engine = ChecklistEngine(lambda: db_session, registry, settings)
    
    # Run sync first time
    result1 = await engine.sync_project_state_to_db(project_id, project_state)
    count1 = db_session.query(ChecklistItem).count()
    
    # Run sync second time
    result2 = await engine.sync_project_state_to_db(project_id, project_state)
    count2 = db_session.query(ChecklistItem).count()
    
    # Counts should be identical (no duplicates)
    assert count1 == count2
    assert result1["items_synced"] == result2["items_synced"]
```

**Expected**: ✅ PASSED

---

#### Test Case 2.6: Round-trip Consistency
```python
@pytest.mark.asyncio
async def test_roundtrip_consistency(db_session):
    """Test JSON → DB → JSON produces equivalent structure."""
    project_id = uuid4()
    original_json = {
        "wafChecklist": {
            "templates": [{
                "slug": "waf-2026",
                "items": [
                    {"id": "item-1", "title": "Item 1", "severity": "high"},
                    {"id": "item-2", "title": "Item 2", "severity": "medium"}
                ]
            }]
        }
    }
    
    engine = ChecklistEngine(lambda: db_session, registry, settings)
    
    # Sync to DB
    await engine.sync_project_state_to_db(project_id, original_json)
    
    # Rebuild JSON from DB
    reconstructed_json = await engine.sync_db_to_project_state(project_id)
    
    # Validate consistency
    is_valid, diffs = validate_normalized_consistency(
        original_json, reconstructed_json
    )
    
    assert is_valid, f"Inconsistencies found: {diffs}"
```

**Expected**: ✅ PASSED

---

#### Test Case 2.7: Progress Calculation
```python
@pytest.mark.asyncio
async def test_compute_progress(db_session):
    """Test progress calculation returns correct percentages."""
    project_id = uuid4()
    checklist = Checklist(project_id=project_id, title="Test")
    
    # Create 10 items
    items = []
    for i in range(10):
        item = ChecklistItem(
            checklist=checklist,
            template_item_id=f"item-{i}",
            title=f"Item {i}",
            severity="medium"
        )
        items.append(item)
    
    # Mark 7 as fixed
    for i in range(7):
        eval = ChecklistItemEvaluation(
            item=items[i],
            project_id=project_id,
            evaluator="test",
            status="fixed",
            source_type="manual"
        )
        db_session.add(eval)
    
    db_session.add(checklist)
    db_session.commit()
    
    engine = ChecklistEngine(lambda: db_session, registry, settings)
    progress = await engine.compute_progress(project_id, checklist.id)
    
    assert progress["total_items"] == 10
    assert progress["completed_items"] == 7
    assert progress["percent_complete"] == 70.0
```

**Expected**: ✅ PASSED

---

### Manual Verification

#### Registry Verification

**Step 1: Create Test Template Cache**
```powershell
# Create cache directory
mkdir backend/config/checklists

# Create test template
echo '{
  "slug": "test-waf-2026",
  "title": "Test WAF 2026",
  "version": "1.0",
  "source": "test",
  "source_url": "https://example.com",
  "source_version": "2026-01-01",
  "content": {
    "items": [
      {"id": "item-1", "title": "Test Item", "severity": "high"}
    ]
  }
}' > backend/config/checklists/test-waf-2026.json
```

**Step 2: Test Registry Loading**
```python
# In Python REPL or test script
from backend.app.agents_system.checklists.registry import ChecklistRegistry
from backend.app.config.settings import get_settings

settings = get_settings()
registry = ChecklistRegistry(settings.WAF_TEMPLATE_CACHE_DIR, settings)

# Verify template loaded
template = registry.get_template("test-waf-2026")
print(f"Template: {template.title}")  # Should print: Test WAF 2026

# List all templates
templates = registry.list_templates()
print(f"Total templates: {len(templates)}")  # Should be >= 1
```

**Verify**:
- [ ] Registry loads templates from cache
- [ ] get_template returns correct template
- [ ] list_templates returns all cached templates
- [ ] No errors in loading

---

#### Engine Verification

**Step 3: Test Engine with Mock Data**
```python
# Create test project and agent result
import asyncio
from uuid import uuid4

async def test_engine():
    project_id = uuid4()
    agent_result = {
        "AAA_STATE_UPDATE": {
            "wafChecklist": {
                "templates": [{
                    "slug": "test-waf-2026",
                    "items": [{
                        "id": "item-1",
                        "title": "Enable MFA",
                        "severity": "critical",
                        "description": "Enable multi-factor auth",
                        "pillar": "security",
                        "guidance": {"steps": []},
                        "metadata": {}
                    }]
                }],
                "evaluations": [{
                    "item_id": "item-1",
                    "status": "open",
                    "evaluator": "agent-validator",
                    "source_type": "agent-validation"
                }]
            }
        }
    }
    
    # Process with engine
    from backend.app.agents_system.checklists.engine import ChecklistEngine
    from backend.app.db.session import get_db
    
    async with get_db() as db:
        engine = ChecklistEngine(lambda: db, registry, settings)
        result = await engine.process_agent_result(project_id, agent_result)
        print(f"Result: {result}")
        
        # Verify records created
        from backend.app.models.checklist import Checklist
        checklist = await db.execute(
            select(Checklist).where(Checklist.project_id == project_id)
        )
        checklist = checklist.scalar_one_or_none()
        print(f"Checklist created: {checklist.id}")
        print(f"Items: {len(checklist.items)}")

asyncio.run(test_engine())
```

**Verify**:
- [ ] Engine processes agent result without errors
- [ ] Checklist record created
- [ ] ChecklistItem record created with deterministic ID
- [ ] ChecklistItemEvaluation record created
- [ ] Result summary accurate

---

### Phase 2 Sign-off

**All checks must pass before proceeding to Phase 3**:

- [ ] All code quality checks pass
- [ ] All 7 test cases pass
- [ ] Registry loads templates correctly
- [ ] Engine creates DB records from agent results
- [ ] Sync is idempotent (verified)
- [ ] Round-trip consistency maintained
- [ ] Progress calculation accurate
- [ ] No `Any` types in code
- [ ] All functions have docstrings

**Approved By**: ___________ **Date**: ___________

---

## Phase 3: Integration & API

### Code Quality Verification

```powershell
# Linting
ruff check backend/app/routers/checklists/
ruff check backend/app/agents_system/orchestrator/
ruff check backend/app/agents_system/runner.py
ruff check backend/app/agents_system/agents/router.py

# Type Checking
mypy backend/app/routers/checklists/ --strict
mypy backend/app/agents_system/orchestrator/orchestrator.py --strict

# Formatting
ruff format backend/app/routers/checklists/ --check

# Frontend Types
cd frontend
npm run type-check
```

**Checklist**:
- [ ] No linting errors
- [ ] No type errors in backend
- [ ] No type errors in frontend
- [ ] All API endpoints have response_model
- [ ] All Pydantic schemas defined

---

### Functional Tests

**Test File**: `backend/tests/test_api/test_waf_checklists.py`

#### Test Case 3.1: List Checklists API
```python
def test_list_checklists(client, test_project, test_checklist):
    """Test GET /api/projects/{id}/checklists returns list."""
    response = client.get(f"/api/projects/{test_project.id}/checklists")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "id" in data[0]
    assert "title" in data[0]
```

**Expected**: ✅ PASSED

---

#### Test Case 3.2: Get Checklist Detail API
```python
def test_get_checklist_detail(client, test_project, test_checklist):
    """Test GET /api/projects/{id}/checklists/{id} returns detail."""
    response = client.get(
        f"/api/projects/{test_project.id}/checklists/{test_checklist.id}"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_checklist.id)
    assert "items" in data
    assert isinstance(data["items"], list)
```

**Expected**: ✅ PASSED

---

#### Test Case 3.3: Update Item API
```python
def test_update_checklist_item(client, test_project, test_checklist, test_item):
    """Test PATCH endpoint updates item evaluation."""
    payload = {
        "status": "fixed",
        "evaluator": "manual-user",
        "evidence": {"note": "Implemented MFA"},
        "source_type": "manual"
    }
    
    response = client.patch(
        f"/api/projects/{test_project.id}/checklists/{test_checklist.id}/items/{test_item.id}",
        json=payload
    )
    
    assert response.status_code == 200
    data = response.json()
    # Verify evaluation created
```

**Expected**: ✅ PASSED

---

#### Test Case 3.4: Progress API
```python
def test_get_progress(client, test_project, test_checklist):
    """Test GET progress endpoint returns metrics."""
    response = client.get(
        f"/api/projects/{test_project.id}/checklists/{test_checklist.id}/progress"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total_items" in data
    assert "completed_items" in data
    assert "percent_complete" in data
    assert isinstance(data["percent_complete"], float)
```

**Expected**: ✅ PASSED

---

#### Test Case 3.5: Authorization Check
```python
def test_cannot_access_other_project_checklist(client, test_project, other_project_checklist):
    """Test authorization prevents cross-project access."""
    response = client.get(
        f"/api/projects/{test_project.id}/checklists/{other_project_checklist.id}"
    )
    
    # Should be 404 (not found) or 403 (forbidden)
    assert response.status_code in [403, 404]
```

**Expected**: ✅ PASSED

---

### Integration Tests

**Test File**: `backend/tests/agents_system/test_agent_checklist_integration.py`

#### Test Case 3.6: End-to-End Agent Flow
```python
@pytest.mark.asyncio
async def test_agent_result_to_db_flow(db_session, test_project):
    """Test full flow: agent result → callback → DB update."""
    # Mock agent result with AAA_STATE_UPDATE
    agent_result = {
        "AAA_STATE_UPDATE": {
            "wafChecklist": {
                "templates": [{"slug": "waf-2026", "items": [...]}]
            }
        }
    }
    
    # Trigger orchestrator with callback
    orchestrator = AgentOrchestrator(on_end=checklist_callback)
    result = await orchestrator.run(test_project.id, agent_result)
    
    # Verify DB records created
    checklist = await db_session.execute(
        select(Checklist).where(Checklist.project_id == test_project.id)
    )
    assert checklist.scalar_one_or_none() is not None
```

**Expected**: ✅ PASSED

---

#### Test Case 3.7: Dual-Write Verification
```python
@pytest.mark.asyncio
async def test_dual_write_consistency(db_session, test_project):
    """Test dual-write updates both JSON and DB correctly."""
    # Enable feature flag
    settings.FEATURE_WAF_NORMALIZED = True
    
    # Trigger update via router
    await router.update_project_state(test_project.id, new_state)
    
    # Verify JSON updated
    project_state = await get_project_state(test_project.id)
    assert "wafChecklist" in project_state.state
    
    # Verify DB updated
    checklist = await db_session.execute(
        select(Checklist).where(Checklist.project_id == test_project.id)
    )
    assert checklist.scalar_one_or_none() is not None
    
    # Verify consistency
    reconstructed = await engine.sync_db_to_project_state(test_project.id)
    is_valid, diffs = validate_normalized_consistency(
        project_state.state, reconstructed
    )
    assert is_valid
```

**Expected**: ✅ PASSED

---

### Manual Verification

#### API Testing with curl/Postman

**Step 1: Start Backend**
```powershell
# Ensure backend running
cd backend
uv run uvicorn app.main:app --reload
```

**Step 2: Test List Endpoint**
```powershell
# Replace {project_id} with actual project UUID
curl http://localhost:8000/api/projects/{project_id}/checklists

# Expected: JSON array of checklists
```

**Verify**:
- [ ] Returns 200 OK
- [ ] Returns valid JSON array
- [ ] Each item has required fields (id, title, status, etc.)

---

**Step 3: Test Detail Endpoint**
```powershell
curl http://localhost:8000/api/projects/{project_id}/checklists/{checklist_id}

# Expected: JSON object with checklist and items
```

**Verify**:
- [ ] Returns 200 OK
- [ ] Returns valid JSON object
- [ ] Includes items array
- [ ] Each item has required fields

---

**Step 4: Test Update Endpoint**
```powershell
curl -X PATCH \
  http://localhost:8000/api/projects/{project_id}/checklists/{checklist_id}/items/{item_id} \
  -H "Content-Type: application/json" \
  -d '{
    "status": "fixed",
    "evaluator": "test-user",
    "evidence": {"note": "Test"},
    "source_type": "manual"
  }'

# Expected: 200 OK with updated item
```

**Verify**:
- [ ] Returns 200 OK
- [ ] Evaluation created in database
- [ ] Response includes updated item

---

**Step 5: Test Progress Endpoint**
```powershell
curl http://localhost:8000/api/projects/{project_id}/checklists/{checklist_id}/progress

# Expected: JSON with progress metrics
```

**Verify**:
- [ ] Returns 200 OK
- [ ] Includes total_items, completed_items, percent_complete
- [ ] Percentages calculated correctly

---

**Step 6: Test OpenAPI Documentation**
```powershell
# Open browser to:
http://localhost:8000/docs

# Navigate to checklists section
```

**Verify**:
- [ ] All endpoints visible in docs
- [ ] Request/response schemas documented
- [ ] Can execute test requests from docs UI

---

### Phase 3 Sign-off

**All checks must pass before proceeding to Phase 4**:

- [ ] All code quality checks pass
- [ ] All 7 functional tests pass
- [ ] All API endpoints functional
- [ ] API documentation generated correctly
- [ ] Integration tests pass (agent → DB flow)
- [ ] Dual-write mode works correctly
- [ ] Manual API testing successful
- [ ] Frontend types aligned with backend

**Approved By**: ___________ **Date**: ___________

---

## Phase 4: Backfill, Testing & Documentation

### Backfill Script Verification

#### Test Case 4.1: Dry-Run Mode
```powershell
# Run backfill in dry-run mode
uv python scripts/backfill_waf.py backfill --dry-run --batch-size 10

# Expected output:
# DRY-RUN: Would process 10 projects
# DRY-RUN: Validation successful
# No errors detected
```

**Verify**:
- [ ] Script runs without errors
- [ ] No database writes performed
- [ ] Validation logic executed
- [ ] Summary statistics displayed

---

#### Test Case 4.2: Single Project Backfill
```powershell
# Backfill a single test project
uv python scripts/backfill_waf.py backfill-project <project-uuid>

# Check result
```

**Verify**:
- [ ] Project backfilled successfully
- [ ] Records created in database
- [ ] Idempotent (can run again)

---

#### Test Case 4.3: Progress Command
```powershell
uv python scripts/backfill_waf.py progress

# Expected output:
# Backfill Progress:
# Total projects: 100
# Migrated: 50
# Remaining: 50
# Completion: 50.0%
```

**Verify**:
- [ ] Displays accurate counts
- [ ] Percentage calculated correctly

---

#### Test Case 4.4: Verification Command
```powershell
uv python scripts/backfill_waf.py verify --sample-size 5

# Expected output:
# Verification Report:
# Sample size: 5
# Passed: 5
# Failed: 0
```

**Verify**:
- [ ] Random sample selected
- [ ] Consistency checked
- [ ] Report generated

---

### Test Coverage Verification

```powershell
# Run tests with coverage
uv python -m pytest backend/tests/ --cov=backend/app --cov-report=html --cov-report=term

# Open coverage report
start coverage/index.html  # Windows
```

**Verify**:
- [ ] Overall coverage > 80%
- [ ] New code coverage > 90%
- [ ] Critical paths covered (engine, service, API)

---

### Documentation Verification

#### Checklist for WAF_NORMALIZED_DB.md

- [ ] Overview section complete
- [ ] Schema diagrams included
- [ ] All tables documented
- [ ] API reference with examples
- [ ] Backfill runbook with step-by-step instructions
- [ ] Configuration reference complete
- [ ] FAQ section addresses common questions
- [ ] Code examples tested and working
- [ ] Links to related docs working

---

#### Checklist for FRONTEND_INTEGRATION.md

- [ ] Type definitions documented
- [ ] API client examples provided
- [ ] UI component specs complete
- [ ] State management explained
- [ ] Error handling covered

---

#### Checklist for Updates to UX_IDE_WORKFLOW.md

- [ ] Checklist lifecycle section added
- [ ] Screenshots or diagrams included (if applicable)
- [ ] User workflows documented
- [ ] Edge cases covered

---

### Phase 4 Sign-off

**All checks must pass before proceeding to Phase 5**:

- [ ] Backfill script functional (dry-run, execute, verify)
- [ ] All unit tests passing (>80% coverage)
- [ ] All integration tests passing
- [ ] All API tests passing
- [ ] Documentation complete and accurate
- [ ] Documentation reviewed and approved
- [ ] Code quality checks pass
- [ ] No critical bugs outstanding

**Approved By**: ___________ **Date**: ___________

---

## Phase 5: Deployment & Operations

### Pre-Deployment Checklist

**Staging Environment**:
- [ ] Code deployed to staging
- [ ] Migration run successfully
- [ ] Database schema verified
- [ ] Backfill completed (dry-run)
- [ ] Backfill executed
- [ ] Verification passed
- [ ] Feature flag enabled
- [ ] Monitoring configured
- [ ] Alerts tested

**Production Readiness**:
- [ ] Staging validated (7+ days)
- [ ] All metrics within targets
- [ ] No P0/P1 bugs
- [ ] Database backup completed
- [ ] Rollback plan tested
- [ ] Maintenance window scheduled (if needed)
- [ ] Stakeholders notified
- [ ] Documentation published

---

### Deployment Verification

#### Staging Verification

**Day 1-3: Initial Validation**
- [ ] Migration runs without errors
- [ ] Backfill completes successfully
- [ ] API endpoints functional
- [ ] No error spikes in logs
- [ ] Performance within SLA

**Day 4-7: Monitoring Period**
- [ ] Consistency checks passing (>99.5%)
- [ ] No data loss incidents
- [ ] Error rate < 0.1%
- [ ] API latency < 500ms (p95)
- [ ] User acceptance testing complete

---

#### Production Verification

**Pre-Cutover**:
- [ ] Database backup verified
- [ ] Backfill dry-run passed
- [ ] Team ready for monitoring

**During Migration**:
- [ ] Migration starts: ___ (timestamp)
- [ ] Migration completes: ___ (timestamp)
- [ ] Duration: ___ minutes
- [ ] Errors: ___ (count)

**Post-Migration** (first 4 hours):
- [ ] Hour 1: Verification passed, spot checks OK
- [ ] Hour 2: API endpoints stable, no error spikes
- [ ] Hour 3: Monitoring dashboards healthy
- [ ] Hour 4: User traffic nominal, no issues reported

**First 24 Hours**:
- [ ] Metrics within normal ranges
- [ ] No P0/P1 incidents
- [ ] Error rate normal
- [ ] Performance acceptable

---

### Gradual Rollout Verification

**Day 1: 10% Rollout**
- [ ] Feature enabled for 10% of projects
- [ ] Metrics tracking 10% cohort
- [ ] No anomalies detected
- [ ] Decision: Proceed / Hold / Rollback

**Day 2: 25% Rollout**
- [ ] Feature enabled for 25% of projects
- [ ] Comparison: 10% vs 25% cohorts
- [ ] Performance stable
- [ ] Decision: Proceed / Hold / Rollback

**Day 3: 50% Rollout**
- [ ] Feature enabled for 50% of projects
- [ ] Majority of traffic on new system
- [ ] No major issues
- [ ] Decision: Proceed / Hold / Rollback

**Day 4: 75% Rollout**
- [ ] Feature enabled for 75% of projects
- [ ] System handling load well
- [ ] Edge cases handled
- [ ] Decision: Proceed / Hold / Rollback

**Day 5: 100% Rollout**
- [ ] Feature enabled for all projects
- [ ] Full migration complete
- [ ] Legacy JSON path deprecated (read-only)
- [ ] Celebration! 🎉

---

### Monitoring Dashboard Verification

**Metrics to Verify**:
- [ ] `waf_sync_counter` incrementing correctly
- [ ] `waf_sync_duration` within target (< 1s p95)
- [ ] `waf_evaluation_counter` tracking evaluations
- [ ] `waf_progress_gauge` updating per project
- [ ] Backfill progress reaching 100%

**Alerts to Verify**:
- [ ] HighWafSyncErrorRate alert configured
- [ ] WafSyncDurationHigh alert configured
- [ ] WafBackfillStalled alert configured
- [ ] Alerts fire when thresholds exceeded (test in staging)
- [ ] On-call runbook updated with alert responses

---

### Final Sign-off

**Implementation Complete**:
- [ ] All phases completed (1-5)
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Staging validation successful
- [ ] Production deployment successful
- [ ] Gradual rollout complete (100%)
- [ ] Monitoring operational
- [ ] No critical issues

**Success Metrics Achieved**:
- [ ] Data loss: 0 incidents ✅
- [ ] Consistency: < 0.5% mismatch ✅
- [ ] Performance: < 500ms API (p95) ✅
- [ ] Coverage: > 80% test coverage ✅
- [ ] Uptime: > 99.9% ✅

**Project Closure**:
- [ ] Postmortem document created
- [ ] Lessons learned documented
- [ ] Future improvements identified
- [ ] Team debriefed

**Final Approval**:
- **Implementation Lead**: ___________ **Date**: ___________
- **QA Lead**: ___________ **Date**: ___________
- **Operations Lead**: ___________ **Date**: ___________
- **Product Owner**: ___________ **Date**: ___________

---

## Troubleshooting Guide

### Common Issues & Solutions

#### Issue: Migration Fails with "Column Already Exists"
**Cause**: Migration run twice or schema conflict  
**Solution**:
```powershell
alembic downgrade -1
alembic upgrade head
```

#### Issue: Tests Fail with "No Such Table"
**Cause**: Test database not migrated  
**Solution**:
```powershell
# Ensure test database has migrations
alembic -x testing upgrade head
```

#### Issue: Backfill Produces Duplicates
**Cause**: Not using deterministic IDs  
**Solution**: Verify `compute_deterministic_item_id` used everywhere

#### Issue: Verification Reports High Mismatch Rate
**Cause**: Schema change or data corruption  
**Solution**: Investigate specific mismatches, fix data, re-run backfill

#### Issue: API Returns 500 Errors
**Cause**: Various (check logs)  
**Solution**:
```powershell
# Check logs
tail -f backend/logs/app.log | grep ERROR

# Common fixes:
# - DB connection issues: check connection string
# - Missing records: check FKs
# - Type errors: check request payload
```

---

**End of Verification & Testing Checklist**

*This document should be used alongside PROGRESS_TRACKER.md to ensure quality at every step.*
