import traceback, sys
modules = [
    'backend.tests.agents.test_mcp_react_agent_llm_wiring',
    'backend.tests.agents_system.test_conflict_choice_guard',
    'backend.tests.agents_system.test_langgraph_skeleton'
]
for m in modules:
    print('--- importing', m)
    try:
        __import__(m, fromlist=['*'])
        print('OK', m)
    except Exception:
        traceback.print_exc()
        print('\n')
