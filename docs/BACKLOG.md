**Architecture Backlog**

- **Refactor `SourceHandlerFactory` resolution**: Replace hardcoded `if/elif` lazy imports with a clean registry-based factory (or DI at composition root).
  - **Problem**: `register_handler`/`list_handlers` exist but `HANDLERS` is undefined and `create_handler` ignores any registry. Hardcoded branches limit extensibility and testability.
  - **Goal**: Support runtime handler registration (e.g., plugins like `confluence`) while keeping call sites simple.
  - **Plan**:
    - Add `HANDLERS: dict[str, type[BaseSourceHandler]] = {}` inside `SourceHandlerFactory`.
    - In `create_handler`, first check `HANDLERS.get(source_type)`; if present, use it; else fallback to built-in handlers.
    - Validate registered classes inherit `BaseSourceHandler`.
    - Update `list_handlers()` to return registry keys (optionally include built-ins).
    - Add minimal startup hook to register environment-specific handlers.
  - **Why Not Now**: Lower priority vs ingestion resilience; current hardcoded handlers are sufficient.
  - **Risks**: Import side effects; stringly-typed keys. Mitigate with validation and typed constants.

- **Optional DI Integration (later)**: At app bootstrap, register handlers via a lightweight DI container; still delegate to the factory registry for resolution.
  - Keeps both approaches compatible; DI provides per-env overrides without changing call sites.
