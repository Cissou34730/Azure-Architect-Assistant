"""
Global pytest fixtures for backend tests.
"""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.agents_system.checklists.engine import ChecklistEngine
from app.agents_system.checklists.registry import ChecklistRegistry
from app.agents_system.checklists.service import ChecklistService
from app.core.app_settings import get_settings
from app.models.checklist import ChecklistTemplate
from app.models.project import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an in-memory database and provide an async session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def mock_settings():
    """Provide mock settings."""
    settings = get_settings()
    # Override settings for testing if needed
    return settings


@pytest.fixture
def test_registry(mock_settings, tmp_path):
    """Provide a registry with a temporary cache directory."""
    cache_dir = tmp_path / "checklists"
    cache_dir.mkdir()
    registry = ChecklistRegistry(cache_dir=cache_dir, settings=mock_settings)
    registry.register_template(
        ChecklistTemplate(
            slug="azure-waf-v1",
            title="Azure WAF",
            description="Test template",
            version="1.0",
            source="tests",
            source_url="https://example.com",
            source_version="1.0",
            content={
                "items": [
                    {
                        "id": "sec-01",
                        "title": "Secure Admin Access",
                        "pillar": "Security",
                        "severity": "high",
                    },
                    {
                        "id": "rel-01",
                        "title": "Backup Strategy",
                        "pillar": "Reliability",
                        "severity": "critical",
                    },
                ]
            },
        )
    )
    return registry


@pytest.fixture
def test_engine(test_db_session, test_registry, mock_settings):
    """Provide a ChecklistEngine with the test database."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def session_factory():
        yield test_db_session

    return ChecklistEngine(
        db_session_factory=session_factory,
        registry=test_registry,
        settings=mock_settings
    )


@pytest.fixture
def test_checklist_service(test_engine, test_registry):
    """Provide a ChecklistService."""
    return ChecklistService(engine=test_engine, registry=test_registry)


# ============================================================================
# Singleton Mock Fixtures for Dependency Injection Testing
# ============================================================================


@pytest.fixture
def mock_agent_runner():
    """
    Mock AgentRunner for testing.
    
    Usage:
        def test_my_route(client, mock_agent_runner):
            from app.dependencies import get_agent_runner
            app.dependency_overrides[get_agent_runner] = lambda: mock_agent_runner
            # ... test code ...
            app.dependency_overrides.clear()
    """
    from unittest.mock import AsyncMock, Mock

    from app.agents_system.runner import AgentRunner

    runner = Mock(spec=AgentRunner)
    runner.initialize = AsyncMock()
    runner.shutdown = AsyncMock()
    return runner


@pytest.fixture
def mock_kb_manager():
    """
    Mock KBManager for testing.
    
    Usage:
        def test_my_route(client, mock_kb_manager):
            from app.dependencies import get_kb_manager
            app.dependency_overrides[get_kb_manager] = lambda: mock_kb_manager
            # ... test code ...
            app.dependency_overrides.clear()
    """
    from unittest.mock import AsyncMock, Mock

    from app.kb import KBManager

    manager = Mock(spec=KBManager)
    manager.list_kbs = Mock(return_value=["test-kb"])
    manager.get_kb = Mock(return_value=None)
    manager.kb_exists = Mock(return_value=False)
    manager.query = AsyncMock(return_value={"results": []})
    manager.create_kb = AsyncMock()
    return manager


@pytest.fixture
def mock_llm_service():
    """
    Mock LLMService for testing.
    
    Usage:
        def test_my_route(client, mock_llm_service):
            from app.dependencies import get_llm_service_dependency
            app.dependency_overrides[get_llm_service_dependency] = lambda: mock_llm_service
            # ... test code ...
            app.dependency_overrides.clear()
    """
    from unittest.mock import AsyncMock, Mock

    from app.services.llm_service import LLMService

    service = Mock(spec=LLMService)
    service.generate_text = AsyncMock(return_value="Generated text")
    service.analyze_document = AsyncMock(return_value={"analysis": "test"})
    service.process_chat_message = AsyncMock(return_value={"response": "test"})
    return service


@pytest.fixture
def mock_ai_service():
    """
    Mock AIService for testing.
    
    Usage:
        def test_my_route(client, mock_ai_service):
            from app.dependencies import get_ai_service_dependency
            app.dependency_overrides[get_ai_service_dependency] = lambda: mock_ai_service
            # ... test code ...
            app.dependency_overrides.clear()
    """
    from unittest.mock import AsyncMock, Mock

    from app.services.ai import AIService

    service = Mock(spec=AIService)
    service.chat = AsyncMock(return_value="AI response")
    service.get_embedding = AsyncMock(return_value=[0.1] * 1536)
    return service


@pytest.fixture
def mock_prompt_loader():
    """
    Mock PromptLoader for testing.
    
    Usage:
        def test_my_route(client, mock_prompt_loader):
            from app.dependencies import get_prompt_loader
            app.dependency_overrides[get_prompt_loader] = lambda: mock_prompt_loader
            # ... test code ...
            app.dependency_overrides.clear()
    """
    from unittest.mock import Mock

    from app.agents_system.config.prompt_loader import PromptLoader

    loader = Mock(spec=PromptLoader)
    loader.get_prompt = Mock(return_value="Test prompt")
    loader.reload = Mock()
    return loader
