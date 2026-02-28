# Frontend Reference

## Structure

- `frontend/src/app/` - layout and route wiring.
- `frontend/src/features/` - feature-specific pages, hooks, context.
- `frontend/src/components/` - shared UI components (including KB, ingestion, agent, diagrams).
- `frontend/src/services/` - API client wrappers.
- `frontend/src/hooks/` - shared hooks (errors, toasts, KB status).
- `frontend/src/types/` - shared types for API responses.
- `frontend/src/utils/` - helper config and utilities.

## Entry points

- App root: `frontend/src/App.tsx`
- Routes: `frontend/src/app/routes.tsx`
- Layout: `frontend/src/app/Layout.tsx`

## Routes

- `/projects` - project list.
- `/projects/:projectId` - project workspace (tabs).
- `/kb` - knowledge base query workspace.
- `/kb-management` - KB creation and ingestion workflow.
- `/agent-chat` - agent chat UI.

Route navigation is defined in `frontend/src/components/common/Navigation.tsx`.

## Project workspace

- Pages: `frontend/src/features/projects/pages/UnifiedProjectPage.tsx` (main workspace).
  - Tab factories and route helpers: `pages/workspaceHelpers.tsx`.
  - Workspace hooks (dirty indicator, quick-open, route intent): `pages/workspaceHooks.ts`.
- Context (split into focused providers, composed in `ProjectProvider.tsx`):
  - `projectMetaContext` — project metadata (name, id).
  - `projectInputContext` — input/workflow state (text requirements, file uploads, analysis).
  - `projectStateContext` — project state (requirements, ADRs, diagrams, etc.).
  - `projectChatContext` — chat messages and send actions.
- State + orchestration: `frontend/src/features/projects/hooks/useProjectDetails.ts`.

### Workspace components

- `CenterWorkspaceTabs.tsx` — Tab container + content rendering.
- `TabStrip.tsx` — Tab strip UI with drag-reorder, pin, close.
- `ChatPanel.tsx` — Chat sidebar (composed from `ChatListHeader`, `ChatListFooter`, `ChatInputForm`, `ChatMessagesList`).
- `ArtifactViews.tsx` — Artifact renderer dispatch (delegates to viewers in `ArtifactViewRenderers.tsx`).
- `WafChecklistView.tsx` — WAF checklist tab.

## Knowledge base UI

- `frontend/src/components/ingestion/` handles KB creation, ingestion progress, and status display.
- `frontend/src/components/kb/` handles KB query, results, and status checking.
- Hooks: `frontend/src/hooks/useKBHealth.ts`, `useKBList.ts`, `useIngestionJob.ts`.

## Agent chat UI

- `frontend/src/components/agent/` renders agent chat and project state panels.

## Diagram UI

- `frontend/src/components/diagrams/DiagramSetViewer.tsx` fetches a diagram set and renders diagram cards.
- `frontend/src/components/diagrams/MermaidRenderer.tsx` renders Mermaid source into SVG.

## API layer

`frontend/src/services/apiService.ts` contains the primary API client used by the UI:
- `projectApi`, `chatApi`, `stateApi`, `kbApi`, `proposalApi`, `diagramApi`.

The base URL is `BACKEND_URL` from `.env` (default http://localhost:8000).

## Error handling and toasts

- `frontend/src/hooks/useErrorHandler.ts` standardizes error handling.
- `frontend/src/hooks/useToast.ts` provides toast notifications.

## Adding a new route or feature

1. Add a page or component under `frontend/src/features/` or `frontend/src/components/`.
2. Wire the route in `frontend/src/app/routes.tsx` and add a nav item in `frontend/src/components/common/Navigation.tsx`.
3. Add API calls in `frontend/src/services/apiService.ts`.
4. Add or update shared types in `frontend/src/types/`.
5. Use `useErrorHandler` or `useToast` for consistent error UX.

## Styling

- Tailwind CSS via `frontend/src/index.css`.
