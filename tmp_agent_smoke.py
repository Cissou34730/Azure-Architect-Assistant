from app.agents_system.tools.kb_tool import create_kb_tools
from app.agents_system.langchain.agent_facade import AgentFacade
from types import SimpleNamespace
import asyncio

if __name__ == '__main__':
    tools = create_kb_tools()
    print('Loaded tools:', [getattr(t,'name',None) for t in tools])
    # Create a dummy LLM-like object with minimal interface expected
    llm = SimpleNamespace()
    f = AgentFacade(llm=llm, tools=tools)
    try:
        asyncio.run(f.initialize())
        print('AgentFacade initialized successfully')
    except Exception as e:
        print('AgentFacade initialize failed:', repr(e))
