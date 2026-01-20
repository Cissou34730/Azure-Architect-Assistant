import importlib
m = importlib.import_module('langchain')
print('langchain version:', getattr(m, '__version__', 'unknown'))
import langchain.agents as agents
print('agents sample:', [n for n in dir(agents) if not n.startswith('_')][:80])
for name in ['initialize_agent','AgentType','AgentExecutor','create_react_agent','Agent','AgentRunner','Tool','create_openai_functions_agent','AgentOutputParser']:
    print(name, hasattr(agents, name))
