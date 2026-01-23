# AAA E2E Validation Suite

This folder contains the **backend-driven** E2E runner and scenario packs described in `plan-aaaE2eTestPlan.prompt.md`.

## Run (backend-only)

- Against a running backend:
  - `uv run python scripts/e2e/run_aaa_e2e.py --base-url http://localhost:8000 --scenario scenario-a`

- In-process (no separate server):
  - `uv run python scripts/e2e/run_aaa_e2e.py --in-process --scenario scenario-a`

## Update goldens

- `uv run python scripts/e2e/run_aaa_e2e.py --in-process --scenario scenario-a --update-goldens`

Goldens live under `scripts/e2e/goldens/` and are committed.
Run outputs are written under `scripts/e2e/runs/` (not intended to be committed).
