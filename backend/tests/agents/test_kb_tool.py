import pytest

from app.agents_system.tools.kb_tool import KBSearchTool, create_kb_tools


class DummyResult:
    def __init__(self):
        self.result = {
            "answer": "This is a grounded answer.",
            "sources": [
                {
                    "title": "Azure Architecture Guide",
                    "url": "https://learn.microsoft.com/azure/architecture/guide",
                    "kb_name": "CAF",
                    "score": 0.9,
                }
            ],
            "has_results": True,
        }


@pytest.fixture
def tool(monkeypatch):
    tools = create_kb_tools()
    # find the legacy kb_search wrapper
    kb_tool = next((t for t in tools if getattr(t, "name", None) == "kb_search"), None)
    assert kb_tool is not None

    # Monkeypatch KBSearchTool used internally by the wrapper
    original_KBSearchTool = KBSearchTool

    class DummyAgent:
        def execute(self, query, profile="chat", kb_ids=None, top_k=5, metadata_filters=None):
            return DummyResult().result

    def dummy_kb_constructor():
        t = original_KBSearchTool()
        t._agent = DummyAgent()
        return t

    monkeypatch.setattr('app.agents_system.tools.kb_tool.KBSearchTool', dummy_kb_constructor)
    return kb_tool


def test_kb_search_tool_returns_cited_answer(tool):
    output = tool.run({"query": "How to secure Azure SQL?", "topK": 3})
    assert "This is a grounded answer." in output
    assert "Sources:" in output
    assert "Azure Architecture Guide" in output
