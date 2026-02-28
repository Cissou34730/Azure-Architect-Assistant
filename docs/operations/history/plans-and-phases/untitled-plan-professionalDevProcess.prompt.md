## Plan: Professionalize Repo Governance, Agent Docs, and Traceability

Professionalize delivery with a strict dual-doc-lane model, enforceable governance/quality gates, and an Issue-first workflow. This plan is designed for full execution by agents with explicit handoffs and maintainer approval checkpoints.

**Execution Sequence and Handoffs**
1. Stage A — Governance Baseline (Governance subagent)
   - Execute:
     - Inventory all policy/instruction sources.
     - Detect contradictions and overlaps.
     - Draft Source-of-Truth Matrix (rule, owner, enforcement, precedence).
   - Handoff package to maintainer:
     - Contradiction report.
     - Proposed precedence map.
     - Draft matrix.
   - Maintainer decision gate:
     - Approve final precedence chain.
     - Approve canonical owner per policy area.
   - Exit criteria:
     - Approved governance baseline document exists and unresolved conflicts are explicitly tracked.

2. Stage B — Dual Docs Lane Contract (Docs-lane architect subagent)
   - Execute:
     - Draft lane contracts for agent lane and human lane.
     - Draft lane-specific templates + DoD checklists.
     - Generate reciprocal-link mapping rules and anti-duplication policy.
   - Handoff package to maintainer:
     - Lane contract draft.
     - Template/checklist set.
     - Link policy + examples.
   - Maintainer decision gate:
     - Approve lane boundaries and required sections.
   - Exit criteria:
     - Canonical lane contract is accepted and referenced from docs index.

3. Stage C — Instruction/Agent/Skill Normalization (Instruction-skill curator subagent)
   - Execute:
     - Fix missing/broken instruction references.
     - Build active asset registry for agents/prompts/skills (owner, status, review cadence).
     - Normalize skill descriptions to standard schema.
   - Handoff package to maintainer:
     - Registry draft.
     - Normalization diff summary.
     - Deprecation candidates list.
   - Maintainer decision gate:
     - Approve active/deprecated status assignments.
   - Exit criteria:
     - Registry published and all active skills/agents satisfy schema completeness.

4. Stage D — CI and Quality Gates (CI-workflow subagent)
   - Execute:
     - Standardize backend command path to uv in scripts/tasks/docs.
     - Implement GitHub Actions checks (frontend lint/type, backend lint/type/test, docs integrity/lane checks).
     - Configure phased TypeScript no-any enforcement path by domain.
     - Align Python typing to Pyright canonical authority and scoped mypy role.
   - Handoff package to maintainer:
     - CI workflow summary and check matrix.
     - Local command matrix.
     - Open strictness backlog items.
   - Maintainer decision gate:
     - Approve which checks are advisory vs blocking.
   - Exit criteria:
     - CI checks run successfully on pilot branch and local commands match CI behavior.

5. Stage E — Issue-first Traceability System (Traceability runbook writer subagent)
   - Execute:
     - Create issue templates (bug, feature, tech debt, docs/policy change).
     - Define branch/commit/changelog linkage rules.
     - Define exception path via decision record when no issue exists.
   - Handoff package to maintainer:
     - Traceability policy table.
     - Template set.
     - Exception approval flow.
   - Maintainer decision gate:
     - Approve mandatory Issue threshold for non-trivial changes.
   - Exit criteria:
     - Traceability rules are documented and templates are published.

6. Stage F — Mandatory Workflow Runbook Publication (Traceability runbook writer subagent + Docs-lane architect subagent)
   - Execute:
     - Produce one canonical operations runbook that defines:
       - when Issue is mandatory,
       - when PR is recommended vs required,
       - how commits, branches, changelog, docs, and release notes must link,
       - exception handling and approval authority,
       - compliant and non-compliant examples.
     - Register runbook in docs TOC and governance references.
   - Handoff package to maintainer:
     - Final runbook draft + cross-reference map.
   - Maintainer decision gate:
     - Approve runbook as single source of workflow truth.
   - Exit criteria:
     - Runbook is discoverable from docs root and referenced by governance docs.

7. Stage G — Pilot Verification and Rollout Readiness (Verification subagent)
   - Execute:
     - Run one full pilot change through Issue-linked flow.
     - Validate lane compliance, traceability chain, and CI integrity.
     - Produce compliance report with gaps and corrective tasks.
   - Handoff package to maintainer:
     - Pilot evidence set (links and checks).
     - Gap list with remediation recommendations.
   - Maintainer decision gate:
     - Go/no-go for broad adoption.
   - Exit criteria:
     - Pilot passes required checks and remaining gaps are tracked with owners.

**Steps (Implementation Content by Stage)**
1. Governance normalization
   - Define precedence chain and publish Source-of-Truth Matrix.
   - Resolve TypeScript and Python policy contradictions.

2. Strict dual-lane docs model
   - Formalize agent lane vs human lane contracts.
   - Add lane templates, DoD checklists, reciprocal links, anti-duplication policy.

3. Instruction/agent/skill quality baseline
   - Normalize instruction roles and repair references.
   - Build active registry and standardize skill description schema.

4. CI and quality gate implementation
   - Standardize uv usage.
   - Implement GitHub Actions checks.
   - Phase TypeScript no-any by domain.

5. Issue-first traceability and templates
   - Add Issue templates and decision-record exception path.
   - Define commit/branch/changelog linkage requirements.

6. Mandatory workflow runbook
   - Publish canonical runbook in operations docs and register from docs index.

7. Verification and onboarding
   - Execute pilot and publish contributor/maintainer playbooks.

**Subagent Delegation Matrix**
1. Governance subagent
   - Delegable: policy inventory, conflict detection, matrix drafting.
   - Non-delegable: authority and precedence approval.
2. Docs-lane architect subagent
   - Delegable: lane contracts, templates, DoD checklists, link policy.
   - Non-delegable: final governance wording.
3. Instruction-skill curator subagent
   - Delegable: skill normalization, asset registry, overlap detection.
   - Non-delegable: deprecation/archival approval.
4. CI-workflow subagent
   - Delegable: workflow files, command alignment, docs checks.
   - Non-delegable: protection policy and required-check governance.
5. Traceability runbook writer subagent
   - Delegable: complete runbook draft and examples.
   - Non-delegable: non-trivial threshold and exception authority.
6. Verification subagent
   - Delegable: pilot execution and compliance evidence.
   - Non-delegable: rollout go/no-go decision.

**Required Deliverables**
1. Source-of-Truth Matrix.
2. Dual-lane docs contract + templates/checklists.
3. Active asset registry for agents/prompts/skills.
4. CI checks for code and docs-lane integrity.
5. Canonical Issue/PR/traceability workflow runbook.
6. Contributor and maintainer playbooks.
7. Pilot compliance report.

**Relevant files**
- `/.specify/memory/constitution.md`
- `/.github/copilot-instructions.md`
- `/.github/copilot-typescript-instruction.md`
- `/.github/python-instruction.md`
- `/.github/terraform-instruction.md`
- `/eslint.config.js`
- `/pyrightconfig.json`
- `/mypy.ini`
- `/pyproject.toml`
- `/.vscode/tasks.json`
- `/package.json`
- `/start-backend.ps1`
- `/docs/README.md`
- `/docs/agents/README.md`
- `/docs/agents/AGENT_DOC_TEMPLATE.md`
- `/docs/operations/DOCUMENTATION_GOVERNANCE.md`
- `/docs/operations/DOC_MIGRATION_INDEX.md`
- `/.github/skills/*`
- `/.github/agents/*`
- `/.github/prompts/*`
- `/.github/workflows/*`
- `/.github/ISSUE_TEMPLATE/*`
- `/.github/PULL_REQUEST_TEMPLATE.md`
- `/CHANGELOG.md`

**Verification**
1. Governance integrity: each rule has one owner and one enforcement mechanism.
2. Docs-lane integrity: paired agent/human docs exist with reciprocal links and no long-form rationale in agent lane.
3. Tooling integrity: uv path is consistent across scripts/tasks/docs.
4. CI integrity: GitHub Actions checks pass on pilot branch.
5. Traceability integrity: pilot change is fully linked (Issue → branch/commits → docs/changelog → optional PR).
6. Runbook integrity: maintainers can execute workflow with no tribal knowledge.

**Decisions integrated**
- CI platform: GitHub Actions only.
- Python type authority: Pyright canonical.
- TypeScript strictness: phased no-any rollout.
- Process strictness: no mandatory PR at this stage.
- Backend execution: mandatory uv.

**Scope boundaries**
- Included: governance alignment, strict dual docs lanes, subagent-delegable execution model, issue-first traceability, mandatory workflow runbook.
- Excluded: forced PR mandate now, broad architecture rewrites, new framework introduction.