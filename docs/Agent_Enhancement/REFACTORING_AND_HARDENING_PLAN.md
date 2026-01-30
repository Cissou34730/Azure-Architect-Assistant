# Refactoring & Hardening Plan
**Status:** Active | **Date:** 2026-01-22  
**Goal:** Harden persistence layer, reinforce testing, ensure agent is a proactive architectural advisor

---

## Executive Summary

Current state: E2E harness validates LangGraph orchestration and tool calls, but **does not prove** the core product contract:
- ADRs, diagrams, and WAF checklist are **persisted and retrievable**
- State can be **modified and evolved** across conversations
- Agent acts as a **proactive architectural advisor** (not just a reactive chatbot)

This plan addresses gaps in:
1. **Persistence testing** (empty DBs, missing artifacts)
2. **KB/RAG integration** (WAF ReAct loop validation)
3. **ADR + diagram storage** (structured, versionable)
4. **Agent behavior** (force of proposition: feedback, corrections, proactive suggestions)
5. **Spec alignment** (system prompt, tool usage, stage routing)

---

## 1. Testing Approach: Make Persistence the Contract

### Current Gap
- E2E runner validates chat completions and scenario assertions, but **does not verify DB persistence**
- `projects.db` and `diagrams.db` are empty after E2E runs
- No "retrieve-modify-retrieve" cycle to prove state evolution

### Actions
#### 1.1 Add DB Contract Layer to E2E Runner
**Priority:** P0 (blocker for all other work)

```python
# New E2E assertions post-run:
- assert_project_exists_in_db(project_id)
- assert_project_state_persisted(project_id)
- assert_waf_checklist_items_count(project_id, min_items=1)
- assert_adrs_persisted(project_id, min_count=1)
- assert_diagrams_persisted(project_id, diagram_db_or_state="state")  # See section 3
```

**Files to modify:**
- `scripts/e2e/aaa_e2e_runner.py`: add `_assert_db_persistence()` helper
- `scripts/e2e/_debug_db_presence.py`: use as library for DB queries

#### 1.2 Add Retrieve-Modify-Retrieve Step
**Priority:** P0

New E2E scenario step (after validation):
```json
{
  "id": "us7-modify-adr",
  "message": "Append a risk mitigation to ADR-001 decision section."
}
```

**Assertions:**
- Before: GET `/api/projects/{id}/state` → capture ADR-001 text length
- After modify: assert ADR-001 text length increased
- Verify modification persisted across GET calls

**Files to create:**
- E2E scenario: `scripts/e2e/scenarios/scenario-b/scenario.json` (modify-state flow)

#### 1.3 Make E2E DB-Isolated
**Priority:** P1

**Problem:** in-process runs may write to shared `backend/data/*.db`, causing cross-run pollution.

**Solution:**
- Add `--data-root <path>` to E2E runner
- Set env vars before app startup:
  ```python
  os.environ["PROJECTS_DATABASE"] = f"{data_root}/projects.db"
  os.environ["DIAGRAMS_DATABASE"] = f"{data_root}/diagrams.db"
  os.environ["INGESTION_DATABASE"] = f"{data_root}/ingestion.db"
  ```
- Runner writes DB paths into run report for validation

**Acceptance Criteria:**
- ✅ Each E2E run writes to its own DB folder
- ✅ Run report includes actual DB paths used
- ✅ DB validator checks those exact paths

---

## 2. Persistence Correctness: Fix "Empty DB / Wrong DB" Ambiguity

### Current Gap
- Unclear which DB path the app writes to during in-process E2E
- No logging confirms persistence events

### Actions
#### 2.1 Add DB Path Logging at Startup
**Priority:** P0

**Files to modify:**
- `backend/app/projects_database.py`: log resolved `DB_PATH` at module load
- `backend/app/services/diagram/database.py`: log diagram DB path during `initialize()`

```python
logger.info(f"Projects DB resolved: {DB_PATH.absolute()}")
logger.info(f"Diagrams DB resolved: {db_file.absolute()}")
```

#### 2.2 Add Persistence Event Logging
**Priority:** P1

Log at INFO level when:
- Project row inserted (`ProjectService.create_project`)
- ProjectState created/updated (`DocumentService.analyze_documents`, `update_project_state`)
- Diagram persisted (`_store_generated_diagram`)

**Acceptance Criteria:**
- ✅ App logs clearly show "Project abc created in /path/to/projects.db"
- ✅ E2E runner captures these logs and includes them in run report

---

## 3. Diagrams: Persist via Diagram-Set API (Option A)

### Current Gap
- Agent produces Mermaid text in chat answer, but **does not persist** to `diagrams.db`
- No way to retrieve/version/evolve diagrams after creation

### Actions
#### 3.1 Create `aaa_create_diagram_set` Tool
**Priority:** P0

**Tool signature:**
```python
async def aaa_create_diagram_set(
    input_description: str,
    adr_id: str | None = None,
    project_id: str | None = None,  # for state updates
) -> dict:
    """
    Generate and persist diagrams (Mermaid functional, C4 context, C4 container).
    Returns diagram set ID and individual diagram IDs.
    """
```

**Behavior:**
1. Call diagram generation service (existing): `POST /api/v1/diagram-sets`
2. Store returned `diagramSetId` and diagram refs into `ProjectState.diagrams[]`
3. Return diagram set ID to agent

**Files to create:**
- `backend/app/agents_system/tools/aaa_diagram_tool.py`

**Files to modify:**
- `backend/app/agents_system/langgraph/nodes/research.py`: add diagram tool to stage toolset
- System prompt: require agent to call this tool when asked for diagrams

#### 3.2 Update ProjectState Diagram Schema
**Priority:** P0

```python
# backend/app/agents_system/services/aaa_state_models.py
class DiagramReference(BaseModel):
    diagram_set_id: str
    diagram_type: str  # "mermaid_functional" | "c4_context" | "c4_container"
    diagram_id: str
    version: str
    created_at: str

# AAAProjectState.diagrams: list[DiagramReference]
```

**Acceptance Criteria:**
- ✅ After diagram turn, `diagrams.db` has rows in `diagram_sets` and `diagrams` tables
- ✅ `ProjectState.diagrams[]` contains references linking to those rows
- ✅ GET `/api/v1/diagram-sets/{id}` returns persisted diagrams

---

## 4. ADRs: Introduce ADR Template + Persistence Tool

### Current Gap
- No structured ADR schema enforcement
- ADRs are freeform text in agent response
- No "propose ADR template" behavior if none exists

### Actions
#### 4.1 Define ADR Schema
**Priority:** P0

```python
# backend/app/agents_system/services/aaa_state_models.py
class AdrArtifact(BaseModel):
    id: str  # e.g., "adr-001"
    title: str
    context: str  # Why this decision is needed
    decision: str  # What we decided
    consequences: str  # Implications and tradeoffs
    alternatives: list[str] = Field(default_factory=list)  # Options considered
    evidence_links: list[SourceCitation] = Field(default_factory=list)
    status: Literal["proposed", "accepted", "superseded"] = "proposed"
    created_at: str
    updated_at: str
```

#### 4.2 Create `aaa_create_adr` Tool
**Priority:** P0

```python
async def aaa_create_adr(
    title: str,
    context: str,
    decision: str,
    consequences: str,
    alternatives: list[str] | None = None,
    evidence_citations: list[dict] | None = None,
) -> str:
    """
    Create structured ADR and persist to ProjectState.
    Returns ADR ID.
    """
```

**Behavior:**
- Validate all required fields present
- Generate ADR ID (adr-NNN, auto-increment)
- Append to `ProjectState.adrs[]`
- Return ADR ID

**Files to create:**
- `backend/app/agents_system/tools/aaa_adr_tool.py`

#### 4.3 Update System Prompt: Propose ADR Template
**Priority:** P1

Add instruction:
> When user requests an ADR but has not provided a template:
> 1. Propose a structured ADR format (context/decision/consequences/alternatives)
> 2. Ask user to confirm or suggest modifications
> 3. Only after agreement, create the ADR using the tool

**Acceptance Criteria:**
- ✅ After ADR creation, `ProjectState.adrs[]` contains structured ADR passing schema validation
- ✅ ADR includes evidence citations linking to WAF/KB sources when applicable
- ✅ If user requests ADR without template, agent **proposes format first**

---

## 5. WAF Checklist: Highlight Missing Items, Propose Remediation

### Current Gap
- Validation tool has guard against empty payload, but no "what's missing?" analysis
- No proactive "you haven't addressed Security pillar X" feedback

### Actions
#### 5.1 Add Checklist Completeness Analysis
**Priority:** P1

**After validation turn, agent must:**
1. Query current `wafChecklist.items[]`
2. Identify missing pillars or low-coverage areas
3. Proactively suggest: "I noticed you haven't addressed Reliability → Disaster Recovery. Would you like me to propose mitigations?"

**Files to modify:**
- `backend/app/agents_system/langgraph/nodes/research.py`: add post-validation reflection step
- System prompt: add "checklist completeness check" instruction

#### 5.2 Enhance Validation Tool Error Messages
**Priority:** P2

When validation payload is rejected (empty or missing fields):
```python
raise ValueError(
    "Validation payload incomplete. "
    "Ensure wafEvaluations includes at least 1 item with evidence. "
    "Currently missing: [list specific required fields]"
)
```

**Acceptance Criteria:**
- ✅ E2E validation turn results in `wafChecklist.items.length >= 1`
- ✅ If checklist is sparse, agent **proactively suggests** missing areas
- ✅ Validation tool error messages are **actionable**

---

## 6. KB/RAG Integration: Test WAF ReAct Loop

### Current Gap
- E2E asserts "KB call count > 0" but doesn't validate **quality** of KB usage
- No explicit test that agent queries WAF correctly during ReAct loop

### Actions
#### 6.1 Add KB Query Quality Assertions
**Priority:** P0

**New E2E assertions:**
```python
# After validation turn:
assert_kb_queries_include_waf_pillar(transcript, required_pillars=["Security", "Reliability"])
assert_waf_checklist_items_cite_kb_sources(state, min_citations=1)
```

**Implementation:**
- Parse `transcript.jsonl` for KB tool calls
- Verify query strings mention WAF pillars
- Verify returned `wafEvaluations[].evidence` includes KB source citations

#### 6.2 Add "KB Not Queried" Remediation
**Priority:** P1

If agent produces validation results **without** querying KB:
- E2E fails with actionable message: "Validation stage did not query WAF KB. Check stage routing or prompt instructions."

**Files to modify:**
- `scripts/e2e/aaa_e2e_runner.py`: add KB query validation

**Acceptance Criteria:**
- ✅ E2E validation turn **always** queries WAF KB (ReAct loop proven)
- ✅ WAF checklist items include KB-sourced evidence
- ✅ If KB query fails or is skipped, E2E fails with clear diagnostic

---

## 7. Agent Behavior: Force of Proposition

### Current Gap
- Agent is **reactive**: responds to direct questions but doesn't proactively guide
- No evaluation of agent's "advisory quality" (feedback, corrections, suggestions)

### Actions
#### 7.1 Update System Prompt: Proactive Advisor
**Priority:** P0

**New instructions:**
> You are a proactive Azure Architect advisor. Your responsibilities:
> 1. **Propose** solutions before being asked (e.g., "Based on your requirements, I recommend...")
> 2. **Correct** misunderstandings or risky decisions ("That approach has X drawback; consider Y instead")
> 3. **Suggest** next steps ("Now that we have ADRs, shall we validate against WAF?")
> 4. **Question** ambiguous requirements ("You mentioned 'high availability' — do you mean 99.9% or 99.99%?")
> 5. **Provide context** for decisions (link to WAF guidance, trade-offs, cost implications)

**Files to modify:**
- `backend/app/agents_system/langgraph/nodes/research.py`: update stage-specific prompts
- `backend/app/agents_system/langgraph/prompts.py`: create shared "advisor persona" instructions

#### 7.2 Create "Agent Advisory Quality" E2E Evaluation
**Priority:** P1

**New E2E metric: `advisoryScore`**

After each turn, evaluate agent response for:
- **Proactivity**: Did agent suggest next steps unprompted? (0-2 points)
- **Correction**: Did agent catch/correct user mistakes or risky assumptions? (0-2 points)
- **Evidence**: Did agent cite sources (WAF/KB) to support recommendations? (0-2 points)
- **Clarity**: Did agent ask clarifying questions when requirements were vague? (0-2 points)

**Implementation:**
```python
# scripts/e2e/aaa_e2e_runner.py
def _evaluate_advisory_quality(step: dict) -> dict:
    """Score agent response on proactivity, correction, evidence, clarity."""
    answer = step["answer"]
    score = {
        "proactivity": _score_proactivity(answer),
        "correction": _score_correction(answer),
        "evidence": _score_evidence(answer, step.get("kbCallCount", 0)),
        "clarity": _score_clarity(answer),
        "total": 0,
    }
    score["total"] = sum(score.values()) - score["total"]  # exclude total from sum
    return score
```

**Scoring heuristics (simple keyword/pattern matching):**
- Proactivity: presence of "I recommend", "shall we", "next step", "would you like me to"
- Correction: presence of "however", "instead", "consider", "risk", "drawback"
- Evidence: KB sources cited in answer
- Clarity: presence of "clarify", "do you mean", "which option", "?"

**Acceptance Criteria:**
- ✅ Each E2E step includes `advisoryScore` in report
- ✅ Scenario passes only if average `advisoryScore.total >= 4` (out of 8)
- ✅ Low-scoring responses are flagged for prompt improvement

#### 7.3 Add "Agent Behavior" Test Scenarios
**Priority:** P2

New scenarios targeting advisory behavior:
- **Scenario: Ambiguous Requirements**
  - User: "I need high availability"
  - Expected: Agent asks for SLA target (99.9%? 99.99%?)
- **Scenario: Risky Decision**
  - User: "Let's put everything in a single region"
  - Expected: Agent warns about disaster recovery implications
- **Scenario: Missing ADR**
  - User proceeds to validation without ADRs
  - Expected: Agent suggests creating ADRs first

**Acceptance Criteria:**
- ✅ Agent proactively **questions** ambiguous requirements
- ✅ Agent **corrects** risky architectural decisions
- ✅ Agent **suggests** missing steps (ADR, validation, diagrams)

---

## 8. Spec Alignment + Prompt Improvements

### Current Gap
- System prompts don't enforce "call persistence tools"
- Agent can produce nice prose without persisting artifacts

### Actions
#### 8.1 Add "Self-Check" Instruction
**Priority:** P0

**New prompt section:**
> Before replying to user:
> 1. Review your tool calls this turn
> 2. If user requested ADR/diagram/validation, verify you called the corresponding persistence tool
> 3. If tool call is missing, call it now before replying
> 4. If state update failed, retry or explain the error to the user

**Files to modify:**
- `backend/app/agents_system/langgraph/nodes/research.py`: add pre-reply self-check step

#### 8.2 Update Stage Routing Keywords
**Priority:** P1

Current issues:
- "record" keyword too generic (routed ADR stage instead of validate stage)

**Actions:**
- Review all stage routing keywords: `backend/app/agents_system/langgraph/nodes/stage_routing.py`
- Add priority/specificity scoring (validate keywords > ADR keywords)
- Add tests for routing edge cases

**Acceptance Criteria:**
- ✅ Stage routing is deterministic and matches user intent
- ✅ Validation turns route to validate stage (not ADR stage)

---

## 9. Deliverables

### Immediate (Next 2 Sprints)
1. **DB Persistence Layer**
   - DB path logging + isolation
   - E2E DB assertions (project/state/checklist/ADRs)
   - Retrieve-modify-retrieve test
2. **Diagram Persistence (Option A)**
   - `aaa_create_diagram_set` tool
   - ProjectState diagram references
   - E2E validation
3. **ADR Tool + Template**
   - `aaa_create_adr` tool
   - ADR schema enforcement
   - Propose-template behavior

### Short-Term (Next Sprint)
4. **Advisory Quality Evaluation**
   - Agent advisory score metric
   - Proactive behavior scenarios
   - System prompt updates

### Medium-Term (Next 2 Sprints)
5. **KB/RAG Quality Tests**
   - WAF ReAct loop validation
   - KB query quality assertions
6. **Checklist Completeness Analysis**
   - Missing pillar detection
   - Proactive remediation suggestions

### Long-Term (Backlog)
7. **Spec Alignment Audit**
   - Reconcile E2E spec vs implementation
   - Stage routing keyword review
8. **Comprehensive Test Suite**
   - Unit tests for retrieve-modify-retrieve
   - Integration tests for diagram + ADR persistence

---

## Acceptance Criteria (Overall)

### Must-Have (Sprint Exit Criteria)
- ✅ E2E run produces non-empty `projects.db` with project + state rows
- ✅ ADRs, diagrams, WAF checklist are **persisted and retrievable**
- ✅ Agent calls persistence tools (not just produces text)
- ✅ Agent advisory score averages >= 4/8 per scenario

### Should-Have
- ✅ E2E runs are DB-isolated (no cross-run pollution)
- ✅ KB queries during validation are proven (ReAct loop validated)
- ✅ Agent proactively suggests missing steps or corrects risky decisions

### Nice-to-Have
- ✅ Comprehensive logging shows persistence events
- ✅ Run reports include DB snapshots and advisory scores
- ✅ Agent proposes ADR template if none exists

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| In-process E2E still writes to wrong DB path | High | Add explicit env var override + logging |
| Diagram persistence breaks existing chat flow | Medium | Maintain backward compat: Mermaid in answer + DB persistence |
| Advisory score too subjective/noisy | Medium | Start with simple heuristics, refine based on data |
| CAF KB index still broken | Low | Document as "known issue", prioritize post-sprint |

---

## Next Steps (Immediate Actions)

1. **Add DB path logging** (`projects_database.py`, `diagram/database.py`)
2. **Add DB isolation** to E2E runner (`--data-root` flag)
3. **Create diagram persistence tool** (`aaa_diagram_tool.py`)
4. **Add DB assertions** to E2E runner (`_assert_db_persistence()`)
5. **Update system prompt** with proactive advisor instructions

**Assignee:** Agent (autonomous implementation)  
**Timeline:** 2-3 hours for P0 items  
**Success Metric:** Next E2E run produces populated DBs + advisory score report
