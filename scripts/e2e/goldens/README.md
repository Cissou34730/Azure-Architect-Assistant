# Goldens

Each scenario has a committed `report.normalized.json` that is used as a golden baseline.

First-time setup:
- Run with `--update-goldens` to generate fresh goldens from a known-good run.

Goldens are intentionally **normalized** (high-variance fields like timestamps and full LLM answers are removed) so diffs are structural and stable.
