# Azure Architecture Assistant

Azure Architecture Assistant is a full-stack app that helps capture project requirements, query Azure knowledge bases, and generate architecture guidance and diagrams.

## Highlights

- Project workspace for requirements, document analysis, chat, and proposal generation.
- Knowledge base management with ingestion, status tracking, and multi-KB queries.
- Agent chat that pulls Microsoft documentation via MCP.
- Diagram generation for functional flow, C4 context, and C4 container views.

## Quick start

```powershell
# 1) Configure environment
Copy-Item .env.example .env
# Edit .env and set OPENAI_API_KEY

# 2) Install dependencies
npm run installAll

# 3) Run services
npm run backend
npm run frontend
```

Frontend: http://localhost:5173
Backend: http://localhost:8000

## Reference docs

- `docs/PROJECT_OVERVIEW.md`
- `docs/SYSTEM_ARCHITECTURE.md`
- `docs/DEVELOPMENT_GUIDE.md`
- `docs/BACKEND_REFERENCE.md`
- `docs/FRONTEND_REFERENCE.md`

## Notes

- Runtime data lives in `data/` (SQLite DBs and KB indices).
- If you are adding features, start with `docs/SYSTEM_ARCHITECTURE.md`, then the backend and frontend references.
- For API details and routes, see `docs/BACKEND_REFERENCE.md`.
