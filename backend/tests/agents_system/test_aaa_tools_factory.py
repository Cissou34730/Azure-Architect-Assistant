from app.agents_system.tools.aaa_candidate_tool import create_aaa_tools


def test_create_aaa_tools_accepts_optional_context():
    tools = create_aaa_tools({"project_id": "demo"})
    assert isinstance(tools, list)
    assert len(tools) > 0
    names = {getattr(tool, "name", "") for tool in tools}
    assert "aaa_record_cost_estimate" in names
    assert "aaa_record_iac_artifacts" in names
    assert "aaa_record_iac_and_cost" not in names
