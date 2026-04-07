# Comprehensive Codebase Review — Azure Architect Assistant

**Date**: 2026-03-01  
**Branch**: `refactor/simply-code-base`  
**Scope**: Full codebase — backend, frontend, architecture, UX/UI, security, testing, features  
**Method**: Multi-pass automated deep analysis (backend, frontend, security, UX/UI)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture & Design](#2-architecture--design)
3. [Security](#3-security)
4. [Backend Code Quality](#4-backend-code-quality)
5. [Frontend Code Quality](#5-frontend-code-quality)
6. [UX & UI](#6-ux--ui)
7. [Testing & Quality Assurance](#7-testing--quality-assurance)
8. [Performance](#8-performance)
9. [Documentation & Developer Experience](#9-documentation--developer-experience)
10. [Feature Enhancement Proposals](#10-feature-enhancement-proposals)
11. [Prioritized Recommendation Matrix](#11-prioritized-recommendation-matrix)

---

## 1. Executive Summary

The Azure Architect Assistant is a **well-structured, modern monorepo** (React 19 + FastAPI) with clean layering, strong TypeScript practices, and thoughtful DDD-inspired backend design. The product is functionally rich — projects, KB ingestion, agent chat, diagram generation, WAF checklists — and covers a broad surface for Azure architecture consulting.

**Key strengths**: Clean separation of concerns, modern stack choices (Vite, Tailwind v4.1, OKLCH colors), strong Pydantic/TypeScript typing, DI-ready architecture, graceful lifecycle management.

**Critical gaps**: No authentication, no API rate limiting, overly permissive CORS, low test coverage (backend ~21%, frontend unit ~7%), no streaming chat responses, missing breadcrumbs and global search.

The codebase is at a **"works well for a single user / demo"** maturity level and needs security hardening, test coverage, and UX polish to be production-multi-user-ready.

---

## 2. Architecture & Design

### 2.1 What Works Well

| Area | Finding |
|------|---------|
| **Backend layering** | Clear Routers → Services → Domain separation; ingestion module is a model DDD implementation |
| **AI provider abstraction** | `AIService` supports OpenAI + Azure OpenAI with automatic transient-error fallback |
| **Singleton services** | `ServiceRegistry` + `dependencies.py` provide testable DI with performance-justified caching (KB indices ~150MB) |
| **Frontend code splitting** | All routes lazy-loaded; vendor chunks manually split (react, router, mermaid) |
| **Feature modularization** | Frontend `features/projects/` owns its own context, hooks, components, pages |
| **Lifecycle management** | Ordered startup (DB → KB → MCP → Agent) with graceful shutdown |

### 2.2 Improvement Opportunities

#### A-1: Dual Graph Factory Consolidation ✅ IMPLEMENT
- `graph_factory.py` (170 LOC) and `graph_factory_advanced.py` (177 LOC) share ~70% node overlap with zero code reuse
- **Risk**: Bug fixes in one don't reach the other
- **Proposal**: Merge into a single configurable factory with feature flags

#### A-2: Fat Router Anti-Pattern ✅ IMPLEMENT
- Several routers contain business logic that should live in service classes
- Example: Agent router (`agents/router.py`, ~350 LOC) does state update parsing, merge conflict handling, and iteration logging inline
- **Proposal**: Extract to dedicated service methods; routers should only parse requests and return responses

#### A-3: Service Registry Extensibility ⏸️ DEFERRED
- Shutdown sequence hard-codes 3 cleanup functions; new services must be manually added
- **Proposal**: Registry-based shutdown — services register their own cleanup callbacks on startup
- **Decision**: Keep current shutdown mechanism as-is for now

#### A-4: Database Consolidation Opportunity ⏸️ DEFERRED
- 2 SQLite databases (`projects.db`, `ingestion.db`) with separate Alembic configs
- **Trade-off**: Isolation vs. operational simplicity
- **Proposal**: Evaluate merging into single DB with namespace separation; simplifies migrations and backup
- **Decision**: Keep dual-DB architecture as-is for now

#### A-5: Missing Event/Message Bus ✅ IMPLEMENT
- Agent chat, ingestion jobs, and project state updates are tightly coupled via direct function calls
- **Proposal**: Lightweight event bus (even in-process) to decouple producers from consumers; enables future features like notifications, audit trails, webhooks

#### A-6: No API Versioning Strategy ✅ IMPLEMENT
- Routes under `/api/` with no version prefix except `/api/v1` for diagrams
- **Proposal**: Standardize all routes under `/api/v1/` now; adds `/api/v2/` path for future breaking changes

---

## 3. Security

### 3.1 Critical Issues ⏸️ ALL DEFERRED TO LATER PHASE

| ID | Issue | Severity | Status | Location |
|----|-------|----------|--------|----------|
| **S-1** | **No authentication/authorization** | 🔴 Critical | ⏸️ Deferred | All endpoints publicly accessible; no Bearer/JWT/Entra ID middleware |
| **S-2** | **CORS misconfiguration** | 🔴 Critical | ⏸️ Deferred | `allow_origins=["*"]` + `allow_credentials=True` violates CORS spec and is rejected by browsers; `allow_methods=["*"]`, `allow_headers=["*"]` overly permissive |
| **S-3** | **No API rate limiting** | 🟠 High | ⏸️ Deferred | No middleware rate limiter (slowapi, etc.); all endpoints unbounded |
| **S-4** | **No CSRF protection** | 🟡 Medium | ⏸️ Deferred | SPA architecture reduces CSRF risk, but no tokens if cookie-auth is ever added |

### 3.2 Moderate Issues

| ID | Issue | Severity | Status | Location |
|----|-------|----------|--------|----------|
| **S-5** | **Mermaid `.innerHTML` without sanitization** | 🟡 Medium | ✅ IMPLEMENT | `useMermaidRenderer.ts` injects SVG via `.innerHTML` — mermaid output should be trustworthy, but DOMPurify adds defense-in-depth |
| **S-6** | **No input length limits on chat messages** | 🟡 Medium | ⏸️ Deferred | `ChatMessageRequest.message: str` has no `Field(max_length=...)` — enables prompt injection and memory exhaustion |
| **S-7** | **No document size/type validation on upload** | 🟡 Medium | ⏸️ Deferred | No server-side max file size or MIME type allowlist for document uploads |

### 3.3 Good Practices Already in Place

- ✅ All secrets sourced from environment variables via Pydantic Settings
- ✅ No hardcoded API keys or tokens in source
- ✅ Pydantic `extra="forbid"` prevents silent config errors
- ✅ All SQLAlchemy queries use parameterized statements (no SQL injection)
- ✅ Frontend uses `react-markdown` (safe) instead of `dangerouslySetInnerHTML` for chat
- ✅ External links use `rel="noopener noreferrer"`

### 3.4 Recommendations

1. ⏸️ **Add Entra ID / JWT authentication** — FastAPI middleware with `Depends(verify_token)` — *deferred*
2. ⏸️ **Restrict CORS** — Allow only the frontend origin; specify methods/headers explicitly — *deferred*
3. ⏸️ **Add slowapi rate limiter** — 60 req/min for queries, 10 req/min for ingestion — *deferred*
4. ✅ **Add DOMPurify** for mermaid SVG injection — `container.innerHTML = DOMPurify.sanitize(svg)`
5. ⏸️ **Add `Field(max_length=10000)`** to all text input models — *deferred*

---

## 4. Backend Code Quality

### 4.1 Strengths

- **Pydantic Settings** with field validators, path normalization, and cross-field validation
- **Error hierarchy** — domain-specific exceptions (`IngestionError`, `MCPError` with subtypes)
- **Graceful degradation** — MCP failure at startup disables agent chat but doesn't crash
- **JSON repair** — `repair_json_content()` with exponential token budgeting handles LLM output artifacts
- **KB query thresholds** — Min-results fallback prevents empty results when similarity threshold is too strict

### 4.2 Issues — ✅ ALL IMPLEMENT

| ID | Issue | Impact | Status | Proposal |
|----|-------|--------|--------|----------|
| **B-1** | **Inconsistent error-to-status-code mapping** | Medium | ✅ Implement | `ValueError → 400` is implicit; use explicit `HTTPException` with status codes or a shared error-mapping utility |
| **B-2** | **No explicit DB rollback** | Medium | ✅ Implement | Relies on context manager cleanup; add explicit `await db.rollback()` in exception handlers |
| **B-3** | **Phase tracking fragility** | Low | ✅ Implement | Multiple `_safe_phase_repo_call()` try-except blocks suppress errors silently; misleading progress reporting |
| **B-4** | **No idempotency on ingestion start** | Medium | ✅ Implement | `/kb/{kb_id}/start` can be called twice, starting duplicate jobs; reject duplicate requests or use idempotency keys |
| **B-5** | **No document size validation before LLM** | Medium | ✅ Implement | Combined document text sent to LLM without token pre-check; risk of exceeding context window |
| **B-6** | **Logging level inconsistency** | Low | ✅ Implement | Some routes use `logger.error(..., exc_info=True)`, others use `logger.exception()`, others `f"...{e!s}"` |
| **B-7** | **AgentRunner 500 on unavailable** | Low | ✅ Implement | `get_instance()` raises `RuntimeError` → unhandled 500; should return 503 Service Unavailable |
| **B-8** | **No structured logging format** | Low | ✅ Implement | Plain text logging; consider JSON structured logging for observability tooling |

### 4.3 Dependency Observations

- `pyproject.toml` pins exact versions for most dependencies (good for reproducibility)
- Heavy dependency footprint: LlamaIndex (8+ sub-packages), LangChain, LangGraph, Scrapy, newspaper3k
- `chromedriver-autoinstaller` suggests Selenium usage — verify if still needed or if it's legacy

---

## 5. Frontend Code Quality

### 5.1 Strengths

- **React 19 + TypeScript 6.0** — latest stack, strict mode enabled
- **Tailwind v4.1** with `@theme` design tokens (OKLCH color space) — modern, accessible
- **20+ custom hooks** — excellent logic extraction and separation of concerns
- **Multi-context approach** in projects — `ProjectStateContext`, `ProjectChatContext`, `ProjectInputContext`, `ProjectMetaContext` minimize re-renders
- **Virtuoso** for chat message lists — handles large conversation histories efficiently
- **Intersection Observer** for lazy mermaid diagram rendering
- **Error boundary** component exists for crash recovery
- **Command Palette** (Cmd/Ctrl+K) with ~15 navigation actions

### 5.2 Issues — ✅ ALL IMPLEMENT

| ID | Issue | Impact | Status | Proposal |
|----|-------|--------|--------|----------|
| **F-1** | **No API retry logic** | Medium | ✅ Implement | Service layer has no retry mechanism for failed requests; add exponential backoff retry (1-2-4s) for transient errors |
| **F-2** | **Silent `.catch(() => null)` patterns** | Medium | ✅ Implement | Some hooks silently swallow errors without logging; standardize error handling via `useErrorHandler` |
| **F-3** | **3 loading components** | Low | ✅ Implement | `PageLoader`, `LoadingSpinner`, `LoadingIndicator` serve similar purposes; consolidate or create clear usage guidelines |
| **F-4** | **Console.log in production** | Low | ✅ Implement | `ProjectProvider` logs context changes in DEV; replace with a proper debug utility |
| **F-5** | **No form validation library** | Medium | ✅ Implement | Client-side input validation is ad-hoc; consider a lightweight form library (react-hook-form) for complex forms |
| **F-6** | **Dense hook aggregation** | Low | ✅ Implement | `useProjectDetails` (~150 LOC) aggregates 5+ hooks; harder to test individual concerns |
| **F-7** | **No stale-data indicators** | Low | ✅ Implement | When API errors occur, stale data is shown without visual indicator |
| **F-8** | **Mixed semantic + utility styles** | Low | ✅ Implement | Components use both `ui-btn` semantic classes and raw Tailwind utilities; standardize one approach |

---

## 6. UX & UI

### 6.1 Navigation & Information Architecture — ✅ ALL IMPLEMENT

| Finding | Status | Action | Recommendation |
|---------|--------|--------|----------------|
| **3 main nav items** (Projects, KB, KB Management) | ✅ Clear | — | — |
| **No breadcrumb navigation** | ❌ Missing | ✅ Implement | Add contextual breadcrumbs: *Projects > MyProject > ADRs > ADR-001* |
| **Command Palette** (Cmd/Ctrl+K) | ✅ Good | ✅ Implement | Make discoverable with visual hint in empty states |
| **No back button in nested views** | ❌ Missing | ✅ Implement | Add explicit "← Back to Project" in artifact detail views |
| **Project switching is dropdown-only** | ⚠️ Adequate | ✅ Implement | Consider persistent breadcrumb instead |

### 6.2 Chat & Agent Experience — ✅ ALL IMPLEMENT

| Finding | Status | Action | Impact |
|---------|--------|--------|--------|
| **No streaming responses** | ❌ Critical UX gap | ✅ Implement | Users wait 5-10s with no feedback; SSE/WebSocket streaming is table-stakes for chat UX |
| **No message copy button** | ❌ Missing | ✅ Implement | Users can't easily copy agent responses |
| **No message edit/regenerate** | ❌ Missing | ✅ Implement | Can't correct or retry; forces new message |
| **No conversation naming/switching** | ❌ Missing | ✅ Implement | Can't organize or reference past conversations |
| **Markdown + code highlighting** | ✅ Good | — | react-markdown + Prism.js with oneDark theme |
| **Source attribution badges** | ✅ Good | — | KB sources shown as clickable badges |
| **Reasoning steps toggle** | ✅ Good | — | Expandable agent thought process |
| **Conversation history** | ✅ Good | — | Virtuoso infinite scroll, persisted per project |

### 6.3 Project Workspace — ✅ ALL IMPLEMENT

| Finding | Status | Action | Notes |
|---------|--------|--------|-------|
| **3-panel layout** (tree / workspace / chat) | ✅ Excellent | — | IDE-inspired; familiar paradigm |
| **Resizable panels** persisted to localStorage | ✅ Good | — | Left: 260-480px, Right: 280-520px |
| **Tab system** with pin/close/reorder | ✅ Good | — | Keyboard nav (Ctrl+Tab) |
| **15 artifact types** in project tree | ✅ Comprehensive | — | Requirements, ADRs, diagrams, costs, IaC, WAF, etc. |
| **No drag-and-drop file upload** | ❌ Missing | ✅ Implement | Upload requires button click |
| **Tab state not persisted across sessions** | ⚠️ Limitation | ✅ Implement | Open tabs lost on page refresh |
| **No inline document editing** | ❌ Missing | ✅ Implement | Documents are view-only after upload |

### 6.4 Ingestion Workflow

| Finding | Status | Notes |
|---------|--------|-------|
| **4-step wizard** (Info → Source → Config → Review) | ✅ Clear flow | Visual progress indicator |
| **Phase timeline** during ingestion | ✅ Good | Shows active phase with timing |
| **Job controls** (start, pause, cancel, retry) | ✅ Good | State-appropriate buttons |
| **No cancel confirmation dialog** | ⚠️ Minor | Just inline text confirmation |
| **No error recovery guidance** | ⚠️ Minor | Shows error message but no suggested fix |

### 6.5 Visual Design

| Finding | Status | Action | Notes |
|---------|--------|--------|-------|
| **OKLCH color system** with semantic tokens | ✅ Excellent | — | Perceptually uniform in light + dark themes |
| **Dark/Light/System theme** | ✅ Good | — | Persisted in localStorage |
| **Consistent spacing** via Tailwind utilities | ✅ Good | — | — |
| **No component library docs** (Storybook) | ❌ Missing | ✅ Implement | Developers can't browse available components |
| **Inconsistent empty states** | ⚠️ Minor | ✅ Implement | Various icon + text layouts across features |
| **Mobile not optimized** | ⚠️ Notable | ⏸️ Deferred | 3-panel layout breaks on small screens; no mobile nav |

### 6.6 Accessibility — ✅ ALL IMPLEMENT

| Finding | Status | Action | Notes |
|---------|--------|--------|-------|
| **Semantic aria-* attributes** on modals, buttons, alerts | ✅ Good | — | `role="dialog"`, `aria-labelledby`, etc. |
| **Focus trap in modals** | ✅ Good | — | `useFocusTrap` hook |
| **`aria-live="polite"` on toasts** | ✅ Good | — | Screen reader announced |
| **Missing focus indicators on some elements** | ⚠️ Partial | ✅ Implement | Needs audit |
| **No screen reader announcements for dynamic content** | ⚠️ Partial | ✅ Implement | Chat messages, state changes not announced |
| **Keyboard shortcuts mismatch** | 🔴 Bug | ✅ Implement | Help text claims Cmd/Ctrl+/ and Cmd/Ctrl+Enter but they're NOT implemented |

---

## 7. Testing & Quality Assurance

### 7.1 Coverage Overview

| Stack | Source Files | Test Files | Coverage Ratio |
|-------|-------------|------------|----------------|
| Backend (Python) | ~227 | 47 | ~20.7% |
| Frontend Unit (TS) | ~276 | 19 | ~6.9% |
| Frontend E2E | — | 7 | 7 workflows covered |

### 7.2 Well-Tested Areas

- ✅ Agent/LangGraph workflows — 23 test files covering state updates, prompts, tools, validation
- ✅ Ingestion orchestrator — Unit tests for workflow, retry policy, content hashing
- ✅ Checklist engine — Registry, engine, service with fixtures
- ✅ Router integration — 9 router test files with mock service injection
- ✅ Frontend hooks — `useToast`, `useDebounce`, project detail hooks
- ✅ E2E — Agent chat, checklist, diagrams, documents, projects, WAF

### 7.3 Critical Test Gaps

| Module | Files Untested | Risk |
|--------|---------------|------|
| **Document parsing** (`document_parsing.py`) | PDF/XLSX extraction logic | High — silent corruption |
| **KB query service** (`query_service.py`) | Vector search + threshold logic | High — core feature |
| **AI provider routing** (`ai_service.py`) | Fallback chain, caching | High — transient error handling |
| **Pricing service** (`pricing/`) | Cost calculations | Medium — financial accuracy |
| **Frontend services** (11 files) | All API communication | Medium — contract drift |
| **Frontend components** (50+) | All React components | Medium — regression risk |
| **Frontend utils** | Utility functions | Low — but easy to test |
| **MCP client** | Connection, retry, error hierarchy | Medium — integration point |

### 7.4 Recommendations — ✅ ALL IMPLEMENT (Target: 100% coverage)

1. ✅ **Target backend 100% coverage** — All modules: query_service, ai_service, document_parsing, pricing, MCP client, all routers, all services
2. ✅ **Add frontend service layer tests** — Mock `fetch`, validate request/response contracts for all 11 services
3. ✅ **Add component smoke tests** — Render + basic interaction for every common/ component
4. ✅ **Add contract tests** — Ensure frontend TypeScript types match backend Pydantic response models
5. ✅ **Add visual regression tests** — Playwright screenshots for workspace layout, theme switching
6. ✅ **Add mutation testing** — Verify existing tests catch real bugs (e.g., Stryker for TS, mutmut for Python)
7. ✅ **Add frontend hook tests** — Cover all custom hooks not yet tested
8. ✅ **Add frontend utility tests** — Cover all utility functions
9. ✅ **Add E2E tests for remaining workflows** — KB query, ingestion error paths, conversation management

---

## 8. Performance

### 8.1 What's Optimized

- ✅ KB indices preloaded at startup (150MB+, 3.2s load → shared singleton)
- ✅ Async FastAPI routes + async SQLAlchemy sessions
- ✅ Frontend code splitting with lazy routes and vendor chunks
- ✅ `useCallback`/`useMemo` to prevent unnecessary re-renders
- ✅ Virtuoso for chat message lists
- ✅ `IntersectionObserver` for lazy diagram rendering
- ✅ Debounced search inputs

### 8.2 Opportunities

| ID | Issue | Impact | Proposal |
|----|-------|--------|----------|
| **P-1** | **No response caching** | Medium | Agent/KB responses for identical queries could be cached (LRU in-memory, TTL 5min) |
| **P-2** | **No bundlesize budget in CI** | Low | Add `bundlesize` or Vite's `chunkSizeWarningLimit` enforcement in CI |
| **P-3** | **Mermaid rendering not cached** | Low | Same diagram code re-renders on every view; cache SVG output |
| **P-4** | **No pagination on project list** | Low | `/api/projects` returns all projects; fine for now, problematic at scale |
| **P-5** | **LLM calls block event loop** | Low | Agent chat is synchronous from user perspective; streaming would improve perceived performance |
| **P-6** | **Large dependency bundle** | Low | `mermaid` (~500KB), `recharts` (~200KB) are chunked but still large; evaluate lighter alternatives or dynamic import |

---

## 9. Documentation & Developer Experience

### 9.1 Strengths

- ✅ Well-organized docs with agent + human lanes
- ✅ Architecture docs (`project-overview.md`, `system-architecture.md`) are current and accurate
- ✅ `README.md` has correct quick start, ports, data paths
- ✅ FastAPI auto-generates OpenAPI at `/docs` and `/redoc`
- ✅ Provider setup docs (`AZURE_OPENAI_SETUP.md`, `AI_PROVIDER_ROUTING.md`) are comprehensive
- ✅ `copilot-instructions.md` codifies contribution standards

### 9.2 Gaps

| ID | Gap | Impact | Proposal |
|----|-----|--------|----------|
| **D-1** | **No security considerations doc** | High | Document auth strategy, CORS policy, secret management, rate limiting decisions |
| **D-2** | **No API contract doc** | Medium | While OpenAPI is auto-generated, there's no human-readable API reference with examples |
| **D-3** | **Stale pointer files** | Low | 5+ `(Moved)` pointer files in `/docs/` root — clean up or set up redirects |
| **D-4** | **No component gallery/Storybook** | Medium | Frontend devs can't browse available components visually |
| **D-5** | **No ADR (Architecture Decision Record) for the project itself** | Medium | Key decisions (SQLite vs Postgres, LangGraph choice, dual graph factories) not documented |
| **D-6** | **No runbook/playbook** for production operations | Medium | No documented procedures for backup, restore, troubleshooting |
| **D-7** | **Logging standards not documented** | Low | Inconsistent logging levels and formats across modules |

---

## 10. Feature Enhancement Proposals

### 10.1 Chat Experience Enhancements

| ID | Feature | Value | Effort | Status |
|----|---------|-------|--------|--------|
| **FE-1** | **Streaming chat responses (SSE)** | 🔴 High — table-stakes for AI chat UX | Medium — requires backend SSE endpoint + frontend EventSource | ✅ Implement |
| **FE-2** | **Copy message button** on all chat messages | 🟠 High | Low — single component change | ✅ Implement |
| **FE-3** | **Message regeneration** ("Regenerate" button) | 🟡 Medium | Low — re-send last user message | ✅ Implement |
| **FE-4** | **Message editing** | 🟡 Medium | Medium — UI for inline editing + resend | ✅ Implement |
| **FE-5** | **Conversation naming/search** | 🟡 Medium | Medium — backend schema change + UI | ✅ Implement |
| **FE-6** | **Conversation export** (Markdown/JSON/PDF) | 🟡 Medium | Low — frontend-only formatting | ✅ Implement |

### 10.2 Navigation & Discovery

| ID | Feature | Value | Effort | Status |
|----|---------|-------|--------|--------|
| **FE-7** | **Breadcrumb navigation** | 🔴 High — reduces disorientation | Low — component + route context | ✅ Implement |
| **FE-8** | **Global project search/filter** | 🟠 High | Low — filter on existing list | ✅ Implement |
| **FE-9** | **Artifact search within project** | 🟡 Medium | Medium — index artifact content | ✅ Implement |
| **FE-10** | **Conversation history search** | 🟡 Medium | Medium — full-text search on messages | ✅ Implement |

### 10.3 Workspace Improvements

| ID | Feature | Value | Effort | Status |
|----|---------|-------|--------|--------|
| **FE-11** | **Drag-and-drop file upload** | 🟡 Medium | Low — HTML5 drag events + drop zone | ✅ Implement |
| **FE-12** | **Persist open tabs across sessions** | 🟡 Medium | Low — save to localStorage | ✅ Implement |
| **FE-13** | **Tab state persistence across sessions** | 🟡 Medium | Low — save active tab + order | ✅ Implement |
| **FE-14** | **Inline document editing** | 🟡 Medium | High — requires editor component | ✅ Implement |
| **FE-15** | **Project templates** ("Web App 3-tier", "Microservices", etc.) | 🟡 Medium | Medium — predefined ProjectState seeds | ✅ Implement |

### 10.4 Export & Portability

| ID | Feature | Value | Effort | Status |
|----|---------|-------|--------|--------|
| **FE-16** | **Full project export** (JSON archive) | 🟠 High | Medium — backend endpoint + download | ✅ Implement |
| **FE-17** | **Project import** from JSON | 🟠 High | Medium — backend endpoint + upload | ✅ Implement |
| **FE-18** | **Diagram export** as PNG/SVG | 🟡 Medium | Low — mermaid already generates SVG | ✅ Implement |
| **FE-19** | **Proposal export as Word/PDF** | 🟡 Medium | Medium — document generation library | ✅ Implement |

### 10.5 Collaboration & Multi-User

| ID | Feature | Value | Effort | Status |
|----|---------|-------|--------|--------|
| **FE-20** | **User authentication** (Entra ID) | 🔴 Critical for multi-user | High — full auth stack | ✅ Implement |
| **FE-21** | **Project sharing / team workspaces** | 🟡 Medium | High — authorization model | ✅ Implement |
| **FE-22** | **Audit trail** (who changed what) | 🟡 Medium | Medium — event sourcing | ✅ Implement |
| **FE-23** | **Real-time collaboration** (WebSocket) | 🟢 Nice-to-have | Very High | ✅ Implement |

### 10.6 Observability & Operations

| ID | Feature | Value | Effort | Status |
|----|---------|-------|--------|--------|
| **FE-24** | **Structured JSON logging** | 🟠 High | Low — configure logging formatter | ✅ Implement |
| **FE-25** | **Request tracing** (correlation IDs) | 🟠 High | Low — middleware adds X-Request-Id | ✅ Implement |
| **FE-26** | **Health dashboard** (backend status, MCP status, KB status) | 🟡 Medium | Medium — aggregate existing health checks | ✅ Implement |
| **FE-27** | **Usage analytics** (projects created, queries run) | 🟡 Medium | Medium — event tracking | ✅ Implement |
| **FE-28** | **Application Insights integration** | 🟡 Medium (for Azure deployment) | Medium — SDK setup | ✅ Implement |

### 10.7 UX Polish

| ID | Feature | Value | Effort | Status |
|----|---------|-------|--------|--------|
| **FE-29** | **Fix keyboard shortcut mismatch** | 🔴 Bug fix | Low — implement or remove false claims | ✅ Implement |
| **FE-30** | **Improve help system** (replace `alert()` with styled modal) | 🟡 Medium | Low | ✅ Implement |
| **FE-31** | **Contextual tooltips** on complex UI elements | 🟡 Medium | Low | ✅ Implement |
| **FE-32** | **Mobile-responsive navigation** | 🟡 Medium | Medium — hamburger menu + stacked layout | ⏸️ Deferred |
| **FE-33** | **Onboarding guided tour** | 🟡 Medium | Medium — step-by-step walkthrough | ⏸️ Deferred |
| **FE-34** | **Dark mode improvements** — verify all components render correctly | 🟡 Medium | Low — visual audit | ✅ Implement |
| **FE-35** | **Stale data indicators** — show visual cue when displayed data may be outdated | 🟢 Low | Low | ✅ Implement |

---

## 11. Prioritized Implementation Plan

### Decision Summary

| Category | Decision |
|----------|----------|
| **Security** | Only S-5 (DOMPurify for mermaid) now; S-1/S-2/S-3/S-4/S-6/S-7 deferred to later phase |
| **Architecture** | A-1, A-2, A-5, A-6 implement now; A-3 (shutdown), A-4 (DB consolidation) keep as-is |
| **Backend quality** | All B-1 through B-8 implement |
| **Frontend quality** | All F-1 through F-8 implement |
| **UX/UI** | Everything implement except FE-32 (mobile) and FE-33 (onboarding) deferred |
| **Testing** | All implement — target 100% coverage |

---

### Phase 1 — Implement Now (✅)

| # | Item | Category | Effort |
|---|------|----------|--------|
| 1 | Add DOMPurify for mermaid SVG | Security (S-5) | Low |
| 2 | Fix keyboard shortcut mismatch (bug) | UX (FE-29) | Low |
| 3 | Consolidate dual graph factories | Architecture (A-1) | Medium |
| 4 | Extract business logic from fat routers | Architecture (A-2) | Medium |
| 5 | Add lightweight event/message bus | Architecture (A-5) | Medium |
| 6 | Standardize API versioning (`/api/v1/`) | Architecture (A-6) | Low |
| 7 | Standardize error-to-status-code mapping | Backend (B-1) | Low |
| 8 | Add explicit DB rollback in exception handlers | Backend (B-2) | Low |
| 9 | Fix phase tracking fragility | Backend (B-3) | Low |
| 10 | Add ingestion start idempotency | Backend (B-4) | Low |
| 11 | Add document size validation before LLM | Backend (B-5) | Low |
| 12 | Standardize logging levels | Backend (B-6) | Low |
| 13 | Return 503 when AgentRunner unavailable | Backend (B-7) | Low |
| 14 | Add structured JSON logging | Backend (B-8) | Low |
| 15 | Add API retry logic with backoff | Frontend (F-1) | Low |
| 16 | Fix silent `.catch(() => null)` patterns | Frontend (F-2) | Low |
| 17 | Consolidate loading components | Frontend (F-3) | Low |
| 18 | Replace console.log with debug utility | Frontend (F-4) | Low |
| 19 | Add form validation library | Frontend (F-5) | Medium |
| 20 | Decompose dense hook aggregation | Frontend (F-6) | Low |
| 21 | Add stale-data indicators | Frontend (F-7) | Low |
| 22 | Standardize semantic vs utility styles | Frontend (F-8) | Low |
| 23 | Implement chat streaming (SSE) | Feature (FE-1) | Medium |
| 24 | Add copy button on chat messages | UX (FE-2) | Low |
| 25 | Add message regeneration | Feature (FE-3) | Low |
| 26 | Add message editing | Feature (FE-4) | Medium |
| 27 | Add conversation naming/search | Feature (FE-5) | Medium |
| 28 | Add conversation export | Feature (FE-6) | Low |
| 29 | Add breadcrumb navigation | UX (FE-7) | Low |
| 30 | Add global project search/filter | Feature (FE-8) | Low |
| 31 | Add artifact search within project | Feature (FE-9) | Medium |
| 32 | Add conversation history search | Feature (FE-10) | Medium |
| 33 | Add drag-and-drop file upload | UX (FE-11) | Low |
| 34 | Persist open tabs across sessions | UX (FE-12) | Low |
| 35 | Tab state persistence across sessions | UX (FE-13) | Low |
| 36 | Add inline document editing | Feature (FE-14) | High |
| 37 | Add project templates | Feature (FE-15) | Medium |
| 38 | Full project export (JSON) | Feature (FE-16) | Medium |
| 39 | Project import from JSON | Feature (FE-17) | Medium |
| 40 | Diagram export as PNG/SVG | Feature (FE-18) | Low |
| 41 | Proposal export as Word/PDF | Feature (FE-19) | Medium |
| 42 | User authentication (Entra ID) | Feature (FE-20) | High |
| 43 | Project sharing / team workspaces | Feature (FE-21) | High |
| 44 | Audit trail | Feature (FE-22) | Medium |
| 45 | Real-time collaboration (WebSocket) | Feature (FE-23) | Very High |
| 46 | Structured JSON logging | DevOps (FE-24) | Low |
| 47 | Request tracing (X-Request-Id) | DevOps (FE-25) | Low |
| 48 | Health dashboard page | Feature (FE-26) | Medium |
| 49 | Usage analytics | Feature (FE-27) | Medium |
| 50 | Application Insights integration | Feature (FE-28) | Medium |
| 51 | Improve help system (styled modal) | UX (FE-30) | Low |
| 52 | Contextual tooltips | UX (FE-31) | Low |
| 53 | Dark mode improvements (visual audit) | UX (FE-34) | Low |
| 54 | Stale data indicators in UI | UX (FE-35) | Low |
| 55 | Add Storybook for component library | DX (D-4) | Medium |
| 56 | Standardize empty state patterns | UX | Low |
| 57 | Add breadcrumb/back navigation in nested views | UX | Low |
| 58 | Make command palette discoverable | UX | Low |
| 59 | Fix focus indicators (a11y audit) | Accessibility | Low |
| 60 | Add screen reader announcements for dynamic content | Accessibility | Low |
| 61 | Backend test coverage to 100% | Testing | High |
| 62 | Frontend service layer tests (all 11 services) | Testing | Medium |
| 63 | Component smoke tests (all common/) | Testing | Medium |
| 64 | Contract tests (TS types ↔ Pydantic models) | Testing | Medium |
| 65 | Visual regression tests (Playwright) | Testing | Medium |
| 66 | Mutation testing (Stryker + mutmut) | Testing | Medium |
| 67 | Frontend hook tests (all untested hooks) | Testing | Medium |
| 68 | Frontend utility tests | Testing | Low |
| 69 | E2E tests for remaining workflows | Testing | Medium |

### Phase 2 — Deferred (⏸️)

| # | Item | Category | Reason |
|---|------|----------|--------|
| D-1 | Add authentication (Entra ID / JWT) | Security (S-1) | Later security phase |
| D-2 | Restrict CORS to frontend origin | Security (S-2) | Later security phase |
| D-3 | Add API rate limiting (slowapi) | Security (S-3) | Later security phase |
| D-4 | Add CSRF protection | Security (S-4) | Later security phase |
| D-5 | Add input length limits on models | Security (S-6) | Later security phase |
| D-6 | Add document size/type validation | Security (S-7) | Later security phase |
| D-7 | Service registry extensibility (shutdown) | Architecture (A-3) | Keep as-is |
| D-8 | Database consolidation | Architecture (A-4) | Keep dual-DB |
| D-9 | Mobile-responsive navigation | UX (FE-32) | Later UX phase |
| D-10 | Onboarding guided tour | UX (FE-33) | Later UX phase |

---

**Status**: Active  
**Last Updated**: 2026-03-01  
**Owner**: Engineering
