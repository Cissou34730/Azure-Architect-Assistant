"Azure Architect Assistant" project: a monorepo with a TypeScript React frontend and a Python backend that together provide: (1) project description authoring, (2) interactive documentation chat, (3) RAG/KB management, and (4) architecture + IaC generation + Pricing via Microsoft API.

Tech stack & tooling
- Frontend: React 19+, TypeScript 5+, Vite, TailwindCSS 4.1. Use strict TypeScript and `any` is strictly prohibited implicit or explicit.
- Backend: Python 3.10+. Use `uv` for environment and dependency management (uv add / uv sync / uv lock).
- Run Python scripts via `uv python <script>` (or repository-standard uv wrapper).
- Linting/formatting: ESLint (TS/React) + Prettier for frontend, Ruff for Python.
- Tests: unit tests required for logic changes; run the test suite before submitting PRs.

TailwindCSS 4.1 policy (IMPORTANT)
- This repository uses Tailwind 4.1 in CSS-first mode.
- The authoritative Tailwind configuration lives in the global CSS entrypoint using:
  - `@import "tailwindcss";`
  - `@theme` for design tokens
  - `@custom-variant` for custom states/themes
  - `@utility` for custom utilities
- Do not introduce or rely on `tailwind.config.js` / `tailwind.config.ts` for normal work in this repo.
- Prefer semantic token utilities (for example `bg-surface`, `text-foreground`, `border-border`, `text-brand`) over palette utilities.
- Prefer token-driven values over arbitrary values in class strings. Arbitrary values are allowed only for true one-off layout constraints.
- Do not introduce Tailwind plugin-based patterns when a native v4.1 directive or utility can solve the same problem.
- Theme switching must be token-driven (`@theme` + `data-theme`/custom variant), not component-by-component color forks.


High-level rules (always)
- Make the smallest changes that solves the problem; prefer incremental, reviewable diffs and small commits.
- Follow Single Responsibility Principle (SRP) and DRY; prefer simple, readable code over cleverness.
- Use descriptive names (e.g., days_until_expiration); if a comment is needed to explain complex logic, consider refactoring.
- Validate and sanitize all external input (APIs, user input, files); never assume correctness.
- Do not add new frameworks or major dependencies without explicit approval.
- Liting: ESLint with recommended settings for TypeScript and React, eslint must be run from the root directory and use /eslint.config.js
- Formatting: Prettier with default settings
- Python: Follow ruff recommended style guide and configurations in /pyproject.toml
- TypeScript: NEVER EVER allows any type. All const, variable, function return types must be typed.
- Not hardcoding values, no magic numbers. Use configuration files where appropriate.
- Naming convention is different between front and backend use apiMappings.ts to map names if needed
- mypy.ini at the root of the project for type checking configuration

Documentation policy (NEW / IMPORTANT)
- All project documentation must reside under the single top-level docs directory: /docs at the repository root.
- Only one high-level global overview document (for example: /docs/README.md or /docs/HIGH_LEVEL_OVERVIEW.md) is allowed directly inside the /docs root. All other documentation must live in subfolders under /docs (for example: /docs/frontend, /docs/backend, /docs/architecture, /docs/iac, /docs/operational, /docs/specs).
- Do NOT create package-level docs outside /docs (avoid frontend/docs or backend/docs); prefer /docs/frontend and /docs/backend so documentation discovery is centralized.
- Maintain a top-level table of contents at /docs/README.md that links to subfolders and major documents.
- Documentation must be updated for any significant change (API/behavior changes, feature additions, infra/IaC changes, public docs). 



Dependency & release rules
- For Python, do NOT use pip directly in CI or contributor instructions — use `uv` or `uvx` commands to ensure reproducible environments.
- For frontend dependencies, use the repository’s configured package manager and lockfiles (respect existing package-lock.json) in the /frontend folder.


When to escalate
- If a proposed change touches security-sensitive code, secrets, or infra configuration, open an issue and request a security/infra review.
- If a requested feature implies adding a major new dependency, propose alternatives and request approval
