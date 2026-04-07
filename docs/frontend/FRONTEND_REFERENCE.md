# Frontend Reference

## Structure

- `frontend/src/app/` - layout, route wiring, workspace registry, and legacy route redirects.
- `frontend/src/features/` - canonical feature ownership for pages, hooks, context, types, and API clients.
- `frontend/src/shared/` - canonical shared UI, hooks, HTTP helpers, and config.
- `frontend/src/components/` - legacy shared UI still being normalized into `shared/` and feature folders.
- `frontend/src/hooks/`, `frontend/src/services/`, `frontend/src/types/` - removed as compatibility layers; feature code now imports canonical modules directly from `features/*` or `shared/*`.

## Entry points

- App root: `frontend/src/App.tsx`
- Routes: `frontend/src/app/routes.tsx`
- Layout: `frontend/src/app/Layout.tsx`

## Routes

- `/project` - project list.
- `/project/:projectId` - project workspace.
- `/kb` - knowledge base query workspace.
- `/kb-management` - KB creation and ingestion workflow.
- `/projects` and `/projects/:projectId` redirect to the canonical `/project` routes.

Top-level route modules are registered in `frontend/src/app/workspaceRegistry.ts`, and navigation is rendered from that registry in `frontend/src/shared/ui/Navigation.tsx`.

## Project workspace

- Pages: `frontend/src/features/projects/pages/UnifiedProjectPage.tsx` (main workspace).
  - Static shell sections, tab catalog, default tab, left-tree entries, and route-intent aliases: `workspace.manifest.ts`.
  - Workspace hooks (dirty indicator, quick-open, route intent): `pages/workspaceHooks.ts`.
- Context (split into focused providers, composed in `ProjectProvider.tsx`):
  - `projectMetaContext` — project metadata (name, id).
  - `projectInputContext` — input/workflow state (text requirements, file uploads, analysis).
  - `projectStateContext` — project state (requirements, ADRs, diagrams, etc.).
  - `projectChatContext` — chat messages and send actions.
- State + orchestration: `frontend/src/features/projects/hooks/useProjectDetails.ts`.

### Workspace components

- `UnifiedProjectWorkspace.tsx` — registry-driven shell composition for the header, left tree, center tabs, and right chat panel.
- `CenterWorkspaceTabs.tsx` — tab container + content rendering.
- `TabStrip.tsx` — Tab strip UI with drag-reorder, pin, close.
- `ChatPanel.tsx` — Chat sidebar (composed from `ChatListHeader`, `ChatListFooter`, `ChatInputForm`, `ChatMessagesList`).
- `workspaceTabRegistry.tsx` — static tab-content registry keyed from the workspace manifest; `WorkspaceTabContent.tsx` only special-cases dynamic document tabs.
- `WafChecklistView.tsx` — WAF checklist tab.

## Knowledge base UI

- Canonical UI lives in `frontend/src/features/knowledge/components/` and `frontend/src/features/ingestion/components/`.
- Canonical API clients and hooks live in `frontend/src/features/knowledge/{api,hooks}/` and `frontend/src/features/ingestion/{api,hooks}/`.
- Knowledge and ingestion consumers now import their canonical hooks, types, and API clients directly from `frontend/src/features/{knowledge,ingestion}/`.

## Agent chat UI

- Canonical UI, hooks, and API clients live under `frontend/src/features/agent/{components,hooks,api}/`.
- Agent consumers now import canonical hooks, API clients, and types directly from `frontend/src/features/agent/`.

## Diagram UI

- Canonical UI, hooks, and types live under `frontend/src/features/diagrams/{components,hooks,types}/`.
- Diagram types are imported directly from `frontend/src/features/diagrams/types/`.

## API layer

- Canonical API clients live under feature folders, for example:
  - `frontend/src/features/projects/api/*.ts`
  - `frontend/src/features/knowledge/api/*.ts`
  - `frontend/src/features/ingestion/api/*.ts`
  - `frontend/src/features/settings/api/*.ts`
- Root service compatibility pointers have been removed; feature modules import their API clients directly from feature-local `api/` folders.
- Project workspace state reads now resolve through `frontend/src/features/projects/api/stateService.ts` and `frontend/src/features/agent/api/agentService.ts`, both of which call the canonical `/api/projects/{projectId}/workspace` endpoint and consume its `projectState` payload.

The base URL is `BACKEND_URL` from `.env` (default http://localhost:8000).

## Error handling and toasts

- `frontend/src/shared/hooks/useErrorHandler.ts` standardizes error handling.
- `frontend/src/shared/hooks/useToast.ts` provides toast notifications.

## Adding a new route or feature

1. Add the feature surface under `frontend/src/features/<feature>/`.
2. Register route-backed workspaces in `frontend/src/app/workspaceRegistry.ts` and expose navigation through the manifest registry.
3. Add feature API clients under `frontend/src/features/<feature>/api/`.
4. Do not reintroduce root `frontend/src/{hooks,services,types}` compatibility files; import canonical feature-local or shared modules directly.
5. Use shared hooks from `frontend/src/shared/hooks/` for consistent error and toast UX.

## Compatibility note

- The former root shim files under `frontend/src/{hooks,services,types}` have been removed. New imports should target `features/*` or `shared/*` directly.
- `frontend/src/components/` only remains as an empty compatibility shell while the old feature folders disappear from working trees; canonical UI code lives in `features/*` and `shared/ui`.
- ESLint now hard-fails any reintroduction of root `services/*`, `hooks/*`, `types/*`, `config/*`, or `utils/*` compatibility imports from feature modules, and it keeps a dedicated failure message for the removed root `frontend/src/types/api.ts` shim inside the cleaned projects surface, knowledge UI components, and project hook tests.

## Styling

- Tailwind CSS via `frontend/src/index.css`.
