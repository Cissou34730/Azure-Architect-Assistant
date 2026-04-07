---
description: 'Python coding conventions and guidelines'
applyTo: '**/*.py'
---


## General Instructions

- Keep implementations explicit, minimal, and maintainable.
- Keep diffs limited to requested behavior.

## Code Standards

- Use type hints (built-in generics where possible).
- Keep functions focused and modules cohesive.
- Add docstrings for public modules, classes, and functions.
- Follow project typing/lint configs (`ruff.toml`, `mypy.ini`, `pyrightconfig.json`).
- Keep imports at module top except justified exceptions (circular/optional/heavy).
- Typing is mandatory of all ojects, never all any or implicit type
- Respect at any cost Single Responsability Principalss

## Naming and Structure

- `snake_case` for functions/variables.
- `PascalCase` for classes.
- Avoid import-time side effects.
- All import must be at the top of the module except if it's absolutly mendatory to do it inside the module

## Best Practices

- Use clear error paths and explicit return contracts.
- Keep module responsibilities narrow.
- Add concise comments only for non-obvious intent.
- All names must be understandable and selfexplanable
