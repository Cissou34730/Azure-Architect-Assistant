# Quickstart: Azure Architect Assistant (AAA)

This quickstart describes the minimal workflow for running the AAA feature in the existing application.

## Prerequisites

- Python 3.10+ environment set up for `backend/`
- Node.js environment set up for `frontend/`
- `/docs/arch_mindmap.json` present

## Run Backend

- Start the backend using the repo’s existing script(s), for example `start-backend.ps1`, or run FastAPI directly as configured in your environment.
- Verify health: `GET /health` should return OK.

## Run Frontend

- Start the Vite dev server in `frontend/`.

## Minimal End-to-End Flow

1) Create a project
- `POST /api/projects` with `{ "name": "My Architecture" }`

2) Upload documents
- `POST /api/projects/{projectId}/documents` (multipart)

3) Analyze documents (generates initial ProjectState)
- `POST /api/projects/{projectId}/analyze-docs`

4) Generate candidate architecture proposal
- `GET /api/projects/{projectId}/architecture/proposal` (SSE)

5) Discussion + artifact generation (via Agent System)

Use the project-aware agent endpoint for iterative discussion and for generating/updating artifacts in ProjectState:

- `POST /api/agent/projects/{projectId}/chat` with `{ "message": "Generate a candidate Azure architecture with assumptions and citations" }`
- `GET /api/agent/projects/{projectId}/history` to retrieve the conversation

Examples of actions to drive through agent chat:

- Generate candidates + WAF baseline initialization
- Create/update ADRs
- Run validation and produce findings
- Generate IaC and cost estimate narratives (and persist outputs in ProjectState)

## Validation Checklist

- Mind map is loaded and coverage is tracked for 13 topics
- Each candidate/ADR/finding includes at least one source citation (reference document or MCP)
- No manual edits are overwritten (conflicts are surfaced)
