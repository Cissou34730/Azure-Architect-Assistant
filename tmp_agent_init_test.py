import asyncio
from backend.app.agents_system.langchain.agent_facade import AgentFacade
from backend.app.agents_system.tools.kb_tool import create_kb_tools

async def main():
    tools = create_kb_tools()
    print('Created tools:', [getattr(t,'name', type(t).__name__) for t in tools])
    class DummyLLM:
        def __init__(self):
            pass
    af = AgentFacade(llm=DummyLLM(), tools=tools, verbose=False)
    try:
        await af.initialize()
        print('AgentFacade initialized OK')
    except Exception as e:
        print('AgentFacade initialize failed:', e)

if __name__ == '__main__':
    asyncio.run(main())
