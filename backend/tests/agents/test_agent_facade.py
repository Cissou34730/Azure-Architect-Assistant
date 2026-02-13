import pytest

from app.agents_system.langchain.agent_facade import AgentFacade


class DummyAgentArun:
    async def arun(self, input_text):
        return f"echo:{input_text}"


class DummyAgentAinvoke:
    async def ainvoke(self, payload):
        # return a dict-like payload to simulate modern agent
        return {"output": f"ai:{payload.get('input')}", "intermediate_steps": []}


@pytest.mark.asyncio
async def test_arun_normalization(monkeypatch):
    facade = AgentFacade(llm=object(), tools=[])

    # inject a dummy agent that implements arun
    facade._executor = DummyAgentArun()

    res = await facade.ainvoke({"input": "hello"})
    assert res["output"] == "echo:hello"
    assert res["intermediate_steps"] == []


@pytest.mark.asyncio
async def test_ainvoke_normalization(monkeypatch):
    facade = AgentFacade(llm=object(), tools=[])
    facade._executor = DummyAgentAinvoke()

    res = await facade.ainvoke({"input": "world"})
    assert res["output"] == "ai:world"
    assert res["intermediate_steps"] == []

