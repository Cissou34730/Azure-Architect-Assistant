# Frontend Reference

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

## Project workspace

Tabs are registered in `frontend/src/features/projects/tabs/`:
- documents
- chat
- state
- proposal
- diagrams (diagram set viewer)

Note: the diagrams tab currently uses a hardcoded diagram set id in `frontend/src/features/projects/tabs/definitions/diagrams.tsx`.

## Knowledge base UI

- `frontend/src/components/ingestion/` handles KB creation, ingestion progress, and status display.
- `frontend/src/components/kb/` handles KB query, results, and status checking.

## Agent chat UI

- `frontend/src/components/agent/` renders agent chat and project state panels.

## API layer

`frontend/src/services/apiService.ts` contains the primary API client used by the UI.
- `projectApi`, `chatApi`, `stateApi`, `kbApi`, `proposalApi`, `diagramApi`.

The base URL is `BACKEND_URL` from `.env` (default http://localhost:8000).

## State and hooks

- `frontend/src/hooks/` contains shared hooks for KB status, ingestion jobs, and error handling.
- Project-specific logic is in `frontend/src/features/projects/`.

## Styling

- Tailwind CSS via `frontend/src/index.css`.
