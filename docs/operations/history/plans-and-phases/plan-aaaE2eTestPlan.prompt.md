## Plan: E2E Validation Suite (LangGraph + Stage Routing ON) with 3 Scenarios

TL;DR: Build a deterministic, on-demand E2E harness that runs **US1→US7** for **3 RFP scenarios** using **LangGraph only** with **stage routing enabled**, hitting the **real backend + live MCP/Pricing APIs** (retry 3x then fail). Store **golden transcripts and JSON run reports in the repo** for prompt iteration. Provide two modes: **backend-only** and **frontend+backend**.

## Non-negotiables (from spec + decisions)
- Engine: LangGraph only.
- Stage routing: ON for every run.
- Live integrations: Microsoft Learn MCP + Azure Retail Prices API.
- Retry policy: 3 attempts then FAIL (to expose bugs).
- Inputs: before US1, scenario docs and any pre-US1 messages MUST NOT mention specific technologies/services.
- After US1: technical architect discussion is simulated (may include tech names).
- Two modes: backend-only and frontend+backend (Playwright headless by default).
- Storage: goldens + run reports are committed to the repo; goldens auto-promote when pass.

### Steps
1. **Lock runtime mode (LangGraph + stage routing ON)**
   - Test runner forces LangGraph engine and stage routing ON for all runs.
   - Each scenario runs as a fresh project and executes **US1→US7 sequentially**.

2. **Create 3 RFP datasets (tech-agnostic inputs pre‑US1)**
   - Scenario A: Enterprise AI-Powered CMS (no tech names in docs).
   - Scenario B: Regulated customer portal (no tech names in docs).
   - Scenario C: Event-heavy case/order processing (no tech names in docs).
   - Each dataset includes mixed inputs (PDF/MD/XLSX/text) + a manifest describing expected ambiguities and constraints (still tech-agnostic).

3. **Implement a shared “full journey” runner (US1→US7)**
   - US1: ingestion/extraction + C4 L1.
   - Post‑US1: technical conversation script begins (allowed to mention tech).
   - US2–US7: candidates, ADRs, validation, IaC validation, costs (Pricing API), mind map + traceability export.

4. **Script the post‑US1 architect discussion (natural, not mechanical)**
   - Multi-turn clarifications, contradiction injection, decision reversal (ADR supersede), and a “human edit authoritative” test.
   - Assertions remain mostly structural (artifacts exist, links exist, conflicts surfaced), while quality is reviewed via stored transcripts.

5. **Live integration rules (MCP + Pricing API)**
   - External calls: retry 3 times with backoff+jitter; fail the run if still failing.
   - Persist in JSON: query terms, URLs, attempts, latency, which artifact consumed which source.

6. **Two runnable modes**
   - **Backend-only mode**: runs the whole scenario via backend APIs and validates stored artifacts + transcripts + JSON report.
   - **Frontend+backend mode**: runs the same scenario through the UI with Playwright against the real backend (chat, uploads, diagrams, artifact views).
   - Both modes write results to the same report schema so you can compare runs.

7. **Golden transcripts + JSON reports stored in the repo**
   - Commit per-scenario “golden” transcripts and baseline JSON (expected structural fields, not exact wording).
   - On new runs, store a timestamped report and produce a diff summary (what changed: citations count, missing links, new clarifications, etc.).

### Further Considerations
1. Golden transcripts/baselines are automatically promoted when a scenario run passes.
2. For frontend+backend runs: Playwright runs headless by default.

## Runner workflow (US1→US7) with minimal assertions

Goal: keep gates structural (to avoid mechanical conversations) while still catching regressions against mandatory requirements.

### US1 — Ingest & extract requirements
Actions:
- Create project.
- Upload scenario files (PDF/MD/XLSX/text) and run ingestion.
- Ask assistant to summarize extracted requirements and ambiguities.

Minimum assertions:
- Project has a normalized corpus and ingestion status is completed/partial-with-errors.
- Requirements are categorized (business/functional/NFR) with at least one ambiguity/gap flagged.
- C4 L1 context diagram exists and is attached/versioned.
- Any failed document extraction has a recorded reason (no silent failure).

### US2 — Candidate architectures
Actions:
- Ask for at least one candidate architecture + assumptions and rationale.
- Ask for diagram update to C4 L1/L2.
- Trigger WAF checklist initialization.

Minimum assertions:
- ≥1 candidate architecture exists with assumptions.
- Diagrams updated (L1 remains, L2 exists or an explicit reason is stored).
- WAF checklists exist for all pillars with covered/partial/not-covered states.
- Sources are recorded: at least one reference doc or MCP query result linked to the candidate.

### US3 — Decisions & ADRs
Actions:
- Ask to record one key decision as ADR.
- Change ADR status (draft → accepted).
- Create a superseding ADR and mark the prior as superseded.

Minimum assertions:
- ADR fields: context/decision/consequences exist.
- Status transitions are recorded with timestamps.
- Superseded ADR references the prior ADR (traceability preserved).
- ADR includes at least one source reference or MCP query record.

### US4 — Validation & findings
Actions:
- Trigger architecture validation.

Minimum assertions:
- Findings exist with: severity, impacted component(s), WAF pillar/topic reference, remediation suggestion.
- WAF checklist states update after validation.
- If reference guidance conflicts, assistant surfaces options/trade-offs (does not auto-select).

### US5 — IaC & static validation
Actions:
- Request IaC generation (Bicep and/or Terraform) aligned to architecture.
- Run static validation/lint on generated IaC artifacts.

Minimum assertions:
- IaC artifact files exist and are linked to architecture components.
- Validation status recorded (pass/fail). If fail, error output captured.
- IaC artifacts cite at least one reference doc or MCP query.

### US6 — Costs (Azure Retail Prices API)
Actions:
- Request cost estimate.

Minimum assertions:
- Cost breakdown exists with key drivers and assumptions.
- Azure Retail Prices API usage is logged.
- If some services can’t be priced (missing meter/SKU/usage inputs), those are recorded as explicit assumptions and variancePct omitted rather than misleading.

### US7 — Mind map & traceability + iteration evidence
Actions:
- Ask for traceability export (requirements → ADRs → diagrams → WAF → IaC → costs).
- Ask assistant to identify uncovered mind map topics and propose clarification prompts.
- Simulate one human-authored edit to an artifact (e.g., append a line in an ADR text field) and then request the assistant to “update” it.

Minimum assertions:
- Traceability links exist and resolve (no broken IDs in the export).
- Mind map coverage report references all 13 top-level topics (addressed/partial/not-addressed).
- Human edits are not overwritten; conflicts are detected and surfaced.
- Iteration evidence exists: at least one propose/challenge note with sources and an architect response.

## Scenario pack format (repo-committed)

Store under a single folder per scenario. Inputs are tech-agnostic; technical details come from post-US1 chat script.

Recommended layout:
- scenario.json: metadata + invariants + scripted conversation.
- inputs/: PDFs/MD/XLSX/text inputs.
- goldens/: baseline transcript + baseline report JSON + baseline artifacts export (if supported).

### scenario.json (minimum schema)
- id, title, description
- inputConstraints: { noExplicitTechInInputs: true }
- preUS1: { files: [...], optionalUserMessage: "..." }
- postUS1Conversation: [ {role: "user", text: "..."}, {role: "user", text: "..."}, ... ]
- injections:
   - contradictionTurnIndex
   - humanEdit: { targetArtifactType, targetIdSelector, appendText }
- expectations (minimal structural expectations): { mustHaveAmbiguities: true, mustProduceL1: true, ... }

## Three scenarios (tech-agnostic inputs + post-US1 technical scripts)

### Scenario A: Enterprise AI-Powered CMS (tech-agnostic inputs)
Inputs (no tech names):
- Editorial workflow description (roles, approvals, SLAs).
- Content governance (retention, audit, legal hold).
- “Smart search” requirement (semantic retrieval) without naming any product.
- Data residency + tenant isolation expectations.
- Traffic profile and cost sensitivity.

Post-US1 technical discussion script (example):
1) “We need strict tenant isolation. What partitioning strategy and access boundaries do you recommend?”
2) “Content must be searchable with semantic relevance and citations. How would you design retrieval and grounding?”
3) “We require private network access to all data services. What networking approach would you pick?”
4) Contradiction injection: “We now require cross-region active-active writes, but also strong consistency everywhere. Present options and trade-offs.”
5) “Record an ADR for the chosen consistency/availability trade-off.”
6) “Run validation and list top 5 findings with remediation.”
7) “Generate IaC and validate it.”
8) “Estimate monthly costs and list assumptions.”

### Scenario B: Regulated Customer Portal (tech-agnostic inputs)
Inputs (no tech names):
- External customer access + internal admin operations.
- Regulatory/audit requirements described as controls (no vendor/product references).
- RTO/RPO targets and incident response expectations.
- Peak usage and latency goals.

Post-US1 technical discussion script (example):
1) “We need strong identity controls, conditional access, and detailed audit logs. Propose an approach.”
2) “We require end-to-end encryption and key rotation. How do you design key management and secret handling?”
3) “Define observability: logs/metrics/traces, alerting, and SLOs.”
4) Contradiction injection: “We must minimize cost, but also need 99.99% availability. Propose options and note what we trade.”
5) “Create an ADR for availability vs cost.”
6) “Run validation and update WAF checklist states.”
7) “Generate IaC + validate. Produce cost estimate.”

### Scenario C: Event-Heavy Case/Order Processing (tech-agnostic inputs)
Inputs (no tech names):
- High throughput “events” and downstream processing.
- Requirements for retries, idempotency, reconciliation, dead-letter handling.
- Reporting needs and data freshness expectations.

Post-US1 technical discussion script (example):
1) “We need reliable messaging with retries and exactly-once effects. Propose patterns for idempotency and deduplication.”
2) “We need near-real-time reporting and long-term audit history. How would you model data flows?”
3) “Define failure handling strategy (poison messages, DLQ, replay).”
4) Contradiction injection: “We now require strict ordering per customer, but also maximum throughput globally. Provide options.”
5) “Create ADR for ordering guarantees.”
6) “Run validation, IaC generation/validation, and cost estimate.”

## Live integration reliability policy (retry 3 then fail)

Retryable conditions:
- Network timeouts / connection resets.
- HTTP 429 / 5xx from external services.
- MCP transient protocol errors.

Non-retryable conditions (fail immediately):
- Authentication/authorization errors.
- Invalid request (4xx other than 429).

Backoff policy:
- Attempt 1: immediate
- Attempt 2: wait 0.75s + jitter
- Attempt 3: wait 2.0s + jitter
- Then fail and capture full diagnostics in report.

## Backend-only vs frontend+backend modes

Backend-only:
- Drive the full workflow through backend APIs.
- Persist: transcript (messages sent/received), artifacts snapshot/export, MCP/pricing logs.

Frontend+backend (Playwright, headless):
- Drive the same script through UI: upload, chat, trigger actions, verify rendering.
- Additional captures: screenshot on failure, network log (HAR) on failure.

## Report schema (JSON) + golden promotion

### JSON report (per scenario run)
- run: { scenarioId, mode, startedAt, finishedAt, gitSha, config: { engine: "langgraph", stageRouting: true } }
- transcript: [ { ts, channel: "ui"|"api", role: "user"|"assistant", text, messageId } ]
- artifacts: { requirements: [...], diagrams: [...], adrs: [...], waf: {...}, iac: {...}, costs: {...}, traceability: {...} }
- externalCalls:
   - mcp: [ { tool, queryTerms, urls, attempts, latencyMs, linkedArtifactIds } ]
   - pricing: [ { requestSummary, attempts, latencyMs, status } ]
- assertions: [ { id, description, passed, details } ]
- observations: { uncoveredMindMapTopics: [...], conflictsDetected: [...], notes: [...] }
- diffVsGolden: { changedFields: [...], addedFindings: n, removedFindings: n, brokenLinks: n }

### Golden artifacts (repo)
- goldens/transcript.json (baseline transcript)
- goldens/report.json (baseline structural snapshot)

Auto-promotion rule:
- If all minimal assertions pass for a scenario run, update goldens for that scenario with the new transcript/report and commit the change.
- If tests fail, never promote; store the failed report for debugging.
