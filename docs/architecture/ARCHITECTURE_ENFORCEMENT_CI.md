# Architecture Enforcement CI

Phase 1 adds warning-first automation so the repo can start enforcing boundaries before the large folder moves begin.

## Checks

### Backend import boundaries

- Config file: [.importlinter](../../.importlinter)
- Local command: `PYTHONPATH=backend uv run lint-imports --config .importlinter`
- Current scope:
  - router-to-service/model layering baseline
  - selected router package independence
  - `agents_system` forbidden from depending on `app.routers`

The current config is intentionally conservative. It establishes a baseline without pretending the final feature layout already exists.

### Horizontal module freeze

- Script: [scripts/check_horizontal_module_freeze.py](../../scripts/check_horizontal_module_freeze.py)
- Local command: `uv run python scripts/check_horizontal_module_freeze.py`
- Current mode: warning-oriented

Frozen roots in Phase 0/1:

1. `backend/app/services/`
2. `backend/app/routers/`
3. `frontend/src/hooks/`
4. `frontend/src/services/`
5. `frontend/src/types/`
6. `frontend/src/components/` outside `components/common/`

Existing approved subpackages remain allowed so the check can focus on preventing new architectural drift.

### Frontend import boundaries

- Config file: [eslint.config.js](../../eslint.config.js)
- Local lint command: `npx eslint "frontend/src/features/**/*.{ts,tsx}" "frontend/src/{services,hooks,types}/**/*.{ts,tsx}"`
- Unit test: [frontend/src/architecture/import-boundaries.test.ts](../../frontend/src/architecture/import-boundaries.test.ts)

The Phase 1 frontend baseline does two things:

1. It errors when top-level shared modules import feature modules.
2. It warns when feature modules reach into top-level `services/`, `hooks/`, or `types/`.

Strict cross-feature bans are deferred until the Phase 2 carve-out gives the repo stable feature-local import paths.

## Workflow

Architecture checks run in [.github/workflows/architecture.yml](../../.github/workflows/architecture.yml).

The workflow uses `continue-on-error` during the baseline rollout so new visibility does not stall unrelated pull requests. The plan is to promote these jobs to blocking once Phase 2 and Phase 3 have reduced the existing dependency debt.