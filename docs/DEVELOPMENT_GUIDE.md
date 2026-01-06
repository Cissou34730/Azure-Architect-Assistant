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

2. Install dependencies:

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
