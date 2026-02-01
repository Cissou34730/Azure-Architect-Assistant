# IDE-Style UX Workflow for Architect Collaboration

## Purpose
Design a clear, architect-first UX that supports a small set of inputs (typically <10 docs), architect-initiated analysis generation, and high-quality artifacts (requirements, ADRs, diagrams, checklists).

This document focuses on UX and interaction patterns only. Backend logic is assumed to exist and work.

## Primary Users and Success Criteria
- Primary user: Solution/Cloud Architect.
- Chatbot behavior: Keep current implementation unchanged.
- Success criteria: Artifact quality, traceability to inputs, and smooth iterative refinement.

## End-to-End Workflow (Target Experience)
1. Architect creates a new project.
2. Architect adds inputs:
   - Uploads RFP documents (PDF, Excel, schemas, TXT, etc.).
   - Adds text clarifications and notes.
3. Architect triggers analysis generation (manual action, no real-time auto generation).
4. System creates a first view of artifacts (baseline outputs).
5. Architect continues using the chatbot as currently implemented to update artifacts.

## UX Model: Inputs vs Artifacts
Inputs are sources (documents + clarifications). Artifacts are outputs (requirements, ADRs, diagrams, checklists, etc.).
This distinction must be visible in the **middle pane tabs** via color/icon coding.

## Core Layout (IDE-Style Workspace)
- **Left pane:** stays as-is (only minimal wiring to open items in center tabs).
- **Center pane:** VSCode‑style tabbed workspace for all inputs and artifacts.
- **Right pane:** stays as-is (chatbot behavior unchanged).

## Navigation and Information Architecture
- Project workspace is the primary view (no distracting landing page).
- Center pane supports multiple open items in tabs.
- Left pane only needs minimal wiring to open items in center tabs.
- Right pane remains unchanged.

## Key Interactions
### Create Project
- “New Project” button in the project list view.
- Enter name + optional description.
- On creation, land directly in the IDE workspace.

### Manage Project (Placeholder UX)
- Project actions menu includes:
  - Add (create new project)
  - Remove (placeholder only, backend not yet implemented)
  - Export (placeholder only, backend not yet implemented)
- These actions are visible in the UI but can show “Coming soon” or disabled states.

### Add Inputs
- Upload documents and add clarification text.
- Inputs become openable items in the middle‑pane tabs.

### Generate First Artifact View
- Architect triggers generation via a clear button (e.g., “Generate Analysis”).
- No real-time auto generation.
- After generation, a baseline set of artifacts is created.
- Artifacts show “Generated from: <input>” to encourage review.
- At this stage, artifacts are read-only except for input text.
  - Updates continue through the existing chatbot flow.

### Chatbot Behavior
- Keep current behavior; no new collaboration or approval flows are introduced.

### Open Multiple Artifacts
- Any input or artifact opens as a center tab.
- Tabs support:
  - Unsaved indicator.
  - Pin to keep open.
  - Close all / close others.

## Clarity and Quality Guardrails
- **Middle pane tabs** must visually distinguish **Input** vs **Artifact** (icon + color).
- Requirements are treated as outputs.
- Artifact type list must match existing code definitions.
- Each artifact shows source inputs, last edited timestamp, and author (user or bot) when available.

## Empty and Loading States
- New project with no inputs:
  - Clear CTA: “Upload RFP docs or add a clarification.”
- Generating artifacts:
  - Inline progress indicator per artifact.

## UX Principles for This Product
1. Inputs are sources, artifacts are authored outputs.
2. The workspace should encourage iteration, not one-shot generation.
3. The chatbot is a supporting surface, not the primary workflow driver.
4. Traceability is mandatory for quality and trust.
5. Keep the tree concise; use search and “recent” sections when needed.

## Non-Goals
- No new backend features are required for this UX.
- No complex multi-user real-time collaboration in this phase.

## Frontend Analysis (Current State)
- The unified workspace is composed in `frontend/src/features/projects/pages/UnifiedProjectPage.tsx`.
- UI is modular and isolated under `frontend/src/features/projects/components/unified/*`.
- Backend access is already separated in `frontend/src/services/*` and hooked through contexts in `frontend/src/features/projects/context`.
- Left and right panes already exist and should remain unchanged.
- Header actions exist (Upload/Generate/ADR/Export) and are UI-only in `useUnifiedProjectPage` (currently `console.log`).

## Concrete Work Plan (UI-Only Changes)
1. **Center panel: VSCode‑style tabs**
   - Add `frontend/src/features/projects/components/unified/CenterWorkspaceTabs.tsx`.
   - Allow opening multiple items (inputs + artifacts).
   - Reuse existing viewers/editors:
     - Inputs: document viewer + text clarification editor.
     - Artifacts: reuse deliverables components (ADR library, diagrams, etc.) and requirements view.
   - Enforce read-only for artifacts (except input text).
2. **Left pane: minimal wiring only**
   - Clicking any input/artifact opens the corresponding tab in the middle pane.
   - No layout or visual changes.
3. **Right pane: no changes**
   - Keep current appearance and behavior.

## Scope Guardrails
- Only change the center pane tab system and minimal wiring from the left pane.
- No changes to the right pane.
- No changes to services, hooks, or backend API behavior.

## Middle Pane Spec (VSCode‑Style Tabs)
The middle pane is the primary workspace and must behave like an IDE (VSCode reference). The left pane only needs minimal changes to open items into tabs.

### Core Behaviors
- Open any input or artifact as a tab in the middle pane.
- If a tab is already open, focus it (no duplicates).
- Multiple tabs can remain open at once.
- Tabs can be closed individually (x button).
- Tabs can be reordered (drag).
- Tabs can be pinned (pinned tabs stay leftmost and do not auto-close).
- Tabs show dirty state (unsaved changes) with a dot.
- Keyboard support:
  - Cmd/Ctrl+W: close current tab
  - Ctrl+Tab / Ctrl+Shift+Tab: cycle tabs
  - Cmd/Ctrl+1..9: jump to tab index

### Visual Style (VSCode‑like)
- Flat tab strip with active underline.
- Active tab is white; inactive tabs are muted gray.
- Close icon on hover or active tab.
- Overflow with horizontal scroll; optional dropdown for overflow list.
- Input vs Artifact is indicated (dot/badge/icon).

### Tab Types (must support all inputs + artifacts)
Inputs:
- Text requirements (editable)
- Reference documents:
  - PDF, Office docs, TXT, images
  - Default: open in external viewer; later embed

Artifacts (read-only for now, editable later):
- Requirements list
- Assumptions list
- Clarification questions list
- ADRs (library; later ADR editor)
- Diagrams (Mermaid)
- Findings
- WAF checklist
- IaC artifacts (code viewer)
- Cost estimates
- Traceability links/issues
- Candidate architectures
- Iteration events
- MCP queries

### Rendering Rules (current phase)
- Text requirements: editable, save action persists.
- All artifacts: read-only (future editable).
- Diagrams: Mermaid renderer; no editing yet.
- Documents: open by URL (or embed if available).

### Minimal Left Pane Change
- Clicking any input/artifact opens a corresponding tab.
- No major redesign of the left pane required.
