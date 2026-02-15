# WAF Normalization - Visual Implementation Map

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    WAF CHECKLIST NORMALIZATION PROJECT                        ║
║                         11-20 Days Implementation                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝

┌───────────────────────────────────────────────────────────────────────────────┐
│ 📋 GOAL: Migrate WAF checklists from denormalized JSON → normalized DB tables │
│ 🎯 OUTCOME: Enable analytics, agent updates, consistency, and performance     │
└───────────────────────────────────────────────────────────────────────────────┘


╔═══════════════════════════════════════════════════════════════════════════════╗
║                              PHASE 1: FOUNDATION                              ║
║                              Days 1-3 (2-3 days)                              ║
╚═══════════════════════════════════════════════════════════════════════════════╝

    🗄️  DATABASE SCHEMA
    ┌─────────────────────────────────────────────────────────────────────┐
    │  ChecklistTemplate          Checklist                               │
    │  ┌──────────────┐          ┌──────────────┐                        │
    │  │ id (PK)      │──────────│ template_id  │                        │
    │  │ slug (unique)│          │ project_id   │                        │
    │  │ title        │          │ status       │                        │
    │  │ version      │          └──────────────┘                        │
    │  │ content      │                 │                                │
    │  └──────────────┘                 │                                │
    │                                   │                                │
    │  ChecklistItem               ChecklistItemEvaluation               │
    │  ┌──────────────┐          ┌──────────────┐                        │
    │  │ id (PK)*     │──────────│ item_id      │                        │
    │  │ checklist_id │          │ project_id   │                        │
    │  │ title        │          │ status       │                        │
    │  │ severity     │          │ evaluator    │                        │
    │  │ guidance     │          │ evidence     │                        │
    │  └──────────────┘          └──────────────┘                        │
    │                                                                     │
    │  * Deterministic UUID v5 (project + template + item)               │
    └─────────────────────────────────────────────────────────────────────┘

    📝 DELIVERABLES
    ✅ backend/app/models/checklist.py          (4 models)
    ✅ backend/migrations/versions/<ts>_create...py  (migration)
    ✅ backend/app/config/settings.py           (5 new settings)
    ✅ backend/tests/models/test_checklist_models.py  (5 tests)

    ✔️  VERIFICATION
    □ Migration runs: alembic upgrade head
    □ Migration reverts: alembic downgrade -1
    □ mypy --strict passes
    □ ruff check passes
    □ Tests pass: pytest backend/tests/models/


╔═══════════════════════════════════════════════════════════════════════════════╗
║                           PHASE 2: CORE SERVICES                              ║
║                              Days 4-8 (3-5 days)                              ║
╚═══════════════════════════════════════════════════════════════════════════════╝

    🔧 SERVICE ARCHITECTURE
    ┌─────────────────────────────────────────────────────────────────────┐
    │                                                                     │
    │  ChecklistRegistry                                                  │
    │  ┌───────────────────────────────────────────────────────┐         │
    │  │ • Load templates from cache                           │         │
    │  │ • get_template(slug)                                  │         │
    │  │ • list_templates()                                    │         │
    │  └───────────────────────────────────────────────────────┘         │
    │                         ↓                                           │
    │  ChecklistEngine                                                    │
    │  ┌───────────────────────────────────────────────────────┐         │
    │  │ • process_agent_result()       → Create DB records    │         │
    │  │ • sync_project_state_to_db()   → Backfill from JSON   │         │
    │  │ • sync_db_to_project_state()   → Rebuild JSON         │         │
    │  │ • evaluate_item()              → Manual evaluation    │         │
    │  │ • list_next_actions()          → Query uncovered      │         │
    │  │ • compute_progress()           → Calculate %          │         │
    │  └───────────────────────────────────────────────────────┘         │
    │                         ↓                                           │
    │  ChecklistService (Wrapper)                                         │
    │  ┌───────────────────────────────────────────────────────┐         │
    │  │ • FastAPI dependency injection                        │         │
    │  │ • Thin adapter for API layer                          │         │
    │  └───────────────────────────────────────────────────────┘         │
    │                                                                     │
    │  normalize_helpers.py                                               │
    │  ┌───────────────────────────────────────────────────────┐         │
    │  │ • compute_deterministic_item_id()                     │         │
    │  │ • normalize_waf_item()         → JSON to DB           │         │
    │  │ • denormalize_checklist()      → DB to JSON           │         │
    │  │ • validate_consistency()       → Verify match         │         │
    │  └───────────────────────────────────────────────────────┘         │
    └─────────────────────────────────────────────────────────────────────┘

    📝 DELIVERABLES
    ✅ backend/app/agents_system/checklists/registry.py
    ✅ backend/app/agents_system/checklists/engine.py
    ✅ backend/app/agents_system/checklists/service.py
    ✅ backend/app/services/normalize_helpers.py
    ✅ Tests for all components (7+ test cases)

    ✔️  VERIFICATION
    □ Registry loads templates
    □ Engine creates DB records
    □ Sync is idempotent (run twice = same result)
    □ Round-trip consistency (JSON → DB → JSON)
    □ Progress calculation accurate


╔═══════════════════════════════════════════════════════════════════════════════╗
║                         PHASE 3: INTEGRATION & API                            ║
║                              Days 9-12 (2-4 days)                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝

    🔌 INTEGRATION POINTS
    ┌─────────────────────────────────────────────────────────────────────┐
    │                                                                     │
    │  Agent Flow                                                         │
    │  ┌────────────────┐    ┌──────────────┐    ┌──────────────┐       │
    │  │ AgentRunner    │───▶│ Orchestrator │───▶│ on_end       │       │
    │  │ (register cb)  │    │ (invoke cb)  │    │ callback     │       │
    │  └────────────────┘    └──────────────┘    └──────┬───────┘       │
    │                                                     │               │
    │                                                     ▼               │
    │                                          ┌─────────────────┐       │
    │                                          │ ChecklistEngine │       │
    │                                          │ process_result()│       │
    │                                          └─────────────────┘       │
    │                                                                     │
    │  Router Flow                                                        │
    │  ┌────────────────┐    ┌──────────────┐    ┌──────────────┐       │
    │  │ Router Agent   │───▶│ update_state │───▶│ sync_to_db() │       │
    │  │ (_apply_update)│    │              │    │              │       │
    │  └────────────────┘    └──────────────┘    └──────────────┘       │
    │                                                                     │
    └─────────────────────────────────────────────────────────────────────┘

    🌐 REST API (6 Endpoints)
    ┌─────────────────────────────────────────────────────────────────────┐
    │  GET    /api/projects/{id}/checklists                               │
    │         → List all checklists for project                           │
    │                                                                     │
    │  GET    /api/projects/{id}/checklists/{cid}                         │
    │         → Get checklist detail with items                           │
    │                                                                     │
    │  PATCH  /api/projects/{id}/checklists/{cid}/items/{iid}            │
    │         → Update item evaluation (manual)                           │
    │                                                                     │
    │  POST   /api/projects/{id}/checklists/{cid}/items/{iid}/evaluate   │
    │         → Evaluate item (explicit POST)                             │
    │                                                                     │
    │  GET    /api/projects/{id}/checklists/{cid}/progress                │
    │         → Get completion metrics                                    │
    │                                                                     │
    │  POST   /api/projects/{id}/checklists/resync                        │
    │         → Trigger manual resync                                     │
    └─────────────────────────────────────────────────────────────────────┘

    📝 DELIVERABLES
    ✅ backend/app/agents_system/orchestrator/orchestrator.py (modified)
    ✅ backend/app/agents_system/runner.py (modified)
    ✅ backend/app/agents_system/agents/router.py (modified)
    ✅ backend/app/routers/checklists/checklist_router.py
    ✅ backend/app/routers/checklists/schemas.py
    ✅ frontend/src/types/api-artifacts.ts (modified)
    ✅ Tests for all endpoints

    ✔️  VERIFICATION
    □ Orchestrator invokes callback
    □ Router syncs after state update
    □ All API endpoints functional
    □ OpenAPI docs accessible: /docs
    □ Frontend types match backend


╔═══════════════════════════════════════════════════════════════════════════════╗
║                      PHASE 4: BACKFILL, TESTS & DOCS                          ║
║                             Days 13-17 (3-5 days)                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝

    🔄 BACKFILL PROCESS
    ┌─────────────────────────────────────────────────────────────────────┐
    │                                                                     │
    │  For Each Project:                                                  │
    │  ┌────────────────────────────────────────────────────┐            │
    │  │ 1. Read ProjectState.state['wafChecklist']         │            │
    │  │                    ↓                                │            │
    │  │ 2. For each template → items:                      │            │
    │  │    • Compute deterministic ID                      │            │
    │  │    • Upsert ChecklistTemplate                      │            │
    │  │    • Upsert Checklist                              │            │
    │  │    • Upsert ChecklistItem                          │            │
    │  │                    ↓                                │            │
    │  │ 3. For each evaluation:                            │            │
    │  │    • Upsert ChecklistItemEvaluation                │            │
    │  │                    ↓                                │            │
    │  │ 4. Verify (sample 1%):                             │            │
    │  │    • Reconstruct JSON from DB                      │            │
    │  │    • Compare with original                         │            │
    │  │    • Log any mismatches                            │            │
    │  │                    ↓                                │            │
    │  │ 5. Commit in chunks (500 items/txn)                │            │
    │  └────────────────────────────────────────────────────┘            │
    │                                                                     │
    │  Features:                                                          │
    │  • Idempotent (can run multiple times)                              │
    │  • Chunked (prevents long transactions)                             │
    │  • Dry-run mode (validate without writing)                          │
    │  • Progress tracking                                                │
    │  • Verification sampling                                            │
    └─────────────────────────────────────────────────────────────────────┘

    🧪 TEST PYRAMID
    ┌─────────────────────────────────────────────────────────────────────┐
    │                                                                     │
    │         ▲                                                           │
    │        ╱ ╲   E2E Tests (10%)                                        │
    │       ╱   ╲  • Full agent flow                                      │
    │      ╱─────╲ • API integration                                      │
    │     ╱       ╲                                                        │
    │    ╱─────────╲  Integration Tests (20%)                             │
    │   ╱           ╲ • API endpoints                                     │
    │  ╱             ╲• Agent + DB                                        │
    │ ╱───────────────╲                                                   │
    │╱                 ╲ Unit Tests (70%)                                 │
    │───────────────────• Models                                          │
    │                   • Helpers                                         │
    │                   • Service methods                                 │
    │                   • Engine logic                                    │
    │                                                                     │
    │  Target: >80% coverage for new code                                 │
    └─────────────────────────────────────────────────────────────────────┘

    📝 DELIVERABLES
    ✅ backend/app/services/backfill_service.py
    ✅ scripts/backfill_waf.py (CLI with 4 commands)
    ✅ scripts/maintain_checklists.py (CLI with 4 commands)
    ✅ 8 test files covering all components
    ✅ docs/waf_normalization_implementation/WAF_NORMALIZED_DB.md
    ✅ docs/waf_normalization_implementation/FRONTEND_INTEGRATION.md
    ✅ docs/UX_IDE_WORKFLOW.md (updated)

    ✔️  VERIFICATION
    □ Backfill dry-run succeeds
    □ Backfill executes without errors
    □ Verification passes (100% sample)
    □ All tests pass: pytest backend/tests/
    □ Coverage >80%: pytest --cov
    □ Documentation complete


╔═══════════════════════════════════════════════════════════════════════════════╗
║                        PHASE 5: DEPLOYMENT & OPERATIONS                       ║
║                         Days 18-20 + 7-14 days monitoring                     ║
╚═══════════════════════════════════════════════════════════════════════════════╝

    🚀 DEPLOYMENT TIMELINE
    ┌─────────────────────────────────────────────────────────────────────┐
    │                                                                     │
    │  STAGING (Week 1)                                                   │
    │  ├─ Deploy code (FEATURE_WAF_NORMALIZED=false)                      │
    │  ├─ Run migration                                                   │
    │  ├─ Backfill dry-run                                                │
    │  ├─ Backfill execute                                                │
    │  ├─ Verify (sample)                                                 │
    │  └─ Enable feature flag                                             │
    │                                                                     │
    │  STAGING VALIDATION (Weeks 2-3: 7-14 days)                          │
    │  ├─ Monitor metrics                                                 │
    │  ├─ Test dual-write                                                 │
    │  ├─ User acceptance testing                                         │
    │  └─ Fix any issues                                                  │
    │                                                                     │
    │  PRODUCTION (Week 4)                                                │
    │  ├─ Backup database                                                 │
    │  ├─ Deploy code                                                     │
    │  ├─ Run migration                                                   │
    │  ├─ Backfill (1-2 hours)                                            │
    │  └─ Verify                                                          │
    │                                                                     │
    │  GRADUAL ROLLOUT (Days 1-5)                                         │
    │  Day 1: 10%  ─┐                                                     │
    │  Day 2: 25%   ├─ Monitor each stage                                 │
    │  Day 3: 50%   ├─ Check metrics                                      │
    │  Day 4: 75%   ├─ Fix issues                                         │
    │  Day 5: 100% ─┘  Celebrate! 🎉                                      │
    └─────────────────────────────────────────────────────────────────────┘

    📊 MONITORING DASHBOARD
    ┌─────────────────────────────────────────────────────────────────────┐
    │                                                                     │
    │  Metrics:                                                           │
    │  • waf_sync_counter              (syncs/sec)                        │
    │  • waf_sync_duration             (latency p95)                      │
    │  • waf_evaluation_counter        (evaluations/min)                  │
    │  • waf_progress_gauge            (% complete per project)           │
    │  • waf_consistency_check         (pass rate %)                      │
    │                                                                     │
    │  Alerts:                                                            │
    │  • HighWafSyncErrorRate          (>5% errors)                       │
    │  • WafSyncDurationHigh           (>5s p95)                          │
    │  • WafBackfillStalled            (no progress 1h)                   │
    │  • WafConsistencyLow             (<99.5%)                           │
    │                                                                     │
    │  Dashboard Panels:                                                  │
    │  • Backfill progress graph                                          │
    │  • Sync error rate                                                  │
    │  • API latency histogram                                            │
    │  • Active checklists gauge                                          │
    │  • Evaluations rate                                                 │
    └─────────────────────────────────────────────────────────────────────┘

    📝 DELIVERABLES
    ✅ Staging deployment runbook
    ✅ Production backfill log (PRODUCTION_BACKFILL_LOG.md)
    ✅ Monitoring setup (MONITORING.md)
    ✅ Deprecation plan (DEPRECATION_PLAN.md)
    ✅ Rollback procedures
    ✅ On-call runbooks

    ✔️  VERIFICATION
    □ Staging deployed successfully
    □ Staging validated (7-14 days)
    □ Production backfill complete
    □ Gradual rollout to 100%
    □ All metrics healthy
    □ No P0/P1 incidents


╔═══════════════════════════════════════════════════════════════════════════════╗
║                              SUCCESS CRITERIA                                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝

    ✅ IMPLEMENTATION
    □ All 5 phases complete
    □ 30+ tasks checked off
    □ All tests passing (>80% coverage)
    □ Documentation complete
    □ Code reviewed and merged

    ✅ QUALITY
    □ Type safety: 100% (no Any types)
    □ Linting: ruff/eslint passing
    □ Type checking: mypy strict passing
    □ Test coverage: >80%

    ✅ FUNCTIONALITY
    □ Migration runs both ways (up/down)
    □ Backfill idempotent
    □ Sync maintains consistency
    □ API endpoints functional
    □ Agent integration working

    ✅ PERFORMANCE
    □ API latency <500ms (p95)
    □ Backfill >10 projects/sec
    □ Query performance acceptable
    □ Database indexes effective

    ✅ RELIABILITY
    □ Data loss: 0 incidents
    □ Consistency: <0.5% mismatch
    □ Error rate: <0.1%
    □ Uptime: >99.9%

    ✅ OPERATIONS
    □ Monitoring operational
    □ Alerts configured
    □ Runbooks available
    □ Team trained


╔═══════════════════════════════════════════════════════════════════════════════╗
║                               QUICK COMMANDS                                  ║
╚═══════════════════════════════════════════════════════════════════════════════╝

    💻 DEVELOPMENT
    # Run migration
    alembic upgrade head
    
    # Run tests
    pytest backend/tests/ -v
    pytest backend/tests/ --cov --cov-report=html
    
    # Linting & Type Checking
    ruff check backend/
    mypy backend/app/ --strict
    
    # Backfill
    uv python scripts/backfill_waf.py backfill --dry-run
    uv python scripts/backfill_waf.py backfill --execute
    uv python scripts/backfill_waf.py verify --sample-size 10


╔═══════════════════════════════════════════════════════════════════════════════╗
║                                  RESOURCES                                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝

    📖 DOCUMENTATION
    • README.md                              - Overview and navigation
    • DETAILED_IMPLEMENTATION_PLAN.md        - Complete specifications
    • PROGRESS_TRACKER.md                    - Task checklist
    • QUICK_REFERENCE.md                     - Developer cheat sheet
    • VERIFICATION_TESTING_CHECKLIST.md      - QA procedures
    • IMPLEMENTATION_SUMMARY.md              - Executive summary

    🔗 EXTERNAL
    • Original Plan: ../plan-normalizeWafChecklistToDb.prompt.prompt.md
    • Backend Reference: ../BACKEND_REFERENCE.md
    • System Architecture: ../architecture/system-architecture.md


╔═══════════════════════════════════════════════════════════════════════════════╗
║                               TEAM ROLES                                      ║
╚═══════════════════════════════════════════════════════════════════════════════╝

    👤 Implementation Lead
    • Overall coordination
    • Track progress
    • Unblock issues
    
    👥 Backend Developers
    • Phase 1-4 implementation
    • Write tests
    • Code review
    
    🔬 QA/Testing
    • Test plan execution
    • Manual verification
    • User acceptance
    
    ⚙️  DevOps/Operations
    • Deployment
    • Backfill execution
    • Monitoring setup
    
    📚 Technical Writer
    • Documentation review
    • Runbook creation
    • User guides


╔═══════════════════════════════════════════════════════════════════════════════╗
║                            PRINT THIS PAGE!                                   ║
║                         Keep it visible during work                           ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```
