# WAF Normalization - Quick Reference Card

**Print this or keep it open for quick reference during implementation!**

---

## 🎯 Core Concepts

| Concept | Description |
|---------|-------------|
| **Template** | Pre-defined WAF checklist structure from Microsoft Learn (fetched once, cached) |
| **Checklist** | Instance of a template for a specific project |
| **Item** | Individual checklist recommendation (e.g., "Enable MFA") |
| **Evaluation** | Status/result for an item (open, fixed, false-positive) |
| **Dual-Write** | Writing to both JSON and DB during rollout for safety |
| **Deterministic ID** | UUID v5 generated from project+template+item (ensures idempotency) |

---

## 📁 Key Files & Locations

### Models & Schema
```
backend/app/models/checklist.py               # 4 SQLAlchemy models
backend/migrations/versions/<ts>_create...py  # Alembic migration
```

### Core Services
```
backend/app/agents_system/checklists/
├── registry.py           # Template cache management
├── engine.py            # Core sync and processing logic
├── service.py           # FastAPI dependency wrapper
└── __init__.py

backend/app/services/
└── normalize_helpers.py  # JSON ↔ DB conversion functions
```

### API & Integration
```
backend/app/routers/checklists/
├── checklist_router.py   # REST API endpoints
├── schemas.py           # Pydantic request/response models
└── __init__.py

backend/app/agents_system/
├── orchestrator/orchestrator.py  # Add on_end callback
├── runner.py                     # Register callback
└── agents/router.py              # Call sync after state update
```

### CLI Scripts
```
scripts/
├── backfill_waf.py          # Backfill CLI (backfill, verify, progress)
└── maintain_checklists.py   # Maintenance CLI (sync, stats, cleanup)
```

### Configuration
```
backend/app/config/settings.py  # Add WAF_* settings
```

### Tests
```
backend/tests/
├── models/test_checklist_models.py
├── services/
│   ├── test_normalize_helpers.py
│   ├── test_checklist_service.py
│   └── test_backfill.py
├── agents_system/
│   ├── test_checklist_engine.py
│   └── test_agent_checklist_integration.py
└── test_api/
    └── test_waf_checklists.py
```

### Frontend
```
frontend/src/types/api-artifacts.ts  # Add ChecklistSummary, etc.
```

---

## 📊 Database Schema Quick Reference

### ChecklistTemplate
- `id` (UUID PK), `slug` (unique), `title`, `version`
- `source`, `source_url`, `source_version`
- `content` (JSONB - full template)
- Relationships: → many Checklists

### Checklist
- `id` (UUID PK), `project_id` (FK), `template_id` (FK)
- `title`, `status` (open/archived)
- Relationships: → many Items, ← Project, ← Template

### ChecklistItem
- `id` (UUID PK - **deterministic!**), `checklist_id` (FK)
- `template_item_id`, `title`, `description`
- `pillar`, `severity` (low/med/high/critical)
- `guidance` (JSONB), `metadata` (JSONB)
- Relationships: → many Evaluations, ← Checklist

### ChecklistItemEvaluation
- `id` (UUID PK), `item_id` (FK), `project_id` (FK)
- `evaluator`, `status` (open/in_progress/fixed/false_positive)
- `score`, `evidence` (JSONB)
- `source_type`, `source_id` (for dedup)
- Relationships: ← Item, ← Project

---

## 🔧 Configuration Settings

```python
# In backend/app/config/settings.py

FEATURE_WAF_NORMALIZED: bool = False              # Enable dual-write
WAF_NAMESPACE_UUID: UUID = "3a7e8c2f-..."        # For deterministic IDs
WAF_TEMPLATE_CACHE_DIR: Path = "backend/config/checklists"
WAF_BACKFILL_BATCH_SIZE: int = 50                # Projects per batch
WAF_SYNC_CHUNK_SIZE: int = 500                   # Items per transaction
```

---

## 🔑 Key Functions & Methods

### Engine (ChecklistEngine)
```python
# Process agent results
await engine.process_agent_result(project_id, agent_result) -> dict

# Sync ProjectState → DB (backfill)
await engine.sync_project_state_to_db(project_id, state, chunk_size) -> dict

# Sync DB → ProjectState (rebuild JSON)
await engine.sync_db_to_project_state(project_id) -> dict

# Evaluate item manually
await engine.evaluate_item(project_id, item_id, payload) -> Evaluation

# Get uncovered items
await engine.list_next_actions(project_id, limit, severity) -> list[dict]

# Calculate progress
await engine.compute_progress(project_id, checklist_id) -> dict
```

### Normalization Helpers
```python
# Generate stable ID
compute_deterministic_item_id(project_id, template_slug, item_id, namespace) -> UUID

# JSON → DB format
normalize_waf_item(item_dict, project_id, template_slug, namespace) -> dict
normalize_waf_evaluation(eval_dict, item_id, project_id) -> dict

# DB → JSON format
denormalize_checklist_to_json(checklist, items, evaluations) -> dict

# Verify consistency
validate_normalized_consistency(original, reconstructed) -> (bool, list[str])
```

### Registry (ChecklistRegistry)
```python
# Get cached template
registry.get_template(slug) -> Optional[ChecklistTemplate]

# List all templates
registry.list_templates() -> list[ChecklistTemplate]

# Register new template
registry.register_template(template) -> None

# Reload cache
registry.refresh_from_cache() -> int
```

---

## 🚀 CLI Commands

### Backfill
```powershell
# Dry-run (validate without writing)
uv python scripts/backfill_waf.py backfill --dry-run --batch-size 50

# Execute backfill
uv python scripts/backfill_waf.py backfill --batch-size 50 --verify

# Single project
uv python scripts/backfill_waf.py backfill-project <uuid>

# Check progress
uv python scripts/backfill_waf.py progress

# Verify consistency
uv python scripts/backfill_waf.py verify --sample-size 10
```

### Maintenance
```powershell
# Refresh templates from Microsoft Learn
uv python scripts/maintain_checklists.py refresh-templates

# Sync project
uv python scripts/maintain_checklists.py sync-project <uuid> --direction to-db

# Show stats
uv python scripts/maintain_checklists.py stats

# Cleanup orphans
uv python scripts/maintain_checklists.py cleanup --dry-run
```

### Database
```powershell
# Run migration
alembic upgrade head

# Revert migration
alembic downgrade -1

# Check current version
alembic current
```

---

## 🧪 Testing Commands

```powershell
# All tests
uv python -m pytest backend/tests/ -v

# Specific test file
uv python -m pytest backend/tests/services/test_normalize_helpers.py -v

# With coverage
uv python -m pytest backend/tests/ --cov=backend/app --cov-report=html

# Only checklist-related tests
uv python -m pytest backend/tests/ -k "checklist" -v

# Fast unit tests only
uv python -m pytest backend/tests/ -m unit

# Integration tests
uv python -m pytest backend/tests/ -m integration
```

---

## 🔍 Code Quality Commands

```powershell
# Linting
ruff check backend/app/models/checklist.py
ruff check backend/app/agents_system/checklists/
ruff check backend/app/routers/checklists/

# Auto-fix linting issues
ruff check --fix backend/

# Formatting
ruff format backend/

# Type checking
mypy backend/app/models/checklist.py
mypy backend/app/agents_system/checklists/
mypy backend/app/routers/checklists/

# Type check with strict mode
mypy --strict backend/app/agents_system/checklists/engine.py
```

---

## 📋 API Endpoints Quick Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/projects/{id}/checklists` | List checklists |
| GET | `/api/projects/{id}/checklists/{cid}` | Get checklist detail |
| PATCH | `/api/projects/{id}/checklists/{cid}/items/{iid}` | Update item |
| POST | `/api/projects/{id}/checklists/{cid}/items/{iid}/evaluate` | Evaluate item |
| GET | `/api/projects/{id}/checklists/{cid}/progress` | Get progress |
| POST | `/api/projects/{id}/checklists/resync` | Trigger resync |

---

## ⚠️ Common Pitfalls & Solutions

### Issue: Duplicate ChecklistItems Created
**Cause**: Not using deterministic IDs  
**Solution**: Always use `compute_deterministic_item_id()` with namespace UUID

### Issue: Sync Fails with Transaction Error
**Cause**: Processing too many items in one transaction  
**Solution**: Use chunking with `WAF_SYNC_CHUNK_SIZE` setting

### Issue: Verification Shows Inconsistencies
**Cause**: JSON structure changed but DB not updated  
**Solution**: Re-run backfill for affected projects

### Issue: Feature Flag Not Working
**Cause**: Settings not reloaded after change  
**Solution**: Restart backend service after changing `FEATURE_WAF_NORMALIZED`

### Issue: Migration Fails
**Cause**: Existing data conflicts with new constraints  
**Solution**: Check for orphaned records, clean up before migration

### Issue: Tests Fail with "Table Not Found"
**Cause**: Test DB not migrated  
**Solution**: Run `alembic upgrade head` on test database

---

## 📊 Success Metrics Thresholds

| Metric | Target | Status |
|--------|--------|--------|
| Type Safety | 100% (no Any) | ⚠️ Required |
| Test Coverage | > 80% | ⚠️ Required |
| API Response Time (p95) | < 500ms | ⚠️ Required |
| Data Loss | 0 incidents | 🚨 Critical |
| Consistency | < 0.5% mismatch | ⚠️ Required |
| Backfill Throughput | > 10 projects/sec | ℹ️ Target |
| Error Rate | < 0.1% | ⚠️ Required |

---

## 🎯 Phase Checklist Summary

- [ ] **Phase 1**: Models + Migration + Config (2-3 days)
- [ ] **Phase 2**: Registry + Engine + Helpers (3-5 days)
- [ ] **Phase 3**: Integration + API + FE Types (2-4 days)
- [ ] **Phase 4**: Tests + Docs + Backfill Scripts (3-5 days)
- [ ] **Phase 5**: Staging Deploy → Monitor → Prod Deploy (1-3 days + 7-14 days monitoring)

**Total**: 11-20 days implementation + monitoring period

---

## 🔗 Quick Links

- **[Detailed Implementation Plan](./DETAILED_IMPLEMENTATION_PLAN.md)** - Full specifications
- **[Progress Tracker](./PROGRESS_TRACKER.md)** - Checklist for tracking
- **[Main README](./README.md)** - Implementation folder overview
- **[Original Plan](../plan-normalizeWafChecklistToDb.prompt.prompt.md)** - Context and rationale

---

## 💡 Pro Tips

1. **Start with models**: Get schema right first, everything else follows
2. **Use deterministic IDs**: Prevents duplicates and makes debugging easier
3. **Test idempotency**: Run sync twice, should be identical
4. **Feature flag everything**: Makes rollback trivial
5. **Monitor from day 1**: Instrument as you build, not after
6. **Document as you go**: Don't leave it for the end
7. **Small commits**: Easier to review and rollback if needed
8. **Verify before moving on**: Each phase's verification must pass

---

**Keep this handy! Print it, pin it, or keep it open in a second monitor.**

*Last Updated: February 4, 2026*
