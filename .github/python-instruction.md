---
description: 'Python coding conventions and guidelines'
applyTo: '**/*.py'
---

# Python Rules (Scoped)

## Scope

- Applies only to `*.py` files.
- Python target: 3.10+.

## General Instructions

- Keep implementations explicit, minimal, and maintainable.
- Keep diffs limited to requested behavior.

## Code Standards

- Use type hints (built-in generics where possible).
- Keep functions focused and modules cohesive.
- Add docstrings for public modules, classes, and functions.
- Follow project typing/lint configs (`ruff.toml`, `mypy.ini`, `pyrightconfig.json`).
- Keep imports at module top except justified exceptions (circular/optional/heavy).

## Naming and Structure

- `snake_case` for functions/variables.
- `PascalCase` for classes.
- Avoid import-time side effects.

## Best Practices

- Use clear error paths and explicit return contracts.
- Keep module responsibilities narrow.
- Add concise comments only for non-obvious intent.

## Python Definition of Done

1. Global TDD policy from `copilot-instructions.md` is followed.
2. Type hints remain consistent with project typing policy.
3. No unrelated structural cleanup mixed into the same change.

