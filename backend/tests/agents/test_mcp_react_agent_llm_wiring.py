from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents_system.agents.mcp_react_agent import MCPReActAgent


@pytest.mark.asyncio
async def test_mcp_react_agent_uses_ai_service_to_create_llm(monkeypatch):
    # Patch get_ai_service to return a fake service with create_chat_llm
    fake_service = MagicMock()
    fake_llm = object()
    fake_service.create_chat_llm.return_value = fake_llm

    with patch('app.agents_system.agents.mcp_react_agent.get_ai_service', return_value=fake_service):
        agent = MCPReActAgent(openai_api_key=None, mcp_client=MagicMock(), model='gpt-test', temperature=0.2)
        # Patch all tool factories to avoid creating real tool instances that may be multi-input
        with (
            patch('app.agents_system.agents.mcp_react_agent.create_mcp_tools', new=AsyncMock(return_value=[])),
            patch('app.agents_system.agents.mcp_react_agent.create_kb_tools', return_value=[]),
            patch('app.agents_system.agents.mcp_react_agent.create_aaa_tools', return_value=[]),
            patch('app.agents_system.agents.mcp_react_agent.AgentFacade') as mock_facade,
        ):
            # Prevent AgentFacade.initialize from constructing a real agent
            af_instance = mock_facade.return_value
            af_instance.initialize = AsyncMock()
            # initialize should call create_chat_llm on the fake service
            await agent.initialize()
            fake_service.create_chat_llm.assert_called()
            assert agent.llm is fake_llm


@pytest.mark.asyncio
async def test_initialize_forwards_callbacks_to_agent_facade(monkeypatch):
    fake_service = MagicMock()
    fake_llm = object()
    fake_service.create_chat_llm.return_value = fake_llm

    with patch('app.agents_system.agents.mcp_react_agent.get_ai_service', return_value=fake_service):
        agent = MCPReActAgent(openai_api_key=None, mcp_client=MagicMock(), model='gpt-test')
        with (
            patch('app.agents_system.agents.mcp_react_agent.create_mcp_tools', new=AsyncMock(return_value=[])),
            patch('app.agents_system.agents.mcp_react_agent.create_kb_tools', return_value=[]),
            patch('app.agents_system.agents.mcp_react_agent.create_aaa_tools', return_value=[]),
            patch('app.agents_system.agents.mcp_react_agent.AgentFacade') as mock_facade,
        ):
            # Patch AgentFacade.initialize to capture callbacks
            af_instance = mock_facade.return_value
            af_instance.initialize = AsyncMock()
            callbacks = [lambda x: x]
            await agent.initialize(callbacks=callbacks)
            af_instance.initialize.assert_called_with(callbacks=callbacks)


def test_constructor_accepts_model_name_and_prompt_aliases():
    agent = MCPReActAgent(
        model_name="gpt-4o",
        system_prompt="custom-system",
        react_template="custom-react",
    )
    assert agent.model == "gpt-4o"
    assert agent.system_prompt == "custom-system"
    assert agent.react_template == "custom-react"


@pytest.mark.asyncio
async def test_ainvoke_maps_payload_to_agent_facade():
    agent = MCPReActAgent(model="gpt-test")
    agent.agent_facade = MagicMock()
    agent.agent_facade.ainvoke = AsyncMock(  # type: ignore[method-assign]
        return_value={"output": "ok", "intermediate_steps": [], "success": True}
    )

    result = await agent.ainvoke({"input": "hello", "context": "ctx"})

    agent.agent_facade.ainvoke.assert_awaited_once_with({"input": "hello", "context": "ctx"})
    assert result["output"] == "ok"


@pytest.mark.asyncio
async def test_ainvoke_maps_query_to_input_for_facade():
    agent = MCPReActAgent(model="gpt-test")
    agent.agent_facade = MagicMock()
    agent.agent_facade.ainvoke = AsyncMock(  # type: ignore[method-assign]
        return_value={"output": "ok", "intermediate_steps": [], "success": True}
    )

    result = await agent.ainvoke({"query": "hello"})

    agent.agent_facade.ainvoke.assert_awaited_once_with({"query": "hello", "input": "hello"})
    assert result["output"] == "ok"

