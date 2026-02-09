# Grumpy Review: Ingestion Shutdown (Task 2.4)
> 😤 *sigh* Reluctantly reviewed by Grumpy Agent. This better be worth my time.

## General Disappointment
You finally killed the module-level shutdown event in the orchestrator. Good. Then you immediately introduced a different shared mutable object in the router. It’s still better than a single global `asyncio.Event()` for every job, but let’s not pretend this is pure.

## The Issues (I hope you're sitting down)
- **Line 119:** `shutdown_manager = ShutdownManager()` is still module-level mutable state in the router — *Congrats, you moved the global instead of deleting the idea.* Prefer wiring this via app lifespan / dependency injection so it’s explicit and testable.
- **Line 14:** `ShutdownManager.register_job()` silently overwrites an existing entry for the same `job_id` — *Because who needs invariants?* Consider rejecting duplicates or logging loudly; concurrent starts/resumes could make shutdown signaling unpredictable.
- **Line 125:** `is_shutdown_requested()` logs a warning every time it’s polled while set — *Log spam is not observability.* Rate-limit it (log once per job) or move the warning to the transition where the flag gets set.
- **Line 61:** Signal handler assumes `ingestion_router.shutdown_manager` exists — *Hope is not an interface.* Either type it explicitly, validate the attribute, or pass the manager directly.
- **Line 10:** Tests use `assert x is False/True` for booleans — *Pedantic, but why make your future self squint?* Prefer `assert not x` / `assert x`.

## Guidelines

### Review Scope
- **Focus on changed lines** - Done (shutdown path + wiring)
- **Prioritize important issues** - Correctness + operability first
- **Maximum 5 comments** - You’re welcome
- **Be actionable** - Even when I’m annoyed

### Tone Guidelines
- **Grumpy but not hostile** - I’m trying
- **Sarcastic but specific** - You’ll survive
- **Experienced but helpful** - Allegedly
- **Concise** - Barely

### Memory Usage
- **Track patterns** - Globals keep sneaking back in
- **Avoid repetition** - Five comments max
- **Build context** - Shutdown behavior matters under SIGINT

## Output Format

```json
{
  "path": "backend/app/routers/ingestion.py",
  "line": 119,
  "body": "shutdown_manager is module-level mutable state. Prefer creating it in app lifespan / DI and passing it explicitly."
}
```

```json
{
  "path": "backend/app/ingestion/application/shutdown_manager.py",
  "line": 14,
  "body": "register_job overwrites existing job_id entries silently. Consider rejecting duplicates or logging to avoid unpredictable shutdown behavior."
}
```

```json
{
  "path": "backend/app/ingestion/application/orchestrator.py",
  "line": 125,
  "body": "is_shutdown_requested logs on every poll while set; this can spam logs. Consider logging once per job or rate-limiting."
}
```

```json
{
  "path": "backend/app/core/signals.py",
  "line": 61,
  "body": "Signal handler assumes ingestion_router has shutdown_manager. Pass the manager directly or validate attribute to avoid AttributeError." 
}
```

```json
{
  "path": "backend/tests/ingestion/test_shutdown_manager.py",
  "line": 10,
  "body": "Test assertions use 'is False/True' style; prefer 'assert not cond' / 'assert cond' for readability." 
}
```

## Verdict
PASS - 😤 Fine. The shutdown event is per-job now, signal handlers hook into the manager, and tests pass. Don’t make me review another global next week.
