# IDE-Style Center Workspace (VSCode-like Tabs)

## Goal
Make the center pane behave like an IDE (VSCode reference). The architect must open multiple inputs and artifacts as tabs, close/reorder/pin them, and see the correct viewer/editor for each type. The center pane is the primary working surface.

This is a UX behavior spec. It does not require backend changes.

## Current Data Sources (from codebase)
Inputs
- Text requirements: `Project.textRequirements` (editable) via `projectApi.saveTextRequirements`
- Reference documents: `ProjectState.referenceDocuments` (`ReferenceDocument`)

Artifacts (from `ProjectState`)
- Requirements: `requirements` (`Requirement[]`)
- Assumptions: `assumptions` (`Assumption[]`)
- Clarification questions: `clarificationQuestions` (`ClarificationQuestion[]`)
- ADRs: `adrs` (`AdrArtifact[]`)
- Diagrams: `diagrams` (`DiagramData[]`, Mermaid)
- Findings: `findings` (`FindingArtifact[]`)
- WAF checklist: `wafChecklist` (`WafChecklist`)
- IaC: `iacArtifacts` (`IacArtifact[]`)
- Costs: `costEstimates` (`CostEstimate[]`)
- Traceability: `traceabilityLinks`, `traceabilityIssues`
- Candidate architectures: `candidateArchitectures`
- Iteration events: `iterationEvents`
- MCP queries: `mcpQueries`

## Tab Model
Each open tab represents one of:
- Input overview (inputs list + text requirements editor)
- Single input document
- Artifact collection view (requirements list, ADR library, diagram gallery, etc.)
- Artifact detail (future: ADR editor, diagram editor, etc.)

Minimum tab fields
- id (unique, stable)
- title (string)
- kind (enum)
- group (input | artifact)
- pinned (boolean)
- dirty (boolean, unsaved changes)
- icon (by type)

## Required IDE Behaviors

### Open / Focus
- Click on an item in the left tree opens it as a tab.
- If tab already open, it becomes active (no duplicates).
- Opening a tab does not close existing tabs.

### Close
- Each tab has a close "x".
- Middle click closes (optional).
- Cmd/Ctrl+W closes active tab.
- “Close other tabs” context action (optional).

### Pin
- Pinned tabs sit leftmost and do not auto-close when opening new tabs.
- Pinned tabs are “fixed width” and show only icon + short title (VSCode style).

### Reorder
- Tabs can be drag-reordered.
- Reordering persists within session.

### Dirty State
- Editable tabs show a dot or “•” when unsaved.
- Close action on dirty tab prompts to save/discard.

### Keyboard Navigation
- Cmd/Ctrl+1..9 to focus tab index.
- Ctrl+Tab / Ctrl+Shift+Tab cycles tabs.

### Overflow
- Tabs overflow with horizontal scroll (like VSCode).
- Optionally show a “more tabs” dropdown for overflow.

## Viewer / Editor Mapping

### Inputs
1) Text requirements
   - Type: Text editor
   - Editable now
   - Save action triggers `projectApi.saveTextRequirements`

2) Reference documents (pdf/doc/xls/txt)
   - Type: external or embedded viewer (initially external open)
   - Read-only
   - Tab title = document title
   - Icon by file type (PDF, Excel, Word, TXT)

### Artifacts
3) Requirements
   - Type: list view (read-only for now)
   - Future: inline edit

4) Assumptions / Questions
   - Type: list view (read-only for now)

5) ADRs
   - Type: library view (read-only for now)
   - Future: ADR editor (dirty state, versioning)

6) Diagrams
   - Type: gallery + viewer (Mermaid)
   - Read-only now; future edit with preview

7) WAF checklist
   - Type: checklist view (read-only now)

8) IaC artifacts
   - Type: code viewer (read-only now)

9) Costs
   - Type: table + charts (read-only now)

10) Findings
   - Type: list view (read-only now)

11) Traceability
   - Type: list of links/issues (read-only now)

12) Candidate architectures, iteration events, MCP queries
   - Type: list view (read-only now)

## Visual Language (VSCode-like)
- Tabs are flat, same height, with active underline.
- Active tab has a white background; inactive tabs are grey.
- Pin indicator on the left of title.
- Type badge/dot indicating input vs artifact.
- Close button appears on hover or active tab.

## Center Pane Layout
- Tab strip at top (VSCode-like)
- Viewer/editor below, full height
- Scrollbar appears only when center panel is focused (current `panel-scroll` behavior)

## Tab Types (current code should align)
Current enum: `frontend/src/features/projects/components/unified/workspace/types.ts`
```
input-overview
input-document
artifact-requirements
artifact-assumptions
artifact-questions
artifact-adrs
artifact-diagrams
artifact-findings
artifact-costs
artifact-iac
artifact-waf
artifact-traceability
artifact-candidates
artifact-iterations
artifact-mcp
```

## Implementation Notes (Front-end)
Suggested structure:
- `CenterWorkspaceTabs` renders tab strip + current view
- Tab registry for mapping kind -> renderer
- Dedicated “tab controller” hook for open/close/pin/dirty/drag

Planned additions:
- Drag reorder (e.g., `@dnd-kit`)
- Pin + dirty state UI
- Context menu on tab

## Non-Goals (for now)
- No backend changes.
- No real-time collaboration.
- No in-tab editing except text requirements.

