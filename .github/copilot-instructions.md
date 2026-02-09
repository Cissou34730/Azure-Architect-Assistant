<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Copilot workspace instructions — Azure Architect Assistant

Purpose
- Assist contributors and Copilot in a consistent way for the "Azure Architect Assistant" project: a monorepo with a TypeScript React frontend and a Python backend that together provide: (1) project description authoring, (2) interactive documentation chat, (3) RAG/KB management, and (4) architecture + IaC generation.

High-level rules (always)
- Make the smallest chgit ange that solves the problem; prefer incremental, reviewable diffs and small commits.
- Follow Single Responsibility Principle (SRP) and DRY; prefer simple, readable code over cleverness.
- Use descriptive names (e.g., days_until_expiration); if a comment is needed to explain complex logic, consider refactoring.
- Validate and sanitize all external input (APIs, user input, files); never assume correctness.
- Do not add new frameworks or major dependencies without explicit approval.
	[x] Code Style and Conventions:
	- Liting: ESLint with recommended settings for TypeScript and React, eslint must be run from the root directory and use /eslint.config.js
	- Formatting: Prettier with default settings
	- Python: Follow ruff recommended style guide and configurations in pyproject.toml
	- TypeScript: Use strict mode.type implecitly or explicitly. NEVER EVER allows any type. All const, variable, function return types must be typed.
	- Not hardcoding values. Use configuration files where appropriate.
	- Naming convention is different between front and backend use apiMappings.ts to map names if needed	
	- mypy.ini at the root of the project for type checking configuration

Documentation policy (NEW / IMPORTANT)
- All project documentation must reside under the single top-level docs directory: /docs at the repository root.
- Only one high-level global overview document (for example: /docs/README.md or /docs/HIGH_LEVEL_OVERVIEW.md) is allowed directly inside the /docs root. All other documentation must live in subfolders under /docs (for example: /docs/frontend, /docs/backend, /docs/architecture, /docs/iac, /docs/operational, /docs/specs).
- Do NOT create package-level docs outside /docs (avoid frontend/docs or backend/docs); prefer /docs/frontend and /docs/backend so documentation discovery is centralized.
- Maintain a top-level table of contents at /docs/README.md that links to subfolders and major documents.
- Documentation must be updated for any significant change (API/behavior changes, feature additions, infra/IaC changes, public docs). Pull requests that modify behavior must include corresponding doc updates or an explicit justification in the PR description.
- Each doc should include a short "Last updated" metadata header and minimal change notes for significant edits.

Repository layout & docs (summary)
- Monorepo top-level code folders: `frontend/` and `backend/`.
- Centralized docs folder: `/docs/` with subfolders as needed (see policy above).
- New public-facing behavior must include or update docs and tests.

Tech stack & tooling
- Frontend: React 19+, TypeScript 5+, Vite, TailwindCSS 4.1. Use strict TypeScript and `any` is strictly prohibited implicit or explicit.
- Backend: Python 3.10+. Use `uv` for environment and dependency management (uv add / uv sync / uv lock).
- Run Python scripts via `uv python <script>` (or repository-standard uv wrapper).
- Linting/formatting: ESLint (TS/React) + Prettier for frontend, Ruff for Python.
- Tests: unit tests required for logic changes; run the test suite before submitting PRs.

Dependency & release rules
- For Python, do NOT use pip directly in CI or contributor instructions — use `uv` commands to ensure reproducible environments.
- For frontend dependencies, use the repository’s configured package manager and lockfiles (respect existing package-lock.json) in the /frontend folder.

Coding & PR conventions
- Small, focused commits with descriptive messages; one concern per PR.
- Include tests and documentation updates for behavioral changes.
- In PR description: summary, motivation, testing steps, and any migration notes.
- If a change affects infra/IaC or developer workflows, include upgrade/migration guidance.

Copilot-specific guidance
- Prefer minimal, idiomatic code suggestions that follow the rules above.
- When offering multi-file changes, present a clear plan and split into small PRs.
- For any ambiguous requirement or design decision, ask a clarifying question rather than making broad assumptions.
- When generating IaC or architecture text, include assumptions, constraints, and a short justification for design choices.

When to escalate
- If a proposed change touches security-sensitive code, secrets, or infra configuration, open an issue and request a security/infra review.
- If a requested feature implies adding a major new dependency, propose alternatives and request approval.

Contact / process
- If uncertain about conventions or priority, open an issue describing the trade-offs and tag the maintainers; do not proceed with large, risky changes without consensus.

Change log
- Record notable edits to this file in PR descriptions to keep its guidance current.
- [x] Customize the Project
	
	Verify that all previous steps have been completed successfully and you have marked the step as completed.
	Develop a plan to modify codebase according to user requirements.
	Apply modifications using appropriate tools and user-provided references.
	
	-[x] Quality ensurance checklist:
	- Ensure commit messages are clear and descriptive of the changes made.
