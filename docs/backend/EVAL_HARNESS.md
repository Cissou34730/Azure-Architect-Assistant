# Eval Harness Foundation

This repository keeps the Phase 0 baseline eval harness in `backend/tests/eval/`.

## Scope

- `backend/tests/eval/reporting.py` converts normalized runner reports into rubric-friendly turn and scenario summaries.
- `backend/tests/eval/eval_runner.py` loads committed golden scenarios, evaluates them with the existing reporting layer, and checks that baseline failures still match the expected snapshot.
- `backend/tests/eval/golden_scenarios/` contains the initial representative scenario set for behavior, clarification guardrails, and delivery-artifact guardrails.

## Relationship to the live E2E runner

- Live replay still belongs to `scripts/e2e/aaa_e2e_runner.py`.
- The test harness under `backend/tests/eval/` is intentionally report-driven for now: it validates committed normalized reports without spinning up the full backend pipeline.
- This keeps the Phase 0 baseline cheap to run in unit-test workflows while reusing the same report shape and scoring rules.

## Run

```bash
uv run python -m pytest backend/tests/eval/test_eval_runner.py backend/tests/eval/test_reporting.py
```

## Extending the harness

1. Add a new folder under `backend/tests/eval/golden_scenarios/`.
2. Commit `scenario.json` with the scenario id, description, tags, and expected baseline failures.
3. Commit the matching `report.normalized.json` using the existing E2E runner report shape.
4. Keep `reporting.py` as the single scoring layer; extend it instead of adding a second scorer.

---

**Status**: Active  
**Last Updated**: 2026-04-17  
**Owner**: Engineering
