import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from backend.app.agents_system.agents.mcp_react_agent import MCPReActAgent


@pytest.mark.asyncio
async def test_mcp_react_agent_uses_ai_service_to_create_llm(monkeypatch):
    # Patch get_ai_service to return a fake service with create_chat_llm
    fake_service = MagicMock()
    fake_llm = object()
    fake_service.create_chat_llm.return_value = fake_llm

    with patch('backend.app.agents_system.agents.mcp_react_agent.get_ai_service', return_value=fake_service):
        agent = MCPReActAgent(openai_api_key=None, mcp_client=MagicMock(), model='gpt-test', temperature=0.2)
        # Patch all tool factories to avoid creating real tool instances that may be multi-input
        with patch('backend.app.agents_system.agents.mcp_react_agent.create_mcp_tools', new=AsyncMock(return_value=[])), \
             patch('backend.app.agents_system.agents.mcp_react_agent.create_kb_tools', return_value=[]), \
             patch('backend.app.agents_system.agents.mcp_react_agent.create_aaa_tools', return_value=[]), \
             patch('backend.app.agents_system.agents.mcp_react_agent.AgentFacade') as AF:
            # Prevent AgentFacade.initialize from constructing a real agent
            af_instance = AF.return_value
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

    with patch('backend.app.agents_system.agents.mcp_react_agent.get_ai_service', return_value=fake_service):
        agent = MCPReActAgent(openai_api_key=None, mcp_client=MagicMock(), model='gpt-test')
        with patch('backend.app.agents_system.agents.mcp_react_agent.create_mcp_tools', new=AsyncMock(return_value=[])), \
             patch('backend.app.agents_system.agents.mcp_react_agent.create_kb_tools', return_value=[]), \
             patch('backend.app.agents_system.agents.mcp_react_agent.create_aaa_tools', return_value=[]):
            # Patch AgentFacade.initialize to capture callbacks
            with patch('backend.app.agents_system.agents.mcp_react_agent.AgentFacade') as AF:
                af_instance = AF.return_value
                af_instance.initialize = AsyncMock()
                callbacks = [lambda x: x]
                await agent.initialize(callbacks=callbacks)
                af_instance.initialize.assert_called_with(callbacks=callbacks)
