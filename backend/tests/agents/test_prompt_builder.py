from app.agents_system.langchain.prompt_builder import build_prompt_template


def test_prompt_builder_sets_react_required_partial_variables():
    prompt = build_prompt_template(
        "System\nTools: {tools}\nAllowed: {tool_names}\nQuestion: {input}\nContext: {context}\nThought: {agent_scratchpad}",
        tools=[{"name": "kb_search", "description": "Search KB"}],
    )

    assert prompt.partial_variables["tools"] == "kb_search: Search KB"
    assert prompt.partial_variables["tool_names"] == "kb_search"
    assert "input" in prompt.input_variables
    assert "agent_scratchpad" in prompt.input_variables
    assert "context" in prompt.input_variables


def test_prompt_builder_injects_missing_react_placeholders():
    prompt = build_prompt_template("System message", tools=[])
    template = prompt.template

    assert "{input}" in template
    assert "{agent_scratchpad}" in template
    assert "{tools}" in template
    assert "{tool_names}" in template
