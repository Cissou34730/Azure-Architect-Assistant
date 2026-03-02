# Implementation Checklist

Tracks every task from [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).  
Ref: [COMPREHENSIVE_CODEBASE_REVIEW_2026-03-01.md](COMPREHENSIVE_CODEBASE_REVIEW_2026-03-01.md)

---

## Phase 1 — Test Foundation

- [ ] 1.1 — Coverage tooling: `pytest-cov` configured, `@vitest/coverage-v8` configured
- [ ] 1.2 — Backend shared fixtures in `conftest.py` + `fixtures/` directory
- [ ] 1.3 — Frontend test utilities (`test-utils.tsx`)
- [ ] 1.4 — Backend service tests: `query_service` (10 cases)
- [ ] 1.4 — Backend service tests: `ai_service` (10 cases)
- [ ] 1.4 — Backend service tests: `interfaces`
- [ ] 1.4 — Backend service tests: `document_parsing` (12 cases + fixture docs)
- [ ] 1.4 — Backend service tests: `document_service` (8 cases)
- [ ] 1.4 — Backend service tests: `document_normalization` (6 cases)
- [ ] 1.4 — Backend service tests: `project_service` (9 cases)
- [ ] 1.4 — Backend service tests: `chat_service` (7 cases)
- [ ] 1.4 — Backend service tests: `llm_service`
- [ ] 1.4 — Backend service tests: `pricing_normalizer` (5 cases)
- [ ] 1.4 — Backend service tests: `retail_prices_client` (5 cases)
- [ ] 1.5 — Diagram service tests: all 11 files (~50 cases)
- [ ] 1.6 — Router tests: `project_router`
- [ ] 1.6 — Router tests: `query_router`
- [ ] 1.6 — Router tests: `models_router`
- [ ] 1.7 — Core modules: untested files covered
- [ ] 1.7 — Lifecycle tests (startup, shutdown, degradation)
- [ ] 1.7 — MCP client gap tests (timeout, retry, errors)
- [ ] 1.7 — Ingestion system gap tests (pipeline, hashing, phases)
- [ ] 1.8 — Backend coverage ≥95%
- [ ] 1.9 — Frontend service tests: all 11 files
- [ ] 1.10 — Frontend hook tests: all 17 untested hooks
- [ ] 1.11 — Frontend common component tests: all 15 components
- [ ] 1.12 — Frontend utility tests: `apiMapping`, `diagramCache`, `typeGuards`
- [ ] 1.13 — Frontend feature component tests (tree, chat, tabs, mermaid, ingestion, KB, palette)
- [ ] 1.14 — Contract tests (TS types ↔ Pydantic models, 8+ endpoints)
- [ ] 1.15 — Visual regression tests (Playwright screenshots)
- [ ] 1.16 — E2E tests: `kb-query`, `ingestion-errors`, `settings`
- [ ] 1.17 — Frontend coverage ≥90% lines, ≥90% functions, ≥85% branches

## Phase 2 — Security

- [ ] 2.1 — S-5: `dompurify` installed, test written, `useMermaidRenderer.ts` sanitized

## Phase 3 — Architecture

- [ ] 3.1 — A-1: Dual graph factory consolidated
- [ ] 3.2 — A-2: Business logic extracted from fat routers
- [ ] 3.3 — A-5: Event bus created + 2 events wired
- [ ] 3.4 — A-6: `/api/v1/` prefix, frontend updated, backward compat

## Phase 4 — Backend Quality

- [ ] 4.1 — B-1: Centralized error-to-status mapping
- [ ] 4.2 — B-2: Explicit DB rollback in exception handlers
- [ ] 4.3 — B-3: Phase tracking — no silent suppression
- [ ] 4.4 — B-4: Ingestion start idempotency (409 on duplicate)
- [ ] 4.5 — B-5: Document size validation before LLM
- [ ] 4.6 — B-6: Logging levels standardized
- [ ] 4.7 — B-7: AgentRunner unavailable → 503
- [ ] 4.8 — B-8: Structured JSON logging

## Phase 5 — Frontend Quality

- [ ] 5.1 — F-1: `fetchWithRetry` + all services migrated
- [ ] 5.2 — F-2: Silent `.catch(() => null)` patterns fixed
- [ ] 5.3 — F-3: Loading components consolidated
- [ ] 5.4 — F-4: `debug.ts` utility, `console.log` replaced
- [ ] 5.5 — F-5: `react-hook-form` + `zod` proof of concept
- [ ] 5.6 — F-6: `useProjectDetails` decomposed
- [ ] 5.7 — F-7: `StaleDataBanner` created + integrated
- [ ] 5.8 — F-8: Style convention documented, top violations fixed

## Phase 6 — Observability

- [ ] 6.1 — FE-25: `X-Request-Id` middleware
- [ ] 6.2 — FE-28: Application Insights (backend + frontend)
- [ ] 6.3 — FE-26: Health dashboard page
- [ ] 6.4 — FE-27: Usage analytics service + endpoint

## Phase 7 — UX/UI Fixes

- [ ] 7.1 — FE-29: Keyboard shortcut mismatch fixed
- [ ] 7.2 — FE-7: Breadcrumb navigation + back buttons
- [ ] 7.3 — Command palette discoverability
- [ ] 7.4 — FE-30: Help modal (replace `alert()`)
- [ ] 7.5 — FE-31: Contextual tooltips
- [ ] 7.6 — FE-34: Dark mode audit + fixes
- [ ] 7.7 — Empty state standardization
- [ ] 7.8 — Accessibility: focus indicators + `aria-live` regions

## Phase 8 — Features: Chat, Navigation, Workspace

- [ ] 8.1 — FE-1: Streaming chat (SSE backend + frontend)
- [ ] 8.2 — FE-2: Copy message button
- [ ] 8.3 — FE-3: Message regeneration
- [ ] 8.4 — FE-4: Message editing
- [ ] 8.5 — FE-5: Conversation naming/search
- [ ] 8.6 — FE-6: Conversation export (MD, JSON, PDF)
- [ ] 8.7 — FE-8: Global project search
- [ ] 8.8 — FE-9: Artifact search within project
- [ ] 8.9 — FE-10: Conversation history search
- [ ] 8.10 — FE-11: Drag-and-drop upload
- [ ] 8.11 — FE-12+13: Tab state persistence (localStorage)
- [ ] 8.12 — FE-14: Inline document editing
- [ ] 8.13 — FE-15: Project templates

## Phase 9 — Features: Export, Collaboration, Operations

- [ ] 9.1 — FE-16+17: Project export/import (JSON)
- [ ] 9.2 — FE-18: Diagram export PNG/SVG
- [ ] 9.3 — FE-19: Proposal export Word/PDF
- [ ] 9.4 — FE-20: User authentication (Entra ID)
- [ ] 9.5 — FE-21: Project sharing (depends on 9.4)
- [ ] 9.6 — FE-22: Audit trail
- [ ] 9.7 — FE-23: Real-time collaboration (presence first)

## Phase 10 — Performance

- [ ] 10.1 — P-1: Response caching (LRU/TTL)
- [ ] 10.2 — P-2: Bundle size budget in Vite
- [ ] 10.3 — P-3: Mermaid render cache integrated
- [ ] 10.4 — P-4: Project list pagination
- [ ] 10.5 — P-5: LLM streaming (verify via FE-1)
- [ ] 10.6 — P-6: Large deps optimized (dynamic imports)

## Phase 11 — Documentation

- [ ] 11.1 — D-1: `docs/SECURITY.md`
- [ ] 11.2 — D-2: `docs/API_REFERENCE.md`
- [ ] 11.3 — D-3: Stale pointer files cleaned
- [ ] 11.4 — D-4: Storybook set up + component stories
- [ ] 11.5 — D-5: 5 ADRs in `docs/architecture/decisions/`
- [ ] 11.6 — D-6: `docs/operations/RUNBOOK.md`
- [ ] 11.7 — D-7: `docs/LOGGING_STANDARDS.md`
- [ ] 11.8 — `docs/README.md` updated

## Phase 12 — Mutation Testing & Final Validation

- [ ] 12.1 — Mutation tools installed (`mutmut`, `stryker`)
- [ ] 12.2 — Backend mutations run, survivors killed
- [ ] 12.3 — Frontend mutations run, survivors killed
- [ ] 12.4 — Final: coverage gates met, lint clean

---

## Deferred (Phase 2 scope — not tracked here)

| ID | Item | Reason |
|----|------|--------|
| S-1 | Auth (Entra ID/JWT) | Later security phase |
| S-2 | CORS restriction | Later security phase |
| S-3 | Rate limiting | Later security phase |
| S-4 | CSRF protection | Later security phase |
| S-6 | Input length limits | Later security phase |
| S-7 | Document size/type validation | Later security phase |
| A-3 | Shutdown extensibility | Keep as-is |
| A-4 | DB consolidation | Keep dual-DB |
| FE-32 | Mobile responsive | Later UX phase |
| FE-33 | Onboarding tour | Later UX phase |
