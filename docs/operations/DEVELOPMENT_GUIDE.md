# Development Guide

## Prerequisites

- Python 3.10+ (project uses uv for dependency management).
- Node.js 18+ and npm.
- OpenAI API key (or Azure OpenAI equivalents).

## Environment setup

1. Copy `.env.example` to `.env` and set at least:
   - `OPENAI_API_KEY`
   - `OPENAI_MODEL` (optional)
   - `OPENAI_EMBEDDING_MODEL` (optional)

2. For OpenAI primary with Azure fallback routing (AI service layer):
   - `AI_LLM_PROVIDER=openai`
   - `AI_EMBEDDING_PROVIDER=openai`
   - `AI_FALLBACK_ENABLED=true`
   - `AI_FALLBACK_PROVIDER=azure`
   - `AI_FALLBACK_ON_TRANSIENT_ONLY=true`
   - `AI_OPENAI_API_KEY=...`
   - `AI_AZURE_OPENAI_ENDPOINT=...`
   - `AI_AZURE_OPENAI_API_KEY=...`
   - `AI_AZURE_OPENAI_API_VERSION=2024-02-15-preview`
   - `AI_AZURE_LLM_DEPLOYMENT=...`
   - `AI_AZURE_EMBEDDING_DEPLOYMENT=...`
   - Optional: `AI_AZURE_LLM_DEPLOYMENTS=deployment-a,deployment-b` for model-list metadata

See `docs/backend/AI_PROVIDER_ROUTING.md` for behavior details.

3. Install dependencies:

```powershell
# Python + frontend (recommended)
npm run installAll

# Or Python only
uv sync
```

## Running locally

```powershell
# Terminal 1 - backend
npm run backend

# Terminal 2 - frontend
npm run frontend
```

`npm run backend` now performs a port preflight before starting uvicorn. If port `8000` is already used by another process, the script exits immediately with the owning PID and command line instead of letting the app complete startup and then fail on bind.

Alternatively you can run the backend directly:

```powershell
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

Default ports:
- Backend: 8000
- Frontend: 5173

## Feature development checklist

1. Identify the backend module (projects, KB, ingestion, agent, diagrams).
2. Add or update the backend route + service.
3. Update `frontend/src/services/apiService.ts` and types.
4. Wire UI changes (pages, components, hooks).
5. Update docs if new endpoints or configs are added.

## Config changes

- New environment variables must be added to `backend/app/core/config.py` (extra env keys are forbidden).
- Update `.env.example` whenever you add a new env key.

## Useful scripts

- `npm run build` - frontend production build.
- `npm run lint` - frontend linting.
- `npm run kill` - stop backend processes (PowerShell).
- `start-backend.ps1` - starts the backend from the repository root even if invoked from another working directory, and refuses to start if the configured backend port is owned by a different process.

## Testing

```powershell
# Python tests
uv run pytest

# Type checking
uv run mypy backend

# Linting
uv run flake8 backend
```

## Local data reset (if needed)

- Delete `data/projects.db` to reset projects.
- Delete `data/ingestion.db` to reset ingestion jobs.
- Delete `data/diagrams.db` to reset diagram sets.
- Remove `data/knowledge_bases/<kb_id>/index/` to force re-ingestion.

## Common locations

- Backend entry point: `backend/app/main.py`
- Frontend entry point: `frontend/src/main.tsx`
- API base URL: `BACKEND_URL` in `.env` (defaults to http://localhost:8000)
