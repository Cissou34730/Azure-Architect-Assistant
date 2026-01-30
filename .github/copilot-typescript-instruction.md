---
applyTo: "**/*.ts,**/*.tsx"
---

# Project coding standards for TypeScript, React 19, and Tailwind CSS 4.1


This project targets **TypeScript 5.x+**, **ES2022 modules**, **React 19.x**, and **Tailwind CSS 4.x (4.1+)**.
All UI styling MUST be done with **TailwindCSS** (utility classes + design tokens).

---

## 1. Core Intent

- Respect the existing architecture and coding standards.
- Prefer readable, explicit solutions over clever shortcuts.
- Extend existing abstractions before introducing new ones.
- Prioritize maintainability and clarity: small, focused functions and cohesive modules.
- Prefer **functional programming** for shared logic:
  - pure functions
  - immutable data
  - composition over inheritance
- In React, favor functional patterns in component logic (stateless helpers, small composable components).

---

## 2. Operational Guardrails (Refactor Safety)

- Use **pure ES modules** only; do not introduce `require`, `module.exports`, or other CommonJS patterns.
- Assume the modern JSX transform (no need to import `React` solely for JSX).
- Do not weaken repository lint/type rules to make errors “go away”.
  - **Never** add global exceptions in ESLint/TS config.
  - If a specific case cannot be fixed cleanly, use an **inline** suppression with a short justification.

---

## 3. Project Organization

- Use **kebab-case** filenames for non-React modules.
- Use **PascalCase** filenames for React component modules.
- Keep tests, types, and helpers close to their implementation when it improves discoverability.
- Prefer reusing existing utilities and patterns before adding new ones.
- Keep modules cohesive; avoid “god files” mixing unrelated responsibilities.
- If a module is large but **linear and cohesive** (e.g., a long form), prefer extracting **logic** (hooks/utils) over splitting markup into many subcomponents.

---

## 4. Naming & Style (Strict)

- Use **PascalCase** for React components, classes, interfaces, enums, exported type aliases.
- Use **camelCase** for variables, functions, and non-component values.
- Do **not** prefix interfaces or types with `I` or `T`.
- Prefer domain/behavior names, not implementation detail names.
- Avoid ambiguous placeholder names:
  - Forbidden examples: `data`, `item`, `obj`, `val`, `e`, `res`
- Prefer explicit event/result names:
  - Examples: `mouseEvent`, `httpResponse`, `userProfile`, `cartItem`
- Export alignment:
  - If a file has a default export, the file name should match the default export name.

---

## 5. TypeScript Guidelines

### 5.1 Type Safety Hierarchy (Mandatory)

- **Priority 1:** Define a specific **interface** or **type alias** for shapes.
- **Priority 2:** Validate external/dynamic data via **type guards** (or equivalent runtime checks).
- **Last resort:** `unknown`, only when the data is truly dynamic and cannot be modeled up front.
- **Forbidden:** `any`.
- **Type assertions (`as`)** are allowed only when paired with runtime validation (type guard / invariant check) or when asserting a value produced by a trusted constructor.

### 5.2 Narrowing & Unions

- Prefer **type narrowing** over casting.
- Use **discriminated unions** for complex state (avoid “ghost state” like `error?: string` to encode exclusive states).
- Centralize shared object shapes.
- Prefer built-in TypeScript utility types.

### 5.3 Immutability & Functional Style

- Prefer immutable data (`const`, `readonly`).
- Avoid mutating parameters; return new values.
- Write shared logic as **pure functions**.
- Prefer composition over deeply nested branching.

### 5.4 Async & Error Handling

- Use `async/await`.
- Wrap awaited calls in `try/catch` when errors are expected.
- Validate inputs early; use early returns.
- Propagate structured errors consistently (avoid ad-hoc strings when a typed error shape is appropriate).

---

## 6. React 19 Guidelines

### 6.1 Components

- Use **function components** exclusively.
- Declare props with explicit TypeScript types.
- Do **not** use `React.FC`; use an explicit props type instead.
- Keep components focused.
- Use ES default parameters instead of `defaultProps`.
- Favor composition from smaller components and helpers.
- Avoid splitting a large component purely to satisfy `max-lines` if it is cohesive and linear.
  - Prefer extracting self-contained logic into hooks (`useX`) or utilities first.

### 6.2 Hooks

- Follow the **Rules of Hooks**.
- Extract reusable logic into custom hooks.
- Use cleanup functions in `useEffect`.
- Do not introduce `useMemo`/`useCallback` unless:
  - a costly calculation is proven/likely, or
  - referential stability is required for correctness.

### 6.3 State & Data Flow

- Keep state colocated with usage.
- Avoid redundant/derivable state.
- Use `useReducer` for multi-step logic.
- Use transitions where appropriate for better UX.

### 6.4 Accessibility

- Prefer semantic HTML.
- Ensure keyboard accessibility.
- Use ARIA attributes only when necessary.

---

## 7. Tailwind CSS 4.1 Guidelines
All styling MUST be done with Tailwind utilities and design tokens.

### 7.1 Setup & Configuration

- Import Tailwind in CSS:
  ```css
  @import "tailwindcss";
  ```
- Define tokens using `@theme` (colors, spacing, radii, typography).
- Structure CSS using:
  ```css
  @layer theme, base, components, utilities;
  ```

### 7.2 Utility-First Usage in JSX/TSX

- Use Tailwind utilities directly in JSX.
- Do not move single-use style combos into CSS.
- Avoid custom CSS when a Tailwind utility exists.

### 7.3 Class Composition

- For conditional classes, use a helper such as `cn(...)`.
- Keep class groups in consistent order:
  1. Layout & display
  2. Spacing
  3. Typography
  4. Colors
  5. Borders & radius
  6. Effects
  7. Variants (hover:, focus:, disabled:, sm:, md:, etc.)

### 7.4 Semantic Colors Only (Strict)

- Raw Tailwind palette classes are forbidden:
  - `text-blue-600`, `bg-red-500`, `border-yellow-200`, etc.
- Always use semantic token-based utilities:
  - `bg-primary`, `text-primary-foreground`, `border-border`, `text-muted-foreground`, etc.
- Introduce new intents by defining semantic tokens, not by using palette names.

### 7.5 Required: Intent-Based Variant Maps

Reusable components supporting variants MUST use intent-based semantic class maps (no raw palette usage).

---

## 8. UI, State & Separation of Concerns

- Keep React components focused on UI behavior.
- Move business logic into hooks or service modules.
- Decouple API code from components.
- Prefer extracting **logic** (hooks/utils) over extracting markup subcomponents.

---

## 9. Testing Expectations

- Use the project’s test framework (Vitest/Jest + React Testing Library).
- Add/update tests when introducing new logic.
- Test normal behavior, edge cases, and async flows.
- Prefer deterministic tests (fake timers, mocks).

---

## 10. Documentation & Comments

- Add TSDoc/JSDoc when helpful.
- Explain **why**, not what.
- Update architectural docs when introducing new patterns.
