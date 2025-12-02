---
applyTo: "**/*.ts,**/*.tsx"
---
# Project coding standards for TypeScript, React 19, and Tailwind CSS 4.1

Apply the [general coding guidelines](./general-coding.instructions.md) to all code.

This project targets **TypeScript 5.x+**, **ES2022 modules**, **React 19.x**, and **Tailwind CSS 4.x (4.1+)**.

---

## 1. Core Intent

- Respect the existing architecture and coding standards.
- Prefer readable, explicit solutions over clever shortcuts.
- Extend existing abstractions before introducing new ones.
- Prioritize maintainability and clarity: small, focused functions and cohesive modules.

---

## 2. General Guardrails

- Use **pure ES modules** only; do not introduce `require`, `module.exports`, or other CommonJS patterns.
- Assume the modern JSX transform (no need to import `React` solely for JSX).
- Use the repository’s existing build, lint, and test scripts unless explicitly instructed otherwise.
- When intent is not obvious, briefly document design trade-offs.

---

## 3. Project Organization

- Use **kebab-case** filenames for non-React modules  
  e.g. `user-session.ts`, `data-service.ts`.
- Use **PascalCase** filenames for React component modules  
  e.g. `UserProfile.tsx`, `DashboardPanel.tsx`.
- Keep tests, types, and helpers close to their implementation when it improves discoverability.
- Prefer reusing or extending existing utilities and patterns before adding new ones.

---

## 4. Naming & Style

- Use **PascalCase** for:
  - React components
  - classes
  - interfaces
  - enums
  - exported type aliases
- Use **camelCase** for variables, functions, and non-component values.
- Do not prefix interfaces or types with `I` or `T`; use descriptive names instead.
- Name modules and symbols for their **behavior or domain meaning**, not their implementation details.

---

## 5. TypeScript Guidelines

### 5.1 Type System Expectations

- Enable and respect **strict** type checking.
- Avoid `any` (implicit or explicit).  
  - If necessary, prefer `unknown` and narrow it with type guards.
- Prefer **type narrowing** (control flow, custom predicates, `in` checks, etc.) over casting.
- Use **discriminated unions** for complex state machines or event types.
- Centralize shared object shapes and contracts instead of duplicating type definitions.
- Use built-in TypeScript utility types (`Readonly`, `Partial`, `Pick`, `Omit`, `Record`, etc.) to express intent.

### 5.2 Data & Immutability

- Prefer immutable data where practical:
  - `const` for bindings
  - `readonly` properties and arrays when appropriate.
- Avoid mutating function parameters; return new values instead.
- Keep pure logic in standalone functions or modules that are easy to test.

### 5.3 Async & Error Handling

- Use `async/await` for asynchronous flows.
- Wrap awaited calls in `try/catch` and propagate structured errors.
- Validate inputs early and use early returns to avoid deep nesting.
- Route errors through the project’s logging / telemetry utilities.

---

## 6. React 19 Guidelines

### 6.1 Components

- Use **function components** for all new React code.
- Declare props with explicit TypeScript types or interfaces.
- Keep components small, focused, and easy to test.
- Use ES defaults for props (`{ prop = default }`) instead of `defaultProps` on function components (React 19 removes `defaultProps` for functions).

### 6.2 Hooks

- Follow the official **Rules of Hooks**.
- Extract reusable behavior into custom hooks (`useSomething`) instead of duplicating logic.
- Keep hooks at the top level of the component or custom hook (no conditional calls).
- Use `useEffect` cleanup functions to dispose subscriptions, event listeners, and other side-effects.

### 6.3 State & Data Flow

- Keep state colocated with the components that use it.
- Avoid duplicating state that can be derived from existing values.
- Use React 19 capabilities (e.g. `useTransition`, Actions, `useActionState`) where they simplify handling pending, error, and optimistic UI states, following the official examples.
- Prefer controlled components for forms unless there is a clear reason to use uncontrolled ones.

### 6.4 Accessibility

- Prefer semantic HTML elements (`button`, `nav`, `header`, etc.) over generic `div`s.
- Ensure interactive elements are keyboard accessible.
- Use ARIA attributes only when native semantics are not sufficient.

---

## 7. Tailwind CSS 4.1 Guidelines

This project uses Tailwind CSS v4 with **CSS-first configuration**.

### 7.1 Setup & Configuration

- Import Tailwind in CSS using:

  ```css
  @import "tailwindcss";
Configure design tokens using @theme in the same CSS file (fonts, colors, spacing, breakpoints, etc.):

css
Copier le code
@theme {
  --font-sans: "Inter", system-ui, -apple-system, sans-serif;
  --color-brand-500: oklch(...);
  /* ... */
}
Tailwind uses CSS layers:

css
Copier le code
@layer theme, base, components, utilities;
Use these layers for:

theme: design tokens

base: base styles / resets

components: custom component-level styles

utilities: custom utility classes

### 7.2 Utility-First Usage in JSX/TSX
Prefer Tailwind utility classes directly in JSX for most styling.

Use design tokens defined via @theme to keep colors, spacing, typography, and sizing consistent.

Only introduce additional CSS when:

creating reusable component classes

implementing complex patterns that would be unreadable as a long list of utilities

Avoid reimplementing styles that already exist as Tailwind utilities.

### 7.3 Layout & Responsiveness
Use Tailwind’s layout utilities (flex, grid, gap-*, justify-*, items-*, etc.) directly in JSX.

Use responsive variants (e.g. sm:, md:, lg:) and container queries:

Mark containers with @container in CSS where needed.

Use container query variants (e.g. @sm:, @max-md:) according to the Tailwind v4 docs.

Use logical properties and utilities (e.g. margin/padding logical variants) when working with bidirectional layouts.

#### 7.4 Design Tokens & Colors
Define the project color palette using @theme so it becomes available as CSS variables and Tailwind utilities.

Use the Tailwind default palette or project-specific tokens based on oklch/oklab color spaces as defined in @theme.

Prefer semantic class names for colors in tokens (e.g. --color-brand-*) mapped to Tailwind utilities (bg-brand-500, text-brand-500, etc.).

#### 7.5 Text & Wrapping (v4.1)
Use the wrap-break-word and wrap-anywhere utilities to control text wrapping, especially for long words or URLs:

wrap-break-word for normal break-word behavior.

wrap-anywhere when needed inside flex layouts where intrinsic size causes layout issues.

Prefer these utilities over custom CSS for text wrapping.

#### 7.6 Shadows, Masks & Effects (v4.1)
Use the built-in text-shadow-* and colored drop-shadow-* utilities where text or element shadows are required instead of writing custom shadow CSS.

When masking or advanced effects are needed, use the new mask-* utilities where they apply, before falling back to custom CSS.

### 7.7 Pointer & Interaction Variants (v4.1)
Use pointer-based variants to adapt UI to input devices:

pointer-fine:* for precise input devices (mouse, trackpad).

pointer-coarse:* for touch devices.

Use any-pointer-* variants when behavior should adapt if any input device matches (e.g. laptops with both mouse and touchscreen).

#### 7.8 Alignment & Safe Alignment (v4.1)
Use items-baseline-last / self-baseline-last for layouts where alignment must follow the last text baseline.

Use *-safe alignment utilities (e.g. justify-center-safe) when content must remain visible in small containers and you want overflows biased to one side.

#### 7.9 Source Scanning & Exclusions
Use @source in CSS if Tailwind’s automatic class scanning requires overrides.

Use @source not "<path>" to exclude legacy or irrelevant folders from scanning when necessary.

Keep @source declarations minimal and focused to avoid scanning unnecessary files.

## 8. UI, State & Separation of Concerns
Keep React components focused on rendering and local UI behavior.

Move business logic and complex state transitions into hooks or service modules.

Decouple transport (API calls) from presentation; use typed interfaces between layers.

Use Tailwind utilities for visual concerns; avoid mixing heavy business logic inside style-related modules.

## 9. Testing Expectations
Use the project’s standard test framework (e.g. Vitest / Jest + React Testing Library if configured).

Add or update tests when:

introducing new components or hooks

changing behavior or branching logic

Test:

rendering and behavior under normal conditions

edge cases (empty data, error states, large inputs)

important asynchronous flows

Prefer deterministic tests:

use fake timers or injected clocks for time-based logic

mock network or external dependencies at boundaries

## 10. Documentation & Comments
Add TSDoc / JSDoc to exported functions, utilities, and public components when it improves understanding.

Write comments that explain why something is done, not restating what the code already expresses.

Remove or update outdated comments during refactors.

Update high-level architecture or design documentation when introducing new patterns, layers, or significant dependencies.