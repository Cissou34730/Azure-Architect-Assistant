# Testing Guide: Dependency Injection and Singleton Mocking

> Part of: Backend Testing Documentation  
> Last Updated: February 12, 2026  
> Related: [Backend Reference](../BACKEND_REFERENCE.md), [Singleton Analysis](../reviews/SINGLETON_PATTERN_ANALYSIS.md)

## Overview

All singleton services in the Azure Architect Assistant backend are accessible via FastAPI dependency injection, making them easy to override in tests without complex mocking setup.

## Available Singletons

### 1. **AgentRunner** - Agent system lifecycle
- **Purpose**: Manages agent orchestrator and LLM interactions
- **Dependency**: `app.dependencies.get_agent_runner`
- **Mock Fixture**: `mock_agent_runner` (in `tests/conftest.py`)

### 2. **KBManager** - Knowledge base indices
- **Purpose**: Manages vector indices and KB configuration
- **Dependency**: `app.dependencies.get_kb_manager`
- **Mock Fixture**: `mock_kb_manager` (in `tests/conftest.py`)

### 3. **LLMService** - LLM operations
- **Purpose**: Text generation, document analysis, chat processing
- **Dependency**: `app.dependencies.get_llm_service_dependency`
- **Mock Fixture**: `mock_llm_service` (in `tests/conftest.py`)

### 4. **AIService** - AI provider abstraction
- **Purpose**: Multi-provider support (OpenAI, Azure, Anthropic)
- **Dependency**: `app.dependencies.get_ai_service_dependency`
- **Mock Fixture**: `mock_ai_service` (in `tests/conftest.py`)

### 5. **PromptLoader** - YAML prompt caching
- **Purpose**: Loads and caches agent prompts from YAML files
- **Dependency**: `app.dependencies.get_prompt_loader`
- **Mock Fixture**: `mock_prompt_loader` (in `tests/conftest.py`)

---

## Mock Fixtures

All mock fixtures are defined in [`tests/conftest.py`](../../tests/conftest.py) and are available automatically via pytest's fixture discovery.

### Example: Using Mock Fixtures

```python
def test_my_route(client, mock_kb_manager):
    """Test endpoint with mocked KBManager."""
    from app.dependencies import get_kb_manager
    
    # Configure mock behavior
    mock_kb_manager.list_kbs.return_value = ["test-kb-1", "test-kb-2"]
    
    # Override dependency
    app.dependency_overrides[get_kb_manager] = lambda: mock_kb_manager
    
    # Make request
    response = client.get("/api/kb/list")
    
    # Assertions
    assert response.status_code == 200
    assert len(response.json()["knowledge_bases"]) == 2
    
    # Verify mock was called
    mock_kb_manager.list_kbs.assert_called_once()
    
    # Cleanup (important!)
    app.dependency_overrides.clear()
```

---

## Overriding Dependencies

### Pattern 1: Override Single Dependency

```python
from app.dependencies import get_kb_manager
from app.main import app

def test_list_kbs(client):
    """Test KB listing with mocked manager."""
    mock_manager = Mock(spec=KBManager)
    mock_manager.list_kbs.return_value = ["kb-1"]
    
    app.dependency_overrides[get_kb_manager] = lambda: mock_manager
    
    response = client.get("/api/kb/list")
    assert response.status_code == 200
    
    app.dependency_overrides.clear()
```

### Pattern 2: Override Multiple Dependencies

```python
def test_complex_endpoint(client, mock_kb_manager, mock_llm_service):
    """Test endpoint requiring multiple services."""
    from app.dependencies import get_kb_manager, get_llm_service_dependency
    
    # Configure mocks
    mock_kb_manager.get_kb.return_value = {"id": "test-kb"}
    mock_llm_service.generate_text.return_value = "AI response"
    
    # Override both
    app.dependency_overrides[get_kb_manager] = lambda: mock_kb_manager
    app.dependency_overrides[get_llm_service_dependency] = lambda: mock_llm_service
    
    response = client.post("/api/generate", json={"prompt": "test"})
    
    assert response.status_code == 200
    app.dependency_overrides.clear()
```

### Pattern 3: Fixture-Based Override

```python
import pytest

@pytest.fixture
def client_with_mocks(client, mock_kb_manager, mock_llm_service):
    """Client with all dependencies mocked."""
    from app.dependencies import get_kb_manager, get_llm_service_dependency
    from app.main import app
    
    app.dependency_overrides[get_kb_manager] = lambda: mock_kb_manager
    app.dependency_overrides[get_llm_service_dependency] = lambda: mock_llm_service
    
    yield client
    
    app.dependency_overrides.clear()


def test_with_fixture(client_with_mocks, mock_kb_manager):
    """Use pre-configured client with mocks."""
    mock_kb_manager.list_kbs.return_value = []
    response = client_with_mocks.get("/api/kb/list")
    assert response.status_code == 200
```

---

## Resetting Singleton State (Integration Tests)

For integration tests that need to reset singleton state between tests:

```python
import pytest

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all singletons between tests."""
    yield  # Run test first
    
    # Clear singleton state after test
    from app.agents_system.runner import AgentRunner
    from app.agents_system.config.prompt_loader import PromptLoader
    from app.services.llm_service import LLMServiceSingleton
    from app.services.ai import AIServiceManager
    from app.service_registry import ServiceRegistry
    
    AgentRunner.set_instance(None)
    PromptLoader.set_instance(None)
    LLMServiceSingleton.set_instance(None)
    AIServiceManager.set_instance(None)
    ServiceRegistry.invalidate_kb_manager()
```

---

## Testing Agent Routes

### Example: Mock AgentRunner

```python
from unittest.mock import AsyncMock

def test_agent_query(client, mock_agent_runner):
    """Test agent query endpoint."""
    from app.dependencies import get_agent_runner
    
    # Configure async mock
    mock_agent_runner.execute_query = AsyncMock(
        return_value={
            "answer": "Test answer",
            "reasoning": ["step 1", "step 2"],
            "waf_checklists": []
        }
    )
    
    app.dependency_overrides[get_agent_runner] = lambda: mock_agent_runner
    
    response = client.post(
        "/api/agent/query",
        json={"query": "test query", "project_id": "proj-123"}
    )
    
    assert response.status_code == 200
    assert response.json()["answer"] == "Test answer"
    
    # Verify call
    mock_agent_runner.execute_query.assert_called_once()
    call_args = mock_agent_runner.execute_query.call_args
    assert call_args[0][0] == "test query"
    
    app.dependency_overrides.clear()
```

---

## Testing KB Routes

### Example: Mock KBManager

```python
def test_kb_health(client, mock_kb_manager):
    """Test KB health endpoint."""
    from app.dependencies import get_kb_manager
    from app.kb.service import KnowledgeBaseService
    
    # Mock KB configuration
    mock_kb = {
        "id": "test-kb",
        "name": "Test KB",
        "index_path": "/path/to/index"
    }
    mock_kb_manager.list_kbs.return_value = ["test-kb"]
    mock_kb_manager.get_kb.return_value = mock_kb
    
    app.dependency_overrides[get_kb_manager] = lambda: mock_kb_manager
    
    response = client.get("/api/kb/health")
    
    assert response.status_code == 200
    assert len(response.json()["knowledge_bases"]) == 1
    
    app.dependency_overrides.clear()
```

---

## Testing LLM Service

### Example: Mock LLM Responses

```python
from unittest.mock import AsyncMock

def test_chat_message(client, mock_llm_service):
    """Test chat with mocked LLM."""
    from app.dependencies import get_llm_service_dependency
    
    # Mock async LLM response
    mock_llm_service.process_chat_message = AsyncMock(
        return_value={
            "response": "AI generated response",
            "sources": [{"url": "https://example.com"}]
        }
    )
    
    app.dependency_overrides[get_llm_service_dependency] = lambda: mock_llm_service
    
    response = client.post(
        "/api/chat",
        json={"message": "user question", "project_id": "proj-123"}
    )
    
    assert response.status_code == 200
    assert "AI generated response" in response.json()["response"]
    
    app.dependency_overrides.clear()
```

---

## Best Practices

### ✅ DO

1. **Always clear overrides**: Use `app.dependency_overrides.clear()` in test cleanup
2. **Use provided fixtures**: Leverage `mock_*` fixtures from `conftest.py`
3. **Configure mocks explicitly**: Set return values and side effects for test clarity
4. **Verify mock calls**: Use `assert_called_once()` to ensure code paths executed
5. **Use AsyncMock for async**: Use `unittest.mock.AsyncMock` for async methods

### ❌ DON'T

1. **Don't mock `get_instance()` directly**: Use dependency override instead
2. **Don't forget cleanup**: Always clear overrides or use fixtures
3. **Don't modify global state**: Reset singletons in integration tests
4. **Don't use real services**: Always mock expensive operations (LLM calls, KB queries)
5. **Don't share mocks**: Each test should configure its own mock behavior

---

## Common Pitfalls

### Pitfall 1: Forgetting to Clear Overrides

```python
# ❌ BAD: Leaks into other tests
def test_something(client):
    app.dependency_overrides[get_kb_manager] = lambda: mock
    # ... test code ...
    # Missing: app.dependency_overrides.clear()

# ✅ GOOD: Always cleanup
def test_something(client):
    app.dependency_overrides[get_kb_manager] = lambda: mock
    try:
        # ... test code ...
    finally:
        app.dependency_overrides.clear()
```

### Pitfall 2: Using Mock Instead of AsyncMock

```python
# ❌ BAD: Won't work with async functions
mock_service.execute_query = Mock(return_value={"result": "test"})

# ✅ GOOD: Use AsyncMock for async methods
from unittest.mock import AsyncMock
mock_service.execute_query = AsyncMock(return_value={"result": "test"})
```

### Pitfall 3: Not Configuring Mock Behavior

```python
# ❌ BAD: Mock returns MagicMock, not expected data
mock_kb_manager.get_kb.return_value  # Not set - returns MagicMock!

# ✅ GOOD: Explicitly set return value
mock_kb_manager.get_kb.return_value = {"id": "kb-1", "name": "Test KB"}
```

---

## Running Tests

```bash
# Run all tests
pytest backend/tests

# Run with coverage
pytest backend/tests --cov=backend/app --cov-report=html

# Run specific test file
pytest backend/tests/routers/test_kb_routes.py

# Run with verbose output
pytest backend/tests -v

# Run only tests matching pattern
pytest backend/tests -k "test_kb"
```

---

## Example: Complete Test Module

```python
"""Test KB management routes with dependency injection."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock

from app.main import app
from app.dependencies import get_kb_manager
from app.kb import KBManager


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_overrides():
    """Automatically clear dependency overrides after each test."""
    yield
    app.dependency_overrides.clear()


def test_list_kbs(client, mock_kb_manager):
    """Test listing knowledge bases."""
    mock_kb_manager.list_kbs.return_value = ["kb-1", "kb-2"]
    
    app.dependency_overrides[get_kb_manager] = lambda: mock_kb_manager
    
    response = client.get("/api/kb/list")
    
    assert response.status_code == 200
    assert len(response.json()["knowledge_bases"]) == 2


def test_kb_not_found(client, mock_kb_manager):
    """Test 404 when KB doesn't exist."""
    mock_kb_manager.kb_exists.return_value = False
    
    app.dependency_overrides[get_kb_manager] = lambda: mock_kb_manager
    
    response = client.get("/api/kb/nonexistent/status")
    
    assert response.status_code == 404
```

---

## Additional Resources

- [FastAPI Testing Documentation](https://fastapi.tiangolo.com/tutorial/testing/)
- [FastAPI Dependency Override](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
- [pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Backend Reference](../BACKEND_REFERENCE.md)
- [Singleton Pattern Analysis](../reviews/SINGLETON_PATTERN_ANALYSIS.md)
