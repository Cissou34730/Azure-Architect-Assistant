import pytest


@pytest.mark.asyncio
async def test_orchestrator_execute_smoke(monkeypatch):
    # Patch environment so OpenAISettings validates
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Import after env patch
    from app.agents_system.orchestrator.orchestrator import AgentOrchestrator

    # Dummy agent to bypass real LLM/tool execution
    class DummyAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.tools = kwargs.get("tools", [])

        async def initialize(self):
            return None

        async def execute(self, user_query: str, project_context=None):
            return {
                "success": True,
                "output": f"echo: {user_query}",
            }

    # Replace MCPReActAgent with dummy inside orchestrator
    monkeypatch.setattr(
        "app.agents_system.orchestrator.orchestrator.MCPReActAgent",
        DummyAgent,
    )

    # Avoid building real MCP tools (type validation on client)
    async def _dummy_create_mcp_tools(_):
        return []

    monkeypatch.setattr(
        "app.agents_system.orchestrator.orchestrator.create_mcp_tools",
        _dummy_create_mcp_tools,
    )

    # Minimal fake MCP client (tools won't be invoked in dummy agent)
    class FakeMCPClient:
        async def initialize(self):
            return None

    orch = AgentOrchestrator()
    await orch.initialize(FakeMCPClient())

    result = await orch.execute("hello world")

    assert isinstance(result, dict)
    assert result.get("success") is True
    assert "echo: hello world" in result.get("output", "")