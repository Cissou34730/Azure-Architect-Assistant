# Workflow and Traceability Runbook

## Purpose

Define the mandatory workflow for issue-first delivery, traceability links, and exception handling.

## Workflow Policy

### Issue Requirement

- **Mandatory**: all non-trivial work (feature, bug fix, refactor with behavior risk, policy/docs governance change, infra change).
- **Optional**: typo-only edits or trivial local wording fixes with no behavior/process impact.

### Branch Naming

- Standard: `type/<issue-id>-short-description`
- Examples:
  - `feature/123-project-chat-streaming`
  - `fix/456-doc-lane-link-check`
  - `docs/789-governance-matrix`

### Commit Linking

- Every non-trivial commit should include an issue reference in message body or subject.
- Preferred formats:
  - `Refs #123`
  - `Fixes #123` (when closing)

### Pull Request Policy

- PR is recommended for collaborative work and required when branch protection is configured.
- Direct branch merge is allowed only when repository policy allows it and traceability requirements are met.

### Changelog and Docs Linking

- Non-trivial changes must include:
  1. `CHANGELOG.md` update in `Unreleased` section.
  2. Docs update in correct lane(s): `/docs/agents` and/or domain docs.
  3. Link integrity from `/docs/README.md` and relevant operations index.

## Exception Path (No Existing Issue)

Use this path only when immediate work is required and issue creation is blocked.

1. Create a decision record under `docs/operations/decisions/` with:
   - reason issue was unavailable,
   - scope,
   - risk,
   - follow-up issue owner and due date.
2. Include decision record path in commit message.
3. Open the missing issue at first opportunity and back-link commits.

## Compliance Checklist

Before merge, confirm:

1. Issue link exists (or approved exception record).
2. Branch naming follows policy.
3. Commits contain issue reference.
4. Changelog updated for non-trivial changes.
5. Relevant docs lane(s) updated.

## Compliant Example

- Issue: `#742`
- Branch: `fix/742-backend-uv-standardization`
- Commits: include `Refs #742`
- Docs: updates in `docs/operations` and `docs/README.md`
- Changelog: entry under `Unreleased`

## Non-Compliant Example

- Branch: `temp/fixes`
- No issue for behavior change
- No changelog update
- No docs lane update

## Authority

- Maintainers approve exceptions.
- Repeated non-compliance triggers mandatory PR review until stabilized.

---

**Status**: Active  
**Last Updated**: 2026-02-22  
**Owner**: Engineering
