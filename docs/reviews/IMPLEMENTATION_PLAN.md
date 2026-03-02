# Implementation Plan

All items trace to `docs/reviews/COMPREHENSIVE_CODEBASE_REVIEW_2026-03-01.md`.  
TDD applies: write failing test → implement → refactor. Tests come first across the board.

---

## Phase 1 — Test Foundation

Build all test infrastructure and bring coverage to 100% before changing any production code. Every subsequent phase relies on these tests as a safety net.

---

### 1.1 — Setup coverage tooling

**What**: Configure coverage reporters so we can measure progress.

**Backend** — edit `pyproject.toml`:
- `uv add --dev pytest-cov`
- Add to `[tool.pytest.ini_options]`: `addopts = "--cov=backend/app --cov-report=term-missing --cov-report=html:backend/htmlcov"`

**Frontend** — edit `frontend/vitest.config.ts`:
- `npm install -D @vitest/coverage-v8 --workspace=frontend`
- Add `coverage` block: provider `v8`, reporters `['text', 'html']`, include `['src/**/*.{ts,tsx}']`
- Add script in `frontend/package.json`: `"test:coverage": "vitest run --coverage"`

**Done when**: `uv run pytest backend/tests -q` and `npm run test:coverage -w frontend` both print coverage tables.

---

### 1.2 — Backend shared fixtures

**What**: Review `backend/tests/conftest.py` and subdirectory conftest files. Ensure these fixtures exist (add what's missing):
- `async_session` — async SQLAlchemy session (in-memory SQLite)
- `test_client` — `httpx.AsyncClient` bound to the FastAPI app
- `mock_llm_provider` — returns canned LLM responses
- `mock_kb_manager` — returns canned KB query results
- `sample_project` — minimal project row in test DB

Create `backend/tests/fixtures/` with reusable test data dicts (sample documents, project payloads, agent states).

> **Subagent eligible**: Reading all existing conftest files to avoid duplication is a good subagent task — hand it the full `backend/tests/` tree and ask what fixtures already exist.

---

### 1.3 — Frontend shared test utilities

**What**: Create `frontend/src/__tests__/test-utils.tsx` with:
- `renderWithProviders(ui, options?)` — wraps component in Theme, Toast, Router providers
- `mockFetch(responses)` — mock `window.fetch` with URL-to-response mapping
- `createMockProject()` / `createMockChatMessage()` — factory functions matching TS types

---

### 1.4 — Backend tests: untested services

Write tests for every untested service. For each file below, create a test file under `backend/tests/services/` mirroring the source path.

> **Subagent eligible**: Each service is independent — multiple services can be tested in parallel by separate subagents. Hand each subagent one source file and ask it to produce a complete test file.

| Source file | Test to create | Min test cases |
|---|---|---|
| `services/kb/query_service.py` | `tests/services/kb/test_query_service.py` | 10 (valid query, missing KB, empty query, threshold fallback, max results, concurrent queries) |
| `services/ai/ai_service.py` | `tests/services/ai/test_ai_service_unit.py` | 10 (default provider, fallback chain, all-fail, caching, token count, rate limit) |
| `services/ai/interfaces.py` | `tests/services/ai/test_interfaces.py` | 3 (interface compliance checks) |
| `services/project/document_parsing.py` | `tests/services/project/test_document_parsing.py` | 12 (PDF, XLSX, DOCX, MD, txt, empty, corrupt, oversized, unsupported) |
| `services/project/document_service.py` | `tests/services/project/test_document_service.py` | 8 (upload, duplicate, get, not-found, list, delete) |
| `services/project/document_normalization.py` | `tests/services/project/test_document_normalization.py` | 6 (headings, whitespace, encoding, empty, code blocks, tables) |
| `services/project/project_service.py` | `tests/services/project/test_project_service.py` | 9 (CRUD, duplicate name, list, export/import if exists) |
| `services/project/chat_service.py` | `tests/services/project/test_chat_service.py` | 7 (create conversation, add message, history, limit, delete, rename, empty) |
| `services/llm_service.py` | `tests/services/test_llm_service.py` | Read file first, test public API |
| `services/pricing/pricing_normalizer.py` | `tests/services/pricing/test_pricing_normalizer.py` | 5 (VM pricing, storage pricing, missing fields, zero-qty) |
| `services/pricing/retail_prices_client.py` | `tests/services/pricing/test_retail_prices_client.py` | 5 (valid SKU, invalid SKU, unreachable API, response parsing, caching) |

For document parsing tests: create minimal binary stubs (1-page PDF, 1-sheet XLSX, 1-para DOCX) under `backend/tests/fixtures/documents/`. Keep under 10KB each.

---

### 1.5 — Backend tests: diagram services (11 files, all untested)

All files in `backend/app/services/diagram/`. Create one test file per source file.

> **Subagent eligible**: Have a subagent read all 11 diagram files, understand their dependencies, and produce tests. Pure-function files (validators, prompt builder) are easy wins.

Test in dependency order:
1. `syntax_validator.py` — valid/invalid Mermaid syntax
2. `semantic_validator.py` — valid/invalid diagrams
3. `c4_compliance_validator.py` — C4 model compliance
4. `visual_quality_checker.py` — complexity metrics
5. `validation_pipeline.py` — mock individual validators, test orchestration
6. `prompt_builder.py` — prompt construction from requirements
7. `ambiguity_detector.py` — ambiguous vs clear requirements
8. `llm_client.py` — mock LLM, test request/response/errors
9. `diagram_generator.py` — mock LLM + validation, test orchestration
10. `database.py` — CRUD for diagram storage
11. `project_diagram_helpers.py` — helper functions

Target: ~50 test cases across these 11 files.

---

### 1.6 — Backend tests: untested routers

| Source file | Test to create | Focus |
|---|---|---|
| `routers/project_management/project_router.py` | `tests/routers/test_project_router.py` | Each endpoint: valid→200, missing fields→422, bad ID→404, service error→proper status |
| `routers/kb_query/query_router.py` | `tests/routers/test_query_router.py` | Same pattern |
| `routers/settings/models_router.py` | `tests/routers/test_models_router.py` | Same pattern |

> **Subagent eligible**: Each router is independent, can be done in parallel.

---

### 1.7 — Backend tests: core, lifecycle, MCP, ingestion gaps

**Core modules**: Read `backend/app/core/` — test any untested files.

**Lifecycle** (`backend/app/lifecycle.py`): Test startup order, MCP-unavailable degradation, missing KB directory, shutdown cleanup.

**MCP client gaps**: Add tests for connection timeout, connection refused, request timeout, malformed response, retry with backoff, no retry on 4xx.

**Ingestion gaps**: Read existing 6 test files, identify coverage holes in pipeline stages, content hashing, phase transitions, concurrent jobs.

> **Subagent eligible**: A subagent can read existing ingestion tests and the source, then produce a gap report and missing tests.

---

### 1.8 — Backend coverage gate

Run `uv run pytest backend/tests -q`. Target: ≥95% line coverage. Set `--cov-fail-under=95` in config.

---

### 1.9 — Frontend tests: all 11 services

Create `frontend/src/__tests__/services/<name>.test.ts` for each:

`agentService`, `chatService`, `checklistService`, `config`, `ingestionApi`, `kbService`, `projectService`, `proposalService`, `serviceError`, `settingsService`, `stateService`

Per service: mock `fetch`, test happy path (correct URL/method/body sent, response parsed), test network error, test HTTP 4xx/5xx → proper error type.

> **Subagent eligible**: All 11 are independent, can be split across subagents.

---

### 1.10 — Frontend tests: untested hooks (17)

These hooks have NO tests: `useCallbackRef`, `useClickOutside`, `useErrorHandler`, `useFocusTrap`, `useIngestionJob`, `useIntersectionObserver`, `useKBHealth`, `useKBJobs`, `useKBList`, `useKBQuery`, `useKBWorkspace`, `useKnowledgeBases`, `useModelSelector`, `useProjectsData`, `useProjectSelector`, `useRenderCount`, `useTheme`.

Use `renderHook` from `@testing-library/react`. Per hook test: initial state, state transitions, cleanup on unmount, error states.

> **Subagent eligible**: Each hook is independent.

---

### 1.11 — Frontend tests: common components (15)

Create smoke + interaction tests for all `frontend/src/components/common/*.tsx`:

`Badge`, `Banner`, `Button`, `Card`, `EmptyState`, `ErrorBoundary`, `LoadingIndicator`, `LoadingSkeleton`, `LoadingSpinner`, `Navigation`, `PageLoader`, `StatCard`, `StatusBadge`, `Toast`

Per component: renders without crash, renders correctly with each prop variant, click/hover handlers fire, correct `aria-*` attributes.

---

### 1.12 — Frontend tests: utilities (3 files)

Test `apiMapping.ts`, `diagramCache.ts`, `typeGuards.ts`. Pure functions — straightforward unit tests.

---

### 1.13 — Frontend tests: key feature components

Test the most complex feature components (use `renderWithProviders`):
- Project tree
- Chat message + chat input
- Workspace tabs
- Mermaid diagram renderer
- Ingestion wizard steps
- KB query interface
- Command palette

Smoke tests + key interactions.

> **Subagent eligible**: Each component is independent.

---

### 1.14 — Contract tests (TS ↔ Pydantic)

Create `frontend/src/__tests__/contracts/api-contracts.test.ts`.

For each major endpoint, create a JSON fixture matching the Pydantic model's output and verify the frontend type can parse it. Cover at minimum: projects CRUD, KB list/query, agent chat, ingestion jobs, settings/models.

> **Subagent eligible**: Have one subagent extract all Pydantic response schemas, another extract all TS types, then write the contract tests.

---

### 1.15 — Visual regression tests (Playwright)

Create `frontend/tests/visual/`:
- `workspace-layout.spec.ts` — screenshots of empty workspace, loaded project, chat open
- `theme-switching.spec.ts` — light vs dark screenshots
- `components.spec.ts` — nav bar, command palette, toast

Add `expect.toHaveScreenshot({ maxDiffPixels: 100 })` in `playwright.config.ts`.

---

### 1.16 — E2E tests: remaining workflows

Create under `frontend/tests/`:
- `kb-query.spec.ts`
- `ingestion-errors.spec.ts`
- `settings.spec.ts`

---

### 1.17 — Frontend coverage gate

Run `npm run test:coverage -w frontend`. Target: ≥90% lines, ≥90% functions, ≥85% branches.

---

## Phase 2 — Security

Only S-5 is in scope. One focused change.

---

### 2.1 — S-5: DOMPurify for mermaid innerHTML

**Install**: `npm install dompurify @types/dompurify --workspace=frontend`

**Test first** — create `frontend/src/__tests__/components/diagrams/useMermaidRenderer.test.ts`:
- Valid SVG renders correctly
- SVG with `<script>` tag → stripped
- SVG with `onerror` attribute → stripped
- SVG with `javascript:` URI → stripped
- SVG with valid `<style>` → preserved
- Cache hit returns sanitized SVG

**Implement** — edit `frontend/src/components/diagrams/hooks/useMermaidRenderer.ts`:
- Import DOMPurify
- Wrap every `container.innerHTML = ...` (except clearing with `""`) in `DOMPurify.sanitize(html, { USE_PROFILES: { svg: true, svgFilters: true } })`

---

## Phase 3 — Architecture

4 items: A-1, A-2, A-5, A-6.

---

### 3.1 — A-1: Consolidate dual graph factories

**File**: `backend/app/agents_system/langgraph/graph_factory.py`

> **Subagent eligible**: Have a subagent read the full file plus all callers to map out what each factory function does and who calls it.

Steps:
1. Read `graph_factory.py` — identify the duplicate factory functions and their differences
2. Write tests covering both paths via a single unified function with a config parameter
3. Merge into one parameterized function. Keep old names as thin wrappers for backward compat.
4. Verify all existing agent tests pass.

---

### 3.2 — A-2: Extract business logic from fat routers

> **Subagent eligible**: Have a subagent identify the top 3 largest router files and which handlers contain business logic (DB queries, LLM calls, transformations) that should live in service files.

Steps per router:
1. Write service-layer tests for the logic being extracted
2. Move logic into `backend/app/services/` methods
3. Slim the router handler to: parse request → call service → format response (≤15 lines per handler)
4. Verify existing router tests still pass

---

### 3.3 — A-5: Add event bus

**Create**: `backend/app/core/event_bus.py`

Test first:
- Publish event → subscribed handler called
- Unsubscribed handler not called
- Handler exception → logged, other handlers still run
- No subscribers → publish succeeds silently

Implement simple class: `publish(event_type, payload)`, `subscribe(event_type, handler)`, `unsubscribe(event_type, handler)`. Dict of event_type → list of async callables.

Wire up 2 initial events as proof of concept:
- `ingestion.completed` → invalidate KB cache
- `project.deleted` → clean up resources

---

### 3.4 — A-6: API versioning

**Goal**: All endpoints accessible under `/api/v1/`.

Steps:
1. Test that `/api/v1/projects` returns 200
2. In `backend/app/main.py`: create `v1_router = APIRouter(prefix="/api/v1")`, mount all routers there
3. Keep `/api/*` temporarily working (dual-mount or redirect)
4. Update frontend `config.ts` base URL to `/api/v1/`

---

## Phase 4 — Backend Quality

B-1 through B-8. Each is small and self-contained.

---

### 4.1 — B-1: Centralized error-to-status mapping

Create `backend/app/core/error_handlers.py`. Register `@app.exception_handler` for `ValueError`→400, `NotFoundError`→404, `ServiceUnavailableError`→503. Standard response body: `{"detail": str, "error_code": str}`. Remove ad-hoc try/except→HTTPException blocks in routers.

### 4.2 — B-2: Explicit DB rollback

In every service `try/except` wrapping DB operations, add `await db.rollback()` before re-raising. Test: failed transaction → session is clean after error.

### 4.3 — B-3: Phase tracking fragility

In `_safe_phase_repo_call()`: replace silent `except: pass` with `except Exception as e: logger.warning(...)` and set phase to error state. Test: failure → error logged, progress accurate.

### 4.4 — B-4: Ingestion start idempotency

Before starting a job, check if one is already running for this KB. If so, return 409 with existing job ID. Test: two `/start` calls → second gets 409.

### 4.5 — B-5: Document size validation before LLM

Before sending combined doc text to LLM, estimate token count. If exceeding context window, raise `DocumentTooLargeError`. Consider `tiktoken` (`uv add tiktoken`) or word-count heuristic.

### 4.6 — B-6: Standardize logging levels

> **Subagent eligible**: Have a subagent grep all logging calls across `backend/app/` and produce a report of inconsistencies. Then batch-fix:

Rules:
- Caught exceptions indicating bugs → `logger.error(msg, exc_info=True)`
- Recoverable situations → `logger.warning(msg)`
- Normal operations → `logger.info(msg)`
- Never use `f"...{e!s}"` — always `exc_info=True`

### 4.7 — B-7: AgentRunner → 503

When `get_instance()` raises `RuntimeError`, catch it and raise `HTTPException(503, detail="Agent service temporarily unavailable")`. Or register in the centralized error handler from B-1.

### 4.8 — B-8: Structured JSON logging

Create `backend/app/core/logging_config.py` with JSON formatter. Configure on startup in `main.py`. Every log line must include: `timestamp`, `level`, `message`, `module`. Wire in `request_id` from FE-25 later.

---

## Phase 5 — Frontend Quality

F-1 through F-8.

---

### 5.1 — F-1: API retry with backoff

Create `frontend/src/services/fetchWithRetry.ts`. Wrap `fetch` with retry logic: retry on 5xx and network errors (1s→2s→4s backoff, max 3 retries), no retry on 4xx. Test first. Then replace `fetch()` calls in all services.

### 5.2 — F-2: Fix silent catch patterns

> **Subagent eligible**: Have a subagent search all `.catch(() =>` patterns in `frontend/src/`, list them, and propose fixes.

Replace each `.catch(() => null)` with `.catch(err => handleError(err))` using `useErrorHandler` or a logging function. Keep silent catch only where intentional (cleanup ops) — add a comment explaining why.

### 5.3 — F-3: Consolidate loading components

Analyze `PageLoader`, `LoadingSpinner`, `LoadingIndicator`, `LoadingSkeleton`. Keep ones with distinct purposes, remove duplicates. Migrate all usages of the removed component. Update `index.ts` barrel.

### 5.4 — F-4: Debug utility

Create `frontend/src/utils/debug.ts`: `debug.log()` only outputs when `import.meta.env.DEV`. Replace all `console.log` in non-test source files.

> **Subagent eligible**: Have a subagent find all `console.log` occurrences in `frontend/src/` (excluding test files) and batch-replace.

### 5.5 — F-5: Form validation

Install `react-hook-form zod @hookform/resolvers`. Integrate into one form as proof of concept (project creation or KB creation).

### 5.6 — F-6: Decompose useProjectDetails

Read `useProjectDetails` (~150 LOC). Split into smaller focused hooks. The original becomes a thin composition calling the sub-hooks. Test each sub-hook individually.

### 5.7 — F-7: Stale-data indicators

Create `frontend/src/components/common/StaleDataBanner.tsx`: when `isStale=true`, show "Data may be outdated" banner with refresh button. Integrate into components that fetch data.

### 5.8 — F-8: Style convention

Document the rule at top of main CSS file: semantic classes (`ui-btn`) for reusable patterns in `@layer components`, raw Tailwind for one-off styling. Fix the worst violations where both are mixed on the same element.

---

## Phase 6 — Observability

FE-24, FE-25, FE-26, FE-27, FE-28.

---

### 6.1 — FE-25: Request tracing (X-Request-Id)

Create `backend/app/middleware/request_id.py`: Starlette middleware that reads or generates UUID for `X-Request-Id`, stores in context var, adds to response headers. Register in `main.py`. Wire into structured logging from B-8.

### 6.2 — FE-28: Application Insights

Backend: add `azure-monitor-opentelemetry`. Frontend: add App Insights JS SDK. Read connection string from environment variable (do NOT touch `.env`). Initialize on startup.

### 6.3 — FE-26: Health dashboard

Create `frontend/src/features/health/HealthDashboard.tsx`. Display: backend up/down, MCP connected/disconnected, KB indices loaded, last startup, active jobs. Call a `/api/v1/health` endpoint. Add route.

### 6.4 — FE-27: Usage analytics

Create `backend/app/services/analytics_service.py`. Track counts (projects, queries, jobs, chats) in DB. Expose via `/api/v1/analytics`. Display on health dashboard.

---

## Phase 7 — UX/UI Fixes

---

### 7.1 — FE-29: Fix keyboard shortcut mismatch (BUG)

Find where `Ctrl+/` and `Ctrl+Enter` are advertised in help text. Either implement the shortcuts or remove the false claims. Test: press shortcut → expected action happens.

### 7.2 — FE-7: Breadcrumb navigation

Create `frontend/src/components/common/Breadcrumb.tsx`. Show path like "Projects > MyProject > ADRs > ADR-001". Read from route context. Add "← Back" button in artifact detail views.

### 7.3 — Command palette discoverability

Add "Press Ctrl+K" hint in empty states. Add keyboard icon in header that opens command palette on click.

### 7.4 — FE-30: Help system

Replace `alert()` calls with a `HelpModal` component using existing modal patterns.

> **Subagent eligible**: Have a subagent find all `alert(` calls in `frontend/src/`.

### 7.5 — FE-31: Contextual tooltips

Add tooltips to tree node actions, toolbar buttons, status indicators. Use `title` attribute or a tooltip component.

### 7.6 — FE-34: Dark mode audit

Open every major view in dark mode. Fix text readability, background contrast, invisible icons.

### 7.7 — Empty state standardization

Find all custom empty-state markup. Replace with the `EmptyState` common component. Consistent icon, text, and CTA button.

> **Subagent eligible**: Have a subagent search for empty-state patterns across features.

### 7.8 — Accessibility (Section 6.6)

Add `focus-visible:ring-2` where missing on interactive elements. Add `aria-live="polite"` for chat messages, ingestion status changes. Verify existing `aria-live` usage.

---

## Phase 8 — Features: Chat, Navigation, Workspace

---

### 8.1 — FE-1: Streaming chat (SSE) ⚡ highest impact

**Backend**: Create `POST /api/v1/agent/chat/stream` returning `StreamingResponse` with `text/event-stream`. Each event: `data: {"chunk": "text", "done": false}\n\n`. Final: `data: {"chunk": "", "done": true, "sources": [...]}\n\n`. Modify agent runner to yield intermediate results.

**Frontend**: Create `useStreamingChat` hook using `fetch` + `ReadableStream` (or `EventSource`). Update chat UI to show message growing as chunks arrive. Show typing indicator. Keep non-streaming path as fallback.

> **Subagent eligible**: Backend and frontend parts are independent and can be done by separate subagents.

### 8.2 — FE-2: Copy message button

Add clipboard icon on each chat message. `navigator.clipboard.writeText()`. Show "Copied!" toast.

### 8.3 — FE-3: Message regeneration

Add "Regenerate" button below assistant messages. Re-submit the preceding user message.

### 8.4 — FE-4: Message editing

Add edit icon on user messages. Click → inline textarea. Submit → re-send to agent, replace subsequent messages.

### 8.5 — FE-5: Conversation naming/search

Backend: add `name` field to conversation model, add rename endpoint. Frontend: conversation sidebar with list, inline rename, search filter, delete button.

### 8.6 — FE-6: Conversation export

Export button in conversation header. Formats: Markdown (`# Conversation\n\n## User\n...`), JSON (raw array). PDF via `window.print()` with print CSS.

### 8.7 — FE-8: Global project search

Search input above project list. Filter client-side by project name.

### 8.8 — FE-9: Artifact search within project

Search box in project tree panel. Search artifact names and optionally content.

### 8.9 — FE-10: Conversation history search

Search in conversation sidebar. Full-text search on messages. May need backend search endpoint.

### 8.10 — FE-11: Drag-and-drop upload

Add `onDragOver` + `onDrop` on workspace panel. Show drop zone overlay. Use existing upload service.

### 8.11 — FE-12 + FE-13: Tab persistence

On tab change → save to `localStorage` (key: `tabs-${projectId}`). On mount → restore. Save: tab IDs, order, active tab, pinned state.

### 8.12 — FE-14: Inline document editing

Add edit toggle to document detail. For Markdown: integrate a Markdown editor (e.g. CodeMirror or `@uiw/react-md-editor`). For plain text: auto-resize textarea. Save via PUT to backend. Read-only for binary formats.

### 8.13 — FE-15: Project templates

Define 3-5 templates as JSON in `frontend/src/data/projectTemplates.ts`: "Web App 3-tier", "Microservices", "Data Pipeline", "ML Workload", "Blank". On selection: create project + pre-populate artifacts via API.

---

## Phase 9 — Features: Export, Collaboration, Operations

---

### 9.1 — FE-16 + FE-17: Project export/import

Backend: `GET /api/v1/projects/{id}/export` → JSON with all data. `POST /api/v1/projects/import` → create from JSON. Frontend: Export button → download. Import button on project list → file picker.

### 9.2 — FE-18: Diagram export PNG/SVG

SVG: serialize the rendered SVG DOM node. PNG: render SVG to canvas, `toDataURL('image/png')`.

### 9.3 — FE-19: Proposal export Word/PDF

Word: use `docx` npm package. PDF: `window.print()` with print-optimized CSS.

### 9.4 — FE-20: User authentication (Entra ID) ⚠️ high effort

Backend: add JWT validation middleware, extract user identity from Entra ID tokens, `current_user` dependency. Frontend: add `@azure/msal-react`, login/logout flow, attach bearer token to all API calls.

**Confirm with user before starting**: needs Tenant ID and Client ID.

### 9.5 — FE-21: Project sharing (depends on 9.4)

Project → user association in DB. Sharing UI: invite by email, roles (viewer/editor/admin). Authorization checks on API endpoints.

### 9.6 — FE-22: Audit trail

Create `audit_log` table. Log: project CRUD, document CRUD, conversations, settings changes. Include user ID, action, timestamp. Add viewer in project settings.

### 9.7 — FE-23: Real-time collaboration ⚠️ very high effort

Start with "presence" only: WebSocket showing who's online in a project. Full collaborative editing (CRDT) is a separate workstream.

---

## Phase 10 — Performance

---

### 10.1 — P-1: Response caching

LRU cache with 5-min TTL for KB query and agent responses. Invalidate on KB update. Use `cachetools.TTLCache`.

### 10.2 — P-2: Bundle size budget

Set `build.chunkSizeWarningLimit: 500` in `vite.config.ts`. Add bundle analyzer for dev.

### 10.3 — P-3: Mermaid render cache

Verify `diagramCache.ts` is properly integrated with the mermaid renderer hook. Same diagram code → cached SVG, no re-render.

### 10.4 — P-4: Project list pagination

Add `page` + `per_page` params to `/api/v1/projects`. Frontend: pagination controls or infinite scroll.

### 10.5 — P-5: LLM streaming

Already covered by FE-1 (8.1). Verify it works.

### 10.6 — P-6: Large dependency optimization

Verify `mermaid` and `recharts` are code-split. If not, add `lazy(() => import(...))`. Only change if chunks exceed 500KB.

---

## Phase 11 — Documentation

---

### 11.1 — D-1: Security doc → `docs/SECURITY.md`

Auth strategy, CORS policy, secret management, rate limiting, input validation, XSS prevention.

### 11.2 — D-2: API reference → `docs/API_REFERENCE.md`

Human-readable docs with endpoint, method, description, request/response examples.

### 11.3 — D-3: Clean stale pointer files

> **Subagent eligible**: Have a subagent find all files in `docs/` containing "(Moved)" and list them.

Delete or update each.

### 11.4 — D-4: Storybook

`npx storybook@latest init --builder vite --type react`. Create stories for all common components. Script: `"storybook": "storybook dev -p 6006"`.

### 11.5 — D-5: ADRs → `docs/architecture/decisions/`

5 ADRs: SQLite choice, LangGraph choice, dual-DB architecture, LlamaIndex choice, MCP protocol choice. Standard format: Status / Context / Decision / Consequences.

### 11.6 — D-6: Runbook → `docs/operations/RUNBOOK.md`

Backup, restore, troubleshooting, monitoring, scaling.

### 11.7 — D-7: Logging standards → `docs/LOGGING_STANDARDS.md`

Levels, JSON format, correlation IDs, sensitive data exclusion.

### 11.8 — Update docs/README.md

Add links to all new docs.

---

## Phase 12 — Mutation Testing & Final Validation

---

### 12.1 — Setup mutation testing tools

Backend: `uv add --dev mutmut`. Frontend: `npm install -D @stryker-mutator/core @stryker-mutator/vitest-runner --workspace=frontend`.

### 12.2 — Run backend mutations

Start with `backend/app/core/` and `backend/app/services/`. Kill surviving mutants by adding more tests.

### 12.3 — Run frontend mutations

Start with utils and hooks. Kill survivors.

### 12.4 — Final coverage + lint

- `uv run pytest backend -q` → ≥95% coverage
- `npm run test:coverage -w frontend` → ≥90% coverage
- `npx playwright test`
- `npm run lint:fast:strict:fix -w frontend`
- `uvx ruff check --fix backend/`
