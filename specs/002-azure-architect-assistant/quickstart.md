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

- [ ] `/docs/arch_mindmap.json` loads at backend startup (missing/invalid fails fast)
- [ ] `POST /api/projects` creates a project
- [ ] `POST /api/projects/{projectId}/documents` uploads at least 1 document
- [ ] `POST /api/projects/{projectId}/analyze-docs` produces `ProjectState` with:
	- [ ] `ingestionStats` (attempted/parsed/failed + failures)
	- [ ] `requirements` populated (business/functional/nfr)
	- [ ] `clarificationQuestions` populated when ambiguity exists
	- [ ] initial diagram link stored (C4 L1)
- [ ] `POST /api/agent/projects/{projectId}/chat` can generate AAA artifacts and persist them via `AAA_STATE_UPDATE`:
	- [ ] `candidateArchitectures` + `assumptions`
	- [ ] `adrs` (with citations + requirement link)
	- [ ] `findings` + `wafChecklist` evaluations
	- [ ] `iacArtifacts` and `costEstimates` (when requested)
- [ ] Each candidate/ADR/finding has at least one source citation (reference doc or MCP)
- [ ] Mind map coverage exists for the 13 topics (`mindMapCoverage.topics`)
- [ ] No manual edits are overwritten: merge conflicts are surfaced via `conflicts` on state updates
