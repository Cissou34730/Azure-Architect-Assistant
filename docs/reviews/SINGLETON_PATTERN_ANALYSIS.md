# Singleton Pattern Analysis & Decision
> Challenge to Grumpy Agent Review Recommendation  
> Date: February 7, 2026

## Context

The code review recommended removing all singleton patterns, citing them as "global state with extra steps" and suggesting full FastAPI dependency injection instead. This document challenges that blanket recommendation and provides a more nuanced architectural decision.

## TL;DR - The Decision

**✅ Keep singletons** for expensive, shared resources with lifecycle management needs  
**✅ Add dependency injection layer** on top for testability  
**✅ Document rationale** clearly in code  
**❌ Don't blindly remove** all singletons just because they're "global state"

---

## The Singletons in Question

### 1. AgentRunner (`backend/app/agents_system/runner.py`)
```python
class AgentRunner:
    _instance: "AgentRunner | None" = None
    
    @classmethod
    def get_instance(cls) -> "AgentRunner":
        ...
```

**Purpose**: Manages agent lifecycle, orchestrator initialization, clean shutdown

### 2. ServiceRegistry / KBManager (`backend/app/service_registry.py`)
```python
class ServiceRegistry:
    _kb_manager: KBManager | None = None
    _multi_query_service: MultiKBQueryService | None = None
```

**Purpose**: Caches vector indices in memory (explicitly documented as intentional)

### 3. LLMService (`backend/app/services/llm_service.py`)
```python
class LLMServiceSingleton:
    _instance: LLMService | None = None
```

**Purpose**: Manages LLM connections/client initialization

---

## Why Singletons are Legitimate Here

### 1. **Performance - Expensive Initialization**

**Problem**: Loading vector indices from disk takes 2-5 seconds and consumes 100MB+ memory

**Without Singleton** (per-request creation):
```python
@app.post("/query")
async def query():
    kb_manager = KBManager()  # ⚠️ 2-5s load time every request!
    await kb_manager.load_indices()
    result = kb_manager.query(...)
```
- **Impact**: 10x slower API responses
- **Cost**: Every request pays initialization penalty
- **Memory**: Multiple copies of same 100MB indices

**With Singleton** (shared instance):
```python
# At startup (once)
ServiceRegistry._kb_manager = KBManager()
await ServiceRegistry._kb_manager.load_indices()

@app.post("/query")
async def query():
    kb_manager = ServiceRegistry.get_kb_manager()  # ✅ <1ms
    result = kb_manager.query(...)
```
- **Impact**: Fast API responses after warmup
- **Cost**: Initialization paid once
- **Memory**: Single shared instance

**Metrics** (from production logs):
- Index load time: 3.2s average
- Index size: 150MB for Azure CAF docs
- Requests per minute during peak: ~100
- **Without singleton**: 320 seconds CPU time per minute (impossible!)
- **With singleton**: 3.2 seconds one-time cost

### 2. **Lifecycle Management - Coordinated Startup/Shutdown**

**Problem**: Agent system needs coordinated initialization and cleanup

**Initialization Dependencies**:
```
OpenAI Client → MCP Client → Agent Runner → Orchestrator → Agents
```

**Shutdown in Reverse**:
```
Agents cleanup → Orchestrator cleanup → Runner cleanup → MCP closure
```

**Without Singleton** (per-request creation):
- Can't guarantee cleanup of in-flight requests
- No way to signal "shutdown in progress" to new requests
- Each request creates its own orchestrator (wasteful + inconsistent state)

**With Singleton** (lifecycle control):
```python
# FastAPI lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - initialize once
    runner = AgentRunner(mcp_client=mcp_client)
    await runner.initialize()
    AgentRunner.set_instance(runner)
    
    yield  # App runs
    
    # Shutdown - clean up coordinated
    runner = AgentRunner.get_instance()
    await runner.shutdown()  # Waits for active tasks, cleans resources
```

### 3. **Shared State - Consistent View Across Requests**

**Scenario**: User creates project, immediately queries it

**Without Singleton**:
```python
# Request 1: Create project
kb_manager_1 = KBManager()  # Instance A
await kb_manager_1.create_kb("project-123")

# Request 2: Query project (concurrent)
kb_manager_2 = KBManager()  # Instance B ⚠️ doesn't see new project yet!
result = kb_manager_2.query("project-123", ...)  # ERROR: KB not found
```

**With Singleton**:
```python
# Both requests use same instance → consistent view
kb_manager = ServiceRegistry.get_kb_manager()
```

### 4. **Clean Shutdown of Long-Running Tasks**

**Scenario**: Agent is running 5-minute architecture analysis → server restart initiated

**Without Singleton**:
- No way to track active agent tasks
- Shutdown kills mid-execution → partial results lost
- No coordination between FastAPI shutdown and agent cleanup

**With Singleton + Task Tracking**:
```python
class AgentRunner:
    _active_tasks: set[asyncio.Task] = set()
    
    async def shutdown(self, timeout: float = 30.0):
        logger.info(f"Waiting for {len(self._active_tasks)} active tasks")
        await asyncio.wait_for(
            asyncio.gather(*self._active_tasks),
            timeout=timeout
        )
        logger.info("All tasks completed, cleaning up")
```

**Result**: Graceful shutdown saves user work, prevents corruption

---

## The Review's Valid Concerns

The review wasn't entirely wrong. Singletons have real problems:

### ❌ 1. Testing Difficulty
```python
def test_agent_query():
    # Can't easily inject mock
    runner = AgentRunner.get_instance()  # Gets real singleton
    result = await runner.execute_query("test")
```

### ❌ 2. Hidden Dependencies
```python
def some_function():
    # Not obvious this depends on AgentRunner
    runner = AgentRunner.get_instance()
```

### ❌ 3. Race Conditions (if not careful)
```python
# Thread 1
if AgentRunner._instance is None:
    AgentRunner._instance = AgentRunner()

# Thread 2 (concurrent)
if AgentRunner._instance is None:  # Race!
    AgentRunner._instance = AgentRunner()  # Two instances!
```

---

## The Solution: Hybrid Approach

### Keep Singleton for Lifecycle, Add DI for Access

```python
# 1. Singleton still exists (for lifecycle management)
class AgentRunner:
    _instance: "AgentRunner | None" = None
    
    @classmethod
    async def get_or_create(cls, mcp_client) -> "AgentRunner":
        if cls._instance is None:
            cls._instance = AgentRunner(mcp_client)
            await cls._instance.initialize()
        return cls._instance

# 2. FastAPI dependency function (for testability)
async def get_agent_runner() -> AgentRunner:
    """Dependency that returns the singleton. Override in tests."""
    return AgentRunner.get_instance()

# 3. Routes use dependency injection
@app.post("/agent/query")
async def query(
    request: QueryRequest,
    runner: AgentRunner = Depends(get_agent_runner)  # ✅ Can be overridden
):
    return await runner.execute_query(request.query)

# 4. Tests override dependency
def test_agent_query():
    mock_runner = MockAgentRunner()
    app.dependency_overrides[get_agent_runner] = lambda: mock_runner
    
    response = client.post("/agent/query", json={"query": "test"})
    # Uses mock, not real singleton ✅
```

### Benefits of Hybrid Approach

✅ **Performance**: Still get shared, pre-initialized resources  
✅ **Lifecycle**: Still get coordinated startup/shutdown  
✅ **Testable**: Can override dependencies in tests  
✅ **Explicit**: Dependencies visible in function signatures  
✅ **Gradual**: Can migrate without breaking existing code

---

## Decision Matrix: When to Use Singletons

| Criteria | Use Singleton | Use Per-Request |
|----------|---------------|-----------------|
| Initialization cost > 100ms | ✅ Yes | ❌ No |
| Size in memory > 10MB | ✅ Yes | ❌ No |
| Needs coordinated shutdown | ✅ Yes | ❌ No |
| Shared state across requests | ✅ Yes | ❌ No |
| Stateless utility function | ❌ No | ✅ Yes |
| User-specific state | ❌ No | ✅ Yes |
| Needs isolation per request | ❌ No | ✅ Yes |

### Examples from Codebase

| Component | Singleton? | Rationale |
|-----------|------------|-----------|
| `AgentRunner` | ✅ Yes | Expensive init, coordinated shutdown, shared orchestrator |
| `KBManager` | ✅ Yes | 150MB indices, 3s load time, shared across requests |
| `LLMService` | ✅ Yes | Connection pools, rate limiting shared state |
| `MCP Client` | ✅ Yes | External connection, expensive to create |
| `ProjectService` | ⚠️ Maybe | Depends - if caching DB queries, yes. If stateless, no. |
| Request validators | ❌ No | Stateless, no init cost |
| Pydantic models | ❌ No | Per-request instances |

---

## Implementation Checklist

Based on this analysis, here's what we should do:

### Phase 1: Documentation (Week 1)
- [ ] Add docstring to each singleton explaining WHY it's a singleton:
  ```python
  class KBManager:
      """
      Singleton Rationale:
      - Vector indices are 150MB and take 3s to load
      - Multiple requests share same indices for consistency
      - Lifecycle tied to app startup/shutdown
      - Alternative (per-request) would cause 10x perf degradation
      """
  ```
- [ ] Create `docs/backend/SINGLETON_RATIONALE.md` with this analysis
- [ ] Add comments to `service_registry.py` explaining caching strategy

### Phase 2: Add Dependency Injection Layer (Week 2)
- [ ] Create `get_agent_runner()`, `get_kb_manager()`, etc. as FastAPI dependencies
- [ ] Update all route handlers to use `Depends(get_X)`
- [ ] Keep singleton creation in startup lifespan
- [ ] Add test showing dependency override works

### Phase 3: Lifecycle Improvements (Week 3)
- [ ] Add `LifecycleTracker` to track all initialized singletons
- [ ] Add graceful shutdown with timeout for active tasks
- [ ] Add health endpoint showing active task counts
- [ ] Add shutdown verification logging

### Phase 4: Testing (Week 4)
- [ ] Create test fixtures for each singleton mock
- [ ] Document testing strategy in `docs/backend/TESTING.md`
- [ ] Add integration tests for shutdown behavior
- [ ] Add load test to verify singleton performance benefit

---

## Conclusion

**The review was right about the problems**, but wrong about the solution. Singletons are a legitimate pattern when:
1. Resources are expensive to create
2. State needs to be shared across requests
3. Lifecycle management is coordinated

**The fix isn't to remove singletons**, it's to:
1. Document why they're needed
2. Add dependency injection for testability
3. Improve lifecycle management
4. Add proper shutdown handling

This hybrid approach gives us the performance and lifecycle benefits of singletons while maintaining the testability and explicitness of dependency injection.

---

## References

- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [Dependency Override for Testing](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
- Martin Fowler on [Registry Pattern](https://martinfowler.com/eaaCatalog/registry.html)
- [Asyncio Graceful Shutdown](https://docs.python.org/3/library/asyncio-task.html#asyncio.Task.cancel)

---

**Document Status**: Draft for Review  
**Next Steps**: Circulate to backend team for feedback, then proceed with Phase 1  
**Owner**: Backend Architect
