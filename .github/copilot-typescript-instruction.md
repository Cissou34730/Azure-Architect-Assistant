---
description: 'TypeScript, React, and Tailwind coding standards for frontend source files'
applyTo: '**/*.ts, **/*.tsx'
---

# TypeScript / React / Tailwind Rules (Scoped)

## Scope

- Applies only to `*.ts` and `*.tsx`.
- Stack target: TypeScript 5+, React 19, Tailwind 4.1.

## General Instructions

- Keep implementations explicit, typed, and minimal.
- Keep diffs limited to requested behavior.

## Code Standards

- `any` is forbidden (explicit and implicit).
- Use ES modules only.
- Prefer explicit domain types, unions, and type guards at boundaries.
- Do not relax ESLint/TypeScript config to bypass type safety.

## React Requirements

- Function components only; do not use `React.FC`.
- Keep component logic cohesive; extract reusable logic into hooks/utilities.
- Component filenames use `PascalCase`; non-component TS files use `kebab-case`.

## Tailwind Requirements

- Use Tailwind 4.1 CSS-first approach.
- Use semantic token classes over palette classes.
- Do not introduce `tailwind.config.*` for routine work in this repo.

## Best Practices

- Keep business logic in hooks/services; keep components UI-focused.
- Use deterministic patterns and explicit error handling.
- Add concise comments only for non-obvious intent.

## TS/TSX Definition of Done

1. Global TDD policy from `copilot-instructions.md` is followed.
2. No `any` introduced.
3. Types remain explicit at boundaries.
4. Any test omission is explicitly justified in the task output.
