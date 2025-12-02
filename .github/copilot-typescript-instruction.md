---
applyTo: "**/*.ts,**/*.tsx"
---
# Project coding standards for TypeScript, React 19, and Tailwind CSS 4.1

Apply the [general coding guidelines](./general-coding.instructions.md) to all code.

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
  - composition over inheritance.
- In React, favor functional patterns in component logic (stateless helpers, small composable components).

---

## 2. General Guardrails

- Use **pure ES modules** only; do not introduce `require`, `module.exports`, or other CommonJS patterns.
- Assume the modern JSX transform (no need to import `React` solely for JSX).
- Use the repository’s existing build, lint, and test scripts unless explicitly instructed otherwise.
- When intent is not obvious, briefly document the design trade-offs and reasoning.

---

## 3. Project Organization

- Use **kebab-case** filenames for non-React modules.
- Use **PascalCase** filenames for React component modules.
- Keep tests, types, and helpers close to their implementation when it improves discoverability.
- Prefer reusing existing utilities and patterns before adding new ones.
- Keep modules cohesive; avoid “god files” mixing unrelated responsibilities.

---

## 4. Naming & Style

- Use **PascalCase** for React components, classes, interfaces, enums, exported type aliases.
- Use **camelCase** for variables, functions, and non-component values.
- Do **not** prefix interfaces or types with `I` or `T`.
- Name modules and symbols for their **behavior or domain meaning**, not implementation details.

---

## 5. TypeScript Guidelines

### 5.1 Type System Expectations

- Enable and respect **strict** type checking.
- Avoid `any`; prefer `unknown` with proper narrowing.
- Prefer **type narrowing** over casting.
- Use **discriminated unions** for complex state.
- Centralize shared object shapes.
- Use built-in TypeScript utility types.

### 5.2 Data, Immutability & Functional Style

- Prefer immutable data (`const`, `readonly`).
- Avoid mutating parameters; return new values.
- Write shared logic as **pure functions**.
- Prefer composition over complex branching logic.

### 5.3 Async & Error Handling

- Use `async/await`.
- Wrap awaited calls in `try/catch`.
- Validate inputs early; use early returns.
- Log or propagate structured errors consistently.

---

## 6. React 19 Guidelines

### 6.1 Components

- Use **function components** exclusively.
- Declare props with explicit TypeScript types.
- Keep components small and focused.
- Use ES default parameters instead of `defaultProps`.
- Favor composition from smaller components and helpers.

### 6.2 Hooks

- Follow the **Rules of Hooks**.
- Extract reusable logic into custom hooks.
- Use cleanup functions in `useEffect`.

### 6.3 State & Data Flow

- Keep state colocated with usage.
- Avoid redundant or derivable state.
- Use `useReducer` for multi-step logic.
- Use transitions where appropriate for better UX.

### 6.4 Accessibility

- Prefer semantic HTML.
- Ensure keyboard accessibility.
- Use ARIA attributes only when necessary.

---

## 7. Tailwind CSS 4.1 Guidelines  
**All styling MUST be done with Tailwind utilities and design tokens.**

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

- Use Tailwind **utility classes directly** in JSX.
- Combine utilities for layout and appearance.
- Do **not** move single-use style combinations into CSS.
- Avoid custom CSS when a Tailwind utility exists.

### 7.3 Class Composition & Grouping

- For conditional classes, use a helper such as `cn(...)`.
- Group utilities in consistent order:
  1. Layout & display  
  2. Spacing  
  3. Typography  
  4. Colors  
  5. Borders & radius  
  6. Effects  
  7. Variants (hover:, focus:, disabled:, sm:, md:, etc.)

### 7.4 Semantic Colors & Banning Raw Palette Classes

- **Raw Tailwind palette classes are forbidden**:
  - `text-blue-600`, `bg-red-500`, `border-yellow-200`, etc.
- Always use **semantic color utilities** bound to tokens:
  - `bg-primary`, `text-primary-foreground`
  - `bg-success`, `bg-warning`, `bg-card`
  - `border-border`, `text-muted-foreground`
- Introduce new intents by defining new semantic tokens, not by using palette names.

### 7.5 Required: Intent-Based Variant Maps

Components supporting variants MUST follow intent-based, semantic class maps.

Example:

```ts
type Intent = "primary" | "success" | "warning" | "danger" | "neutral";

const intentClasses: Record<Intent, string> = {
  primary: "bg-primary text-primary-foreground border-primary",
  success: "bg-success text-success-foreground border-success",
  warning: "bg-warning text-warning-foreground border-warning",
  danger: "bg-destructive text-destructive-foreground border-destructive",
  neutral: "bg-card text-muted-foreground border-border",
};
```

Forbidden:

```ts
color: "text-blue-600 bg-blue-50"
```

### 7.6 Layout & Responsiveness

- Use responsive utilities (`sm:`, `md:`, `lg:`).  
- Use logical properties for bidirectional layouts.

### 7.7 Strict Rules for Custom CSS

Custom CSS is allowed **only** for:

- reusable component patterns used widely,
- styles Tailwind cannot express (complex masks, animations),
- global/base styles.

Forbidden:

- one-off utility aliases:
  ```css
  .flex-center { @apply flex items-center justify-center }
  ```
- variant logic in CSS,
- component-specific styling in `index.css`,
- CSS Modules, styled-components, Emotion, or any CSS-in-JS.

---

## 8. UI, State & Separation of Concerns

- Keep React components focused on UI behavior.
- Move business logic into hooks or service modules.
- Decouple API code from components.
- Use Tailwind utilities for layout and appearance.

---

## 9. Testing Expectations

- Use the project’s test framework (Vitest / Jest + React Testing Library).
- Add/update tests when introducing new logic.
- Test:
  - normal rendering/behavior,
  - edge cases,
  - async flows.
- Prefer deterministic tests (fake timers, mocks).

---

## 10. Documentation & Comments

- Add TSDoc/JSDoc when helpful.
- Explain **why**, not what.
- Remove outdated comments during refactors.
- Update architectural docs when introducing new patterns.
