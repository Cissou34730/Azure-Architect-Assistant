# Prompt for Coding Agent: WAF Checklist Normalization Implementation

## Context

You are implementing the WAF (Well-Architected Framework) Checklist Normalization project for the Azure Architect Assistant application. This project migrates checklist data from denormalized JSON storage in `ProjectState.state` to normalized relational database tables.

## Your Mission

Implement the complete WAF normalization system following the detailed specifications in the implementation package located at:

```
docs/waf_normalization_implementation/
```

## Documentation Package Overview

You have access to a comprehensive implementation package with 8 documents (~20,000 lines):

1. **README.md** - Start here for navigation and overview
2. **IMPLEMENTATION_SUMMARY.md** - Executive summary and project context
3. **DETAILED_IMPLEMENTATION_PLAN.md** - Your primary reference (11,500+ lines with exact specifications)
4. **PROGRESS_TRACKER.md** - Use this to track your progress and mark tasks complete
5. **QUICK_REFERENCE.md** - Quick lookups for file paths, commands, schemas
6. **VERIFICATION_TESTING_CHECKLIST.md** - Quality assurance procedures after each task
7. **VISUAL_MAP.md** - Visual overview of architecture and phases
8. **PACKAGE_INDEX.md** - Complete package documentation index

## Implementation Approach

### Phase-by-Phase Execution

Implement in **5 sequential phases**. Complete each phase fully before moving to the next:

1. **Phase 1: Schema, Models & Migration** (2-3 days)
2. **Phase 2: Core Services & Engine** (3-5 days)
3. **Phase 3: Integration & API** (2-4 days)
4. **Phase 4: Backfill, Testing & Documentation** (3-5 days)
5. **Phase 5: Deployment & Operations** (1-3 days + monitoring)

### Your Workflow for Each Phase

For each phase, follow this workflow:

1. **Read Phase Overview**: Review the phase section in `DETAILED_IMPLEMENTATION_PLAN.md`
2. **Understand Tasks**: Read all tasks in the phase carefully
3. **Implement Tasks Sequentially**: Complete each task following the specifications
4. **Verify After Each Task**: Use `VERIFICATION_TESTING_CHECKLIST.md` to verify your work
5. **Update Tracker**: Update `PROGRESS_TRACKER.md` after completing each task (mark checkboxes, update status)
6. **Phase Sign-off**: Complete all phase verification steps
7. **Commit Phase**: Make a git commit for the completed phase with descriptive message (e.g., `feat(waf): Complete Phase 1 - Database Schema and Models`)

## Critical Requirements

### Code Quality Standards (Non-Negotiable)

✅ **Type Safety**:
- Python: Use explicit type hints everywhere, NO `Any` types allowed
- TypeScript: Use explicit types everywhere, NO `any` types allowed
- Run `mypy backend/app/ --strict` - must pass with zero errors
- Run `npm run type-check` in frontend - must pass

✅ **Linting & Formatting**:
- Python: Run `ruff check backend/` and `ruff format backend/`
- TypeScript: Run `eslint .` from frontend directory
- All checks must pass before moving to next task

✅ **Testing**:
- Write tests as you implement (not after)
- Target >80% code coverage for new code
- Backend: All pytest tests must pass: `pytest backend/tests/ -v`
- Frontend: Use Playwright for E2E tests: `npx playwright test`
- Run tests after each significant change
- **DO NOT** run full backend server for testing - use pytest and mocked dependencies

✅ **Documentation**:
- All classes must have docstrings
- All public methods must have docstrings with Args, Returns, Raises
- Complex logic must have inline comments
- Update PROGRESS_TRACKER.md as you complete tasks

### Architecture Principles

✅ **Idempotency**: All sync operations must be repeatable without side effects
✅ **Deterministic IDs**: Use UUID v5 for ChecklistItem IDs (never random UUIDs)
✅ **Chunked Processing**: Process large datasets in chunks (500 items/transaction)
✅ **Feature Flagged**: All new behavior controlled by `FEATURE_WAF_NORMALIZED`
✅ **Dual-Write**: During transition, write to both JSON and DB
✅ **Error Handling**: Don't crash on errors - log and continue or rollback transaction

## Starting Point

### Step 1: Orientation (15 minutes)

Read these files in order to understand the full context:

1. `docs/waf_normalization_implementation/README.md`
2. `docs/waf_normalization_implementation/IMPLEMENTATION_SUMMARY.md`
3. `docs/waf_normalization_implementation/VISUAL_MAP.md`

This gives you the full context and visual overview.

### Step 2: Verify Your Environment

You're already in the workspace. Verify the environment is ready:

```powershell
# Verify backend dependencies (run from backend folder)
uv sync

# Verify frontend dependencies (run from frontend folder)
npm install

# Verify database connection (run from backend folder)
alembic current
```

If any of these fail, address the issues before proceeding.

### Step 3: Begin Phase 1

Read the **Phase 1: Schema, Models & Migration** section in `docs/waf_normalization_implementation/DETAILED_IMPLEMENTATION_PLAN.md`.

Once you understand Phase 1, start implementing **Task 1.1: Create SQLAlchemy Models**.

## Task Execution Pattern

For each task, follow this pattern:

### 1. Read Task Specification

In `DETAILED_IMPLEMENTATION_PLAN.md`, each task has:
- **File**: Exact file path to create/modify
- **What to Implement**: Detailed description of what to build
- **Quality Checks**: Verification steps

Example:
```
Task 1.1: Create SQLAlchemy Models
File: backend/app/models/checklist.py (NEW)
What to Implement: [detailed specification]
Quality Checks: [checklist]
```

### 2. Implement

- Create or modify the file as specified
- Follow the code structure guidelines exactly
- Use the type signatures and patterns shown
- Refer to `QUICK_REFERENCE.md` for schemas, settings, function signatures

### 3. Verify Immediately

After implementing each task, run these checks:

```powershell
# Type checking
mypy backend/app/models/checklist.py --strict

# Linting
ruff check backend/app/models/checklist.py

# Formatting
ruff format backend/app/models/checklist.py

# If tests exist for this task, run them
pytest backend/tests/models/test_checklist_models.py -v
```

All checks must pass before moving to next task.

### 4. Update Progress Tracker

Update `docs/waf_normalization_implementation/PROGRESS_TRACKER.md` immediately after completing each task:
- Check the box `[ ]` → `[x]` for the completed task
- Update status fields (% complete, current focus, etc.)
- Document any issues or blockers encountered
- Add notes if you deviated from the plan

This keeps your progress visible and helps track what's been done.

## Phase-Specific Guidance

### Phase 1: Database Foundation

**Focus**: Get the schema right. Everything else depends on it.

Key files to create:
- `backend/app/models/checklist.py` (4 models)
- `backend/migrations/versions/<timestamp>_create_waf_normalized.py`
- Update `backend/app/config/settings.py`

**Critical**: 
- Use deterministic UUID v5 for ChecklistItem.id
- Add all indexes specified
- Test migration both ways (upgrade and downgrade)

**Verification**:
```powershell
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

**Phase Completion**:
After all Phase 1 tasks are complete and verified, commit your work:
```powershell
git add backend/app/models/checklist.py backend/migrations/ backend/app/config/settings.py
git commit -m "feat(waf): Complete Phase 1 - Database schema and models

- Add ChecklistTemplate, Checklist, ChecklistItem, ChecklistItemEvaluation models
- Create Alembic migration with indexes and foreign keys
- Add WAF_NORMALIZED feature flag and settings"
```

### Phase 2: Core Logic

**Focus**: Implement the engine that powers everything.

Key files to create:
- `backend/app/agents_system/checklists/registry.py`
- `backend/app/agents_system/checklists/engine.py`
- `backend/app/agents_system/checklists/service.py`
- `backend/app/services/normalize_helpers.py`

**Critical**:
- Make sync operations idempotent (test by running twice)
- Implement chunking for large datasets
- Add comprehensive error handling

**Verification**:
```powershell
# Test idempotency with pytest
pytest backend/tests/services/test_checklist_engine.py::test_sync_idempotency -v

# Test chunking
pytest backend/tests/services/test_checklist_engine.py::test_chunked_processing -v
```

**Phase Completion**:
```powershell
git add backend/app/agents_system/checklists/ backend/app/services/normalize_helpers.py
git commit -m "feat(waf): Complete Phase 2 - Core services and engine

- Implement ChecklistRegistry for template management
- Create ChecklistEngine with sync operations
- Add idempotent sync_project_state_to_db and sync_db_to_project_state
- Implement chunked processing for large datasets"
```

### Phase 3: Integration

**Focus**: Hook into existing agent system and expose APIs.

Key files to modify:
- `backend/app/agents_system/orchestrator/orchestrator.py`
- `backend/app/agents_system/runner.py`
- `backend/app/agents_system/agents/router.py`

Key files to create:
- `backend/app/routers/checklists/checklist_router.py`
- `backend/app/routers/checklists/schemas.py`

**Critical**:
- Don't break existing agent flows
- Test API endpoints with pytest (not by running full backend)
- Align frontend types with backend schemas

**Verification**:
```powershell
# Test API endpoints with pytest
pytest backend/tests/routers/test_checklist_router.py -v

# Test agent integration
pytest backend/tests/agents/test_checklist_integration.py -v

# For frontend integration tests (if applicable)
pytest frontend/tests/ --headed  # or use playwright
```

### Phase 4: Testing & Documentation

**Focus**: Comprehensive tests and operational docs.

**Critical**:
- Write tests as you go (not at the end)
- Aim for >80% coverage
- Test both success and error cases
- Document backfill procedures thoroughly

**Verification**:
```powershell
# Run all pytest tests
pytest backend/tests/ -v --cov=backend/app --cov-report=html

# Check coverage report
Start-Process backend/htmlcov/index.html

# Run Playwright E2E tests
npx playwright test

# Generate Playwright report
npx playwright show-report
```

**Phase Completion**:
```powershell
git add backend/tests/ scripts/ docs/ frontend/tests/
git commit -m "feat(waf): Complete Phase 4 - Testing and documentation

- Add comprehensive pytest test suite (>80% coverage)
- Create backfill and maintenance scripts
- Add Playwright E2E tests for frontend integration
- Document operational procedures in WAF_NORMALIZED_DB.md
- Update FRONTEND_INTEGRATION.md and UX_IDE_WORKFLOW.md"
```

### Phase 5: Deployment

**Focus**: Safe production rollout.

**Critical**:
- Test backfill in staging first
- Use dry-run mode before execute
- Monitor metrics closely
- Have rollback plan ready

This phase is mostly operational - follow the runbook exactly.

**Phase Completion**:
```powershell
git add backend/app/config/ docs/
git commit -m "feat(waf): Complete Phase 5 - Deployment preparation

- Finalize deployment runbook and rollback procedures
- Document gradual rollout plan (10% -> 100%)
- Add monitoring and alerting configurations
- Complete all operational documentation"
```

## Key Reference Documents

Keep these open while working:

### During Coding
- **Primary**: `DETAILED_IMPLEMENTATION_PLAN.md` (current phase)
- **Reference**: `QUICK_REFERENCE.md` (schemas, commands, patterns)
- **Tracking**: `PROGRESS_TRACKER.md` (mark tasks complete)

### During Testing
- **Primary**: `VERIFICATION_TESTING_CHECKLIST.md` (test procedures)
- **Reference**: `QUICK_REFERENCE.md` (test commands)

### For Questions
- **Architecture**: `VISUAL_MAP.md` (see the big picture)
- **Context**: `IMPLEMENTATION_SUMMARY.md` (understand why)

## Common Pitfalls to Avoid

❌ **Don't**:
- Skip verification steps (they catch issues early)
- Use `Any` type in Python or TypeScript
- Create random UUIDs for ChecklistItem (use deterministic!)
- Process all items in one transaction (use chunking!)
- Forget to update PROGRESS_TRACKER.md
- Move to next phase without completing current phase

✅ **Do**:
- Read task specifications completely before coding
- Run type checking and linting after each change
- Write tests as you implement (pytest for backend, Playwright for frontend)
- Update PROGRESS_TRACKER.md after completing each task
- Commit at the end of each phase with descriptive message
- Ask for clarification if specification unclear

## Success Metrics

Your implementation is successful when:

✅ **Functionality**:
- [ ] All 30+ tasks completed
- [ ] Migration runs both ways (up and down)
- [ ] Backfill is idempotent (run twice = same result)
- [ ] API endpoints return expected data
- [ ] Agent integration works without breaking existing flows

✅ **Quality**:
- [ ] mypy --strict passes with zero errors
- [ ] ruff check passes with zero errors
- [ ] Test coverage >80% for new code
- [ ] All 58 test cases passing
- [ ] No `Any` types anywhere

✅ **Documentation**:
- [ ] All public APIs have docstrings
- [ ] PROGRESS_TRACKER.md fully updated
- [ ] New operational docs created (Phase 4)

## Getting Help

If you encounter issues:

1. **Check Documentation First**:
   - `QUICK_REFERENCE.md` → Common pitfalls section
   - `VERIFICATION_TESTING_CHECKLIST.md` → Troubleshooting guide
   - `DETAILED_IMPLEMENTATION_PLAN.md` → Specific task details

2. **Common Issues**:
   - Type errors? Review type signatures in QUICK_REFERENCE.md
   - Tests failing? Check test case specifications in VERIFICATION_TESTING_CHECKLIST.md
   - Migration issues? Review migration section in DETAILED_IMPLEMENTATION_PLAN.md

3. **Document Blockers**:
   - Add to PROGRESS_TRACKER.md under "Blockers" section
   - Include: what you tried, error messages, context

## Deliverables Checklist

At the end of implementation, you should have:

### Code Deliverables
- [ ] 16 new files created (models, services, API, tests, scripts)
- [ ] 6 files modified (integration points, config, types)
- [ ] 1 Alembic migration (up and down)
- [ ] All code type-checked and linted

### Test Deliverables
- [ ] 8 test files created
- [ ] 58 test cases implemented
- [ ] All tests passing
- [ ] Coverage >80%

### Documentation Deliverables
- [ ] WAF_NORMALIZED_DB.md created
- [ ] FRONTEND_INTEGRATION.md created
- [ ] UX_IDE_WORKFLOW.md updated
- [ ] PROGRESS_TRACKER.md fully updated

### Operational Deliverables
- [ ] Backfill scripts working (dry-run and execute)
- [ ] Maintenance scripts working
- [ ] Verification reports passing

## Final Notes

This is a **large, complex project** (11-20 days of work). Take it **phase by phase**:

1. **Don't rush** - follow the specifications exactly
2. **Verify constantly** - run checks after each task
3. **Test as you go** - don't leave testing for the end
4. **Track progress** - update PROGRESS_TRACKER.md daily
5. **Ask questions** - if specification unclear, document the question

The implementation package provides everything you need to succeed. Trust the specifications, follow the workflow, and verify at each step.

## Your First Action

Start here:

1. **Read** `docs/waf_normalization_implementation/DETAILED_IMPLEMENTATION_PLAN.md`
2. **Navigate to** Phase 1, Task 1.1: Create SQLAlchemy Models
3. **Read** the complete task specification
4. **Create** `backend/app/models/checklist.py` with the 4 models as specified
5. **Verify** your implementation with type checking and linting
6. **Mark complete** in `PROGRESS_TRACKER.md`

Good luck! 🚀

---

**Ready to begin?** Start with Phase 1, Task 1.1 in DETAILED_IMPLEMENTATION_PLAN.md!
