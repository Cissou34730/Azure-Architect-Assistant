from app.agents_system.tools.kb_tool import create_kb_tools

if __name__ == '__main__':
    tools = create_kb_tools()
    for t in tools:
        name = getattr(t, 'name', None)
        ttype = type(t)
        desc = getattr(t, 'description', None)
        has_func = hasattr(t, 'func')
        print(f"name={name!r}, type={ttype.__name__}, has_func={has_func}, description={desc!r}")

