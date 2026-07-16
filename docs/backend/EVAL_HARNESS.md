# Output Quality Evaluation Strategy

The repository uses layered quality gates so a technically valid response can
still fail when it is generic, unsupported, incomplete, or not useful for an
architecture decision.

## Pull-request gates

- Strict YAML journey manifests reject unknown fields.
- Healthy golden fixtures permit no expected failures and require at least 4/5.
- Journey checks cover stage, response shape, required concepts, unsupported
  claims, citation presence and host, word ceilings, and thin receipts.
- Runtime tests verify every graph output path passes through the quality gate.
- Rubric calibration tests reject polished but decision-free output.
- Frontend unit tests run in the main CI workflow.

Run locally with:

    uv run pytest backend/tests/eval backend/tests/test_quality_gate_loop.py backend/tests/test_aaa_e2e_runner_utils.py -m quality

## Live evaluation

The live harness accepts an executor and passes each YAML scenario input through
the actual pipeline. The E2E runner stores the full assistant answer in the run
report and transcript. Normalized goldens retain the answer hash, advisory
criteria, and critical failures, so output changes cannot disappear from review.

Run a credentialed live journey explicitly:

    uv run python scripts/e2e/aaa_e2e_runner.py --scenario scenario-behavior --in-process

Live execution is intentionally opt-in. Repository owners must approve the
credential, schedule, artifact-retention, and redaction policy before enabling a
hosted scheduled lane. Live failures are release signals and must never be
automatically promoted as new goldens.

## Runtime protection and telemetry

Every graph output path, including specialist workers, passes through the quality
gate before persistence. Retry exhaustion is marked as quality_gate_exhausted,
logged with stage and failure details, and surfaced in response warnings. It is
never counted as a pass.

## Human calibration

At least monthly, reviewers sample live reports and label recommendation,
rationale, request specificity, trade-off, risk, evidence, and next action.
Disagreements are resolved by an Azure architect. Deterministic rules should only
change when they improve agreement on the labeled set. Track false-pass and
false-fail rates separately, with a target below 10 percent for each.

## Extending the harness

1. Add a scenario manifest and reference-oriented assertions.
2. Add a healthy normalized report with a declared minimum score.
3. Include hard negative answers that should fail despite polished wording.
4. Run the deterministic lane and, when credentials are available, a live replay.
5. Review output diffs; never accept a failure merely because it is expected.

Status: Active
Last updated: 2026-07-16
Owner: Engineering
