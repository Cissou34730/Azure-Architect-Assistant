from app.agents_system.tools.aaa_candidate_tool import create_aaa_tools


def test_create_aaa_tools_accepts_optional_context():
    tools = create_aaa_tools({"project_id": "demo"})
    assert isinstance(tools, list)
    assert len(tools) > 0
